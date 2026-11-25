import json
import os
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta

FILENAME = "chgk_full_analytics.json"
TEAM_IDS = [87812, 98143]
MIN_CORE_GAMES = 10      # Игроки основы (от 10 игр в базе)
MIN_OVERLAP_PLAYERS = 2  # Минимум игроков основы за одним столом в стороннем турнире
RECENT_DAYS_REFRESH = 60 # Обновлять TrueDL для турниров моложе 60 дней

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json"
}


def fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception:
        return None


def get_tid(g):
    for k in ["tournamentId", "idtournament", "tournament_id", "id"]:
        if g.get(k) is not None:
            try:
                return int(g[k])
            except (ValueError, TypeError):
                pass
    t = g.get("tournament")
    if isinstance(t, dict) and t.get("id") is not None:
        try:
            return int(t["id"])
        except (ValueError, TypeError):
            pass
    return None


def extract_editors_from_info(info, tid=None):
    names, seen = [], set()

    def add_person(obj):
        if isinstance(obj, str):
            s = obj.strip()
            if s and s.lower() not in seen:
                seen.add(s.lower())
                names.append(s)
            return
        if isinstance(obj, dict):
            p = obj.get("player") or obj.get("person") or obj.get("user") or obj
            if isinstance(p, dict):
                parts = [
                    p.get("surname") or p.get("lastName") or "",
                    p.get("name") or p.get("firstName") or "",
                    p.get("patronymic") or p.get("middleName") or ""
                ]
                full = " ".join(str(x).strip() for x in parts if x and str(x).strip())
                if not full:
                    full = str(p.get("fullName") or p.get("title") or "").strip()
                if full and full.lower() not in seen:
                    seen.add(full.lower())
                    names.append(full)

    if isinstance(info, dict):
        for key in ["editors", "redactors", "editorsAssigned", "tournamentsEditors"]:
            val = info.get(key)
            if isinstance(val, list):
                for item in val:
                    add_person(item)

    if not names and tid is not None:
        ed_resp = fetch_json(f"https://api.rating.chgk.info/tournaments/{tid}/editors")
        if isinstance(ed_resp, list):
            for item in ed_resp:
                add_person(item)

    return names


def build_game_record(tid, team_id, player_names_fallback, is_overlap=False):
    t_info = fetch_json(f"https://api.rating.chgk.info/tournaments/{tid}")
    res_list = fetch_json(
        f"https://api.rating.chgk.info/tournaments/{tid}/results?includeTeamMembers=1&includeMasksAndControversials=1"
    )
    if not isinstance(t_info, dict) or not isinstance(res_list, list):
        return None

    target_res = None
    all_taken = []
    for r in res_list:
        q_tot = r.get("questionsTotal")
        if isinstance(q_tot, (int, float)):
            all_taken.append(float(q_tot))
        r_team = r.get("team") or {}
        r_tid = r_team.get("id") if isinstance(r_team, dict) else r.get("idteam")
        if r_tid is not None and int(r_tid) == int(team_id):
            target_res = r

    if not target_res:
        return None

    mask = target_res.get("mask") or ""
    total_q = len(mask) if mask else 0
    if total_q == 0:
        q_qty = t_info.get("questionQty")
        if isinstance(q_qty, dict):
            total_q = sum(int(v) for v in q_qty.values() if str(v).isdigit())
    if total_q == 0:
        total_q = 36

    taken = target_res.get("questionsTotal")
    if taken is None:
        taken = mask.count("1") if mask else 0

    members = []
    for tm in (target_res.get("teamMembers") or []):
        p = tm.get("player") or tm
        if isinstance(p, dict) and p.get("id"):
            pid = int(p["id"])
            full_name = " ".join(
                str(p.get(k) or "").strip() for k in ["surname", "name", "patronymic"] if p.get(k)
            ).strip()
            members.append({
                "id": pid,
                "name": full_name or player_names_fallback.get(pid, f"Игрок {pid}")
            })

    raw_true_dl = t_info.get("trueDL")
    raw_forecast_dl = t_info.get("difficultyForecast")
    true_dl = raw_true_dl if raw_true_dl is not None else raw_forecast_dl
    dl_is_forecast = (raw_true_dl is None and raw_forecast_dl is not None)

    date_end = str(t_info.get("dateEnd") or t_info.get("dateStart") or "")[:10]
    field_avg = round(sum(all_taken) / len(all_taken), 2) if all_taken else 0

    record = {
        "tournamentId": int(tid),
        "teamId": int(team_id),
        "name": t_info.get("name") or f"Турнир {tid}",
        "dateEnd": date_end,
        "taken": int(taken),
        "totalQuestions": int(total_q),
        "fieldAvg": field_avg,
        "mask": mask,
        "trueDL": float(true_dl) if true_dl is not None else None,
        "declaredDL": float(raw_forecast_dl) if raw_forecast_dl is not None else None,
        "dlIsForecast": dl_is_forecast,
        "editors": extract_editors_from_info(t_info, tid=tid),
        "members": members
    }
    if is_overlap:
        record["isOverlapAdded"] = True
    return record


def main():
    if os.path.exists(FILENAME):
        with open(FILENAME, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"teamNames": {}, "games": []}

    games = data.get("games", [])
    team_names = data.get("teamNames", {})

    existing_tids = set()
    player_counts = defaultdict(int)
    player_names = {}

    for g in games:
        tid = get_tid(g)
        if tid is not None:
            existing_tids.add(tid)
        for m in (g.get("members") or []):
            pid = m.get("id")
            if pid:
                pid = int(pid)
                player_counts[pid] += 1
                player_names[pid] = m.get("name", f"Игрок {pid}")

    # 1. Проверяем новые турниры основных команд (87812 и 98143)
    print(f"=== Шаг 1: Поиск новых турниров команд {TEAM_IDS} ===", flush=True)
    added_team = 0
    for team_id in TEAM_IDS:
        if str(team_id) not in team_names:
            t_meta = fetch_json(f"https://api.rating.chgk.info/teams/{team_id}")
            if isinstance(t_meta, dict) and t_meta.get("name"):
                team_names[str(team_id)] = t_meta["name"]

        t_list = fetch_json(f"https://api.rating.chgk.info/teams/{team_id}/tournaments")
        if not isinstance(t_list, list):
            continue

        for item in t_list:
            tid = item.get("idtournament") or item.get("tournamentId")
            if not tid:
                continue
            tid = int(tid)
            if tid in existing_tids:
                continue

            rec = build_game_record(tid, team_id, player_names, is_overlap=False)
            if rec:
                games.append(rec)
                existing_tids.add(tid)
                added_team += 1
                print(f"  + [{rec['dateEnd']}] {rec['name']} ({rec['taken']}/{rec['totalQuestions']})", flush=True)
            time.sleep(0.06)

    print(f"Новых игр основных команд: {added_team}", flush=True)

    # 2. Проверяем новые игры с пересечениями игроков основы
    print("=== Шаг 2: Поиск новых пересечений игроков основы ===", flush=True)
    core_players = [pid for pid, cnt in player_counts.items() if cnt >= MIN_CORE_GAMES]
    tt_players = defaultdict(set)
    for pid in core_players:
        resp = fetch_json(f"https://api.rating.chgk.info/players/{pid}/tournaments")
        if isinstance(resp, list):
            for item in resp:
                tid = item.get("idtournament") or item.get("tournamentId")
                team_id = item.get("idteam") or item.get("teamId")
                if tid and team_id:
                    tid, team_id = int(tid), int(team_id)
                    if tid not in existing_tids:
                        tt_players[(tid, team_id)].add(pid)
        time.sleep(0.05)

    added_overlap = 0
    for (tid, team_id), pids in tt_players.items():
        if len(pids) < MIN_OVERLAP_PLAYERS or tid in existing_tids:
            continue
        rec = build_game_record(tid, team_id, player_names, is_overlap=True)
        if rec:
            games.append(rec)
            existing_tids.add(tid)
            added_overlap += 1
            print(f"  + [пересечение {len(pids)} чел.] [{rec['dateEnd']}] {rec['name']}", flush=True)
        time.sleep(0.06)

    print(f"Новых игр с пересечениями: {added_overlap}", flush=True)

    # 3. Докачиваем TrueDL и редакторов для свежих игр и игр с пропусками
    print("=== Шаг 3: Обновление TrueDL и редакторов ===", flush=True)
    cutoff_date = (datetime.utcnow() - timedelta(days=RECENT_DAYS_REFRESH)).strftime("%Y-%m-%d")
    refreshed_games = 0
    for g in games:
        tid = get_tid(g)
        if tid is None:
            continue
        date_str = str(g.get("dateEnd") or "")[:10]
        needs_dl = (g.get("trueDL") is None) or bool(g.get("dlIsForecast")) or (date_str >= cutoff_date)
        needs_ed = not g.get("editors")
        if not (needs_dl or needs_ed):
            continue

        info = fetch_json(f"https://api.rating.chgk.info/tournaments/{tid}")
        if isinstance(info, dict):
            if needs_dl:
                new_true_dl = info.get("trueDL")
                new_forecast_dl = info.get("difficultyForecast")
                if new_forecast_dl is not None:
                    g["declaredDL"] = float(new_forecast_dl)
                if new_true_dl is not None:
                    g["trueDL"] = float(new_true_dl)
                    g["dlIsForecast"] = False
                elif new_forecast_dl is not None and g.get("trueDL") is None:
                    g["trueDL"] = float(new_forecast_dl)
                    g["dlIsForecast"] = True
            if needs_ed:
                eds = extract_editors_from_info(info, tid=tid)
                if eds:
                    g["editors"] = eds
            refreshed_games += 1
        time.sleep(0.05)

    print(f"Обновлено карточек турниров (TrueDL/редакторы): {refreshed_games}", flush=True)

    # 4. Обновляем актуальные личные рейтинги МАИИ
    print("=== Шаг 4: Обновление личных рейтингов МАИИ ===", flush=True)
    all_pids = sorted({int(m["id"]) for g in games for m in (g.get("members") or []) if m.get("id")})
    ratings_cache = {}
    for pid in all_pids:
        p_info = fetch_json(f"https://api.rating.chgk.info/players/{pid}")
        if isinstance(p_info, dict) and p_info.get("rating") is not None:
            ratings_cache[pid] = float(p_info["rating"])
        time.sleep(0.03)

    for g in games:
        for m in (g.get("members") or []):
            pid = m.get("id")
            if pid is not None and int(pid) in ratings_cache:
                m["playerRating"] = ratings_cache[int(pid)]

    # Сохраняем базу
    data["teamNames"] = team_names
    data["games"] = games
    with open(FILENAME, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"База '{FILENAME}' сохранена. Всего игр: {len(games)}.", flush=True)

    # 5. Пересобираем веб-прогноз index.html
    if os.path.exists("build_web_forecast.py"):
        print("=== Шаг 5: Пересборка index.html ===", flush=True)
        import build_web_forecast
        build_web_forecast.main()
    else:
        print("Внимание: build_web_forecast.py не найден рядом, index.html не пересобран.", flush=True)


if __name__ == "__main__":
    main()
