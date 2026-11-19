import json
import os
from datetime import datetime, timezone, timedelta

INPUT_JSON = "chgk_full_analytics.json"
OUTPUT_HTML = "index.html"

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Прогноз ЧГК • Симулятор результата команды</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background-color: #0f172a; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; }
    .card { background-color: #1e293b; border: 1px solid #334155; border-radius: 1rem; }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
  </style>
</head>
<body class="min-h-screen p-3 sm:p-6 flex flex-col items-center">
  <div class="w-full max-w-5xl space-y-4">
    <!-- Шапка -->
    <div class="card p-4 sm:p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
      <div>
        <div class="flex items-center gap-2.5 flex-wrap">
          <span class="text-2xl">🔮</span>
          <h1 id="teamTitle" class="text-xl sm:text-2xl font-bold text-white">Прогноз ЧГК</h1>
          <span class="px-2.5 py-0.5 text-[11px] font-semibold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Логистическая IRT-модель</span>
        </div>
        <p id="teamSubtitle" class="text-slate-400 text-xs sm:text-sm mt-1">Выберите состав, сложность пакета, дистанцию и редакторов</p>
        <p class="text-[11px] text-slate-500 mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-0.5">
          <span>🕒 Обновлено: <b class="text-slate-300">__LAST_UPDATED__</b></span>
          <span class="hidden sm:inline">•</span>
          <span>Автообновление: по вторникам в 12:00 МСК</span>
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2 w-full sm:w-auto justify-end">
        <span id="modelSampleBadge" class="px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-900 text-indigo-300 border border-slate-700">База: 0 игр</span>
        <a href="https://github.com/ALukmanov/chgk-prognoz/actions/workflows/update.yml" target="_blank" rel="noopener noreferrer" title="Запустить обновление базы на GitHub" class="text-xs bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 px-3 py-1.5 rounded-lg transition flex items-center gap-1">
          <span>🔄 Обновить рейтинг</span>
        </a>
        <button type="button" onclick="clearAll()" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-600 px-3 py-1.5 rounded-lg transition">
          Сбросить
        </button>
      </div>
    </div>

    <!-- Основной блок прогноза -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-5">
      <!-- Левая колонка: Настройки -->
      <div class="lg:col-span-6 space-y-4">
        <!-- 1. Игроки -->
        <div class="card p-4 space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-xs font-semibold text-slate-200 uppercase tracking-wider">1. Игроки за столом (<span id="simSelectedCount">0</span> / 6)</span>
            <span class="text-[11px] text-slate-400">От 1 до 6 чел.</span>
          </div>
          <div id="simulatorPlayerPool" class="flex flex-wrap gap-1.5 sm:gap-2 max-h-52 overflow-y-auto pr-1"></div>
        </div>

        <!-- 2. Сложность и 3. Дистанция -->
        <div class="card p-4 space-y-4">
          <div class="space-y-2">
            <div class="flex justify-between text-xs">
              <span class="text-slate-200 font-semibold uppercase tracking-wider">2. Сложность (TrueDL)</span>
              <span id="simDlLabel" class="font-bold text-indigo-300">3.5 (Рабочий)</span>
            </div>
            <input type="range" id="simDlSlider" min="1.5" max="8.5" value="3.5" step="0.1" oninput="updatePredictionOutput()" class="w-full accent-indigo-500 cursor-pointer" />
            <div class="flex justify-between text-[10px] text-slate-500">
              <span>1.5 (Лёгкий)</span>
              <span>3.5 (Рабочий)</span>
              <span>6.0 (Сложный)</span>
              <span>8.5 («Гроб»)</span>
            </div>
          </div>

          <div class="space-y-2 pt-3 border-t border-slate-700/70">
            <div class="flex justify-between items-center">
              <span class="text-xs text-slate-200 font-semibold uppercase tracking-wider">3. Дистанция (вопросов)</span>
            </div>
            <div id="distanceButtons" class="grid grid-cols-4 gap-1.5 sm:gap-2"></div>
          </div>

          <div class="space-y-2 pt-3 border-t border-slate-700/70">
            <div class="flex justify-between items-center gap-2">
              <span class="text-xs text-slate-200 font-semibold uppercase tracking-wider">4. Редакторы (<span id="simSelectedEditorsCount">0</span> / 6)</span>
              <button type="button" id="clearSimEditorsBtn" onclick="clearSimEditors()" class="hidden text-[11px] text-rose-300 hover:text-rose-200 underline">Сбросить</button>
            </div>
            <div id="simulatorEditorPool" class="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto pr-1"></div>
          </div>
        </div>
      </div>

      <!-- Правая колонка: Результат прогноза -->
      <div class="lg:col-span-6">
        <div class="card p-5 border-2 border-indigo-500/40 bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950/30 flex flex-col justify-between space-y-5 lg:sticky lg:top-6">
          <div class="space-y-4">
            <div class="flex items-center justify-between gap-2 flex-wrap">
              <div class="text-xs uppercase tracking-wider text-slate-400 font-semibold">Прогноз (<span id="simSeatBadge">0 игроков</span>)</div>
              <div id="simMatchedGamesText" class="text-[11px] text-slate-400">—</div>
            </div>

            <!-- 3 сценария -->
            <div class="grid grid-cols-3 gap-2.5 sm:gap-3">
              <div class="rounded-xl bg-amber-500/10 border border-amber-500/30 p-3 sm:p-4 text-center">
                <div class="text-[11px] font-semibold uppercase tracking-wide text-amber-300">Низкий</div>
                <div id="simLowQuestions" class="text-2xl sm:text-3xl font-extrabold text-amber-400 mt-1.5">—</div>
                <div id="simLowPct" class="text-xs text-amber-200/80 mt-1">—%</div>
                <div class="text-[10px] text-slate-400 mt-1">неудачный пакет</div>
              </div>

              <div class="rounded-xl bg-indigo-500/15 border-2 border-indigo-400/60 p-3 sm:p-4 text-center shadow-lg shadow-indigo-500/15">
                <div class="text-[11px] font-semibold uppercase tracking-wide text-indigo-300">Средний</div>
                <div id="simMidQuestions" class="text-3xl sm:text-4xl font-extrabold text-emerald-400 mt-1">—</div>
                <div id="simMidPct" class="text-xs font-semibold text-emerald-300 mt-1">—%</div>
                <div class="text-[10px] text-slate-300 mt-1">ожидаемый итог</div>
              </div>

              <div class="rounded-xl bg-emerald-500/10 border border-emerald-500/30 p-3 sm:p-4 text-center">
                <div class="text-[11px] font-semibold uppercase tracking-wide text-emerald-300">Высокий</div>
                <div id="simHighQuestions" class="text-2xl sm:text-3xl font-extrabold text-emerald-300 mt-1.5">—</div>
                <div id="simHighPct" class="text-xs text-emerald-200/80 mt-1">—%</div>
                <div class="text-[10px] text-slate-400 mt-1">удачный пакет</div>
              </div>
            </div>
          </div>

          <!-- Детали поправок -->
          <div class="space-y-2.5 pt-4 border-t border-slate-700/80 text-xs">
            <div class="flex justify-between items-start gap-3">
              <span class="text-slate-400 shrink-0">Состав:</span>
              <span id="simRosterSummary" class="font-medium text-slate-200 text-right">—</span>
            </div>
            <div class="flex justify-between items-center gap-3">
              <span class="text-slate-400 shrink-0">Поправка стола:</span>
              <span id="simSeatPenaltyText" class="font-semibold text-emerald-300 text-right">—</span>
            </div>
            <div class="flex justify-between items-center gap-3">
              <span class="text-slate-400 shrink-0">Поправка редакторов:</span>
              <span id="simEditorPenaltyText" class="font-semibold text-slate-300 text-right">0.0% (Другой редактор)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const EMBEDDED_DATA = __EMBEDDED_DATA__;
    const DISTANCES = [36, 45, 48, 60, 72, 75, 81, 90];
    const REF_DL = 3.5;

    let rawData = EMBEDDED_DATA;
    let kaznacheevId = null;
    let allPlayersPoolForSim = [];
    let simSelectedIds = new Set();
    let simOtherPlayersCount = 0;
    let simTotalQ = 36;

    let significantEditorsMap = new Map();
    let simEditorsAlphabetical = [];
    let simSelectedEditors = new Set();
    let simOtherEditorsCount = 0;

    function setText(id, val) {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    }

    function setHtml(id, val) {
      const el = document.getElementById(id);
      if (el) el.innerHTML = val;
    }

    function sigmoid(z) {
      if (z > 20) return 1 - 1e-9;
      if (z < -20) return 1e-9;
      return 1 / (1 + Math.exp(-z));
    }

    function logit(p) {
      const pc = Math.min(0.995, Math.max(0.005, p));
      return Math.log(pc / (1 - pc));
    }

    function solveLinearSystem(A, b) {
      const n = b.length;
      const M = A.map((row, i) => [...row, b[i]]);
      for (let i = 0; i < n; i++) {
        let maxRow = i;
        for (let k = i + 1; k < n; k++) {
          if (Math.abs(M[k][i]) > Math.abs(M[maxRow][i])) maxRow = k;
        }
        [M[i], M[maxRow]] = [M[maxRow], M[i]];
        if (Math.abs(M[i][i]) < 1e-10) continue;
        for (let k = i + 1; k < n; k++) {
          const factor = M[k][i] / M[i][i];
          for (let j = i; j <= n; j++) M[k][j] -= factor * M[i][j];
        }
      }
      const x = new Array(n).fill(0);
      for (let i = n - 1; i >= 0; i--) {
        let sum = M[i][n];
        for (let j = i + 1; j < n; j++) sum -= M[i][j] * x[j];
        x[i] = Math.abs(M[i][i]) > 1e-10 ? sum / M[i][i] : 0;
      }
      return x;
    }

    function logGamma(z) {
      const c = [76.18009172947146, -86.50532032941677, 24.01409824083091,
        -1.231739572450155, 0.001208650973866179, -0.000005395239384953];
      let x = z, y = z, tmp = x + 5.5;
      tmp -= (x + 0.5) * Math.log(tmp);
      let ser = 1.000000000190015;
      for (let j = 0; j < 6; j++) ser += c[j] / ++y;
      return -tmp + Math.log(2.5066282746310005 * ser / x);
    }

    function betacf(a, b, x) {
      const MAXIT = 100, EPS = 3e-7, FPMIN = 1e-30;
      let qab = a + b, qap = a + 1, qam = a - 1;
      let c = 1, d = 1 - qab * x / qap;
      if (Math.abs(d) < FPMIN) d = FPMIN;
      d = 1 / d;
      let h = d;
      for (let m = 1; m <= MAXIT; m++) {
        let m2 = 2 * m;
        let aa = m * (b - m) * x / ((qam + m2) * (a + m2));
        d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
        c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
        d = 1 / d; h *= d * c;
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2));
        d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
        c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
        d = 1 / d; let del = d * c; h *= del;
        if (Math.abs(del - 1.0) < EPS) break;
      }
      return h;
    }

    function betai(a, b, x) {
      if (x <= 0) return 0;
      if (x >= 1) return 1;
      const bt = Math.exp(logGamma(a + b) - logGamma(a) - logGamma(b) + a * Math.log(x) + b * Math.log(1 - x));
      if (x < (a + 1) / (a + b + 2)) return bt * betacf(a, b, x) / a;
      return 1 - bt * betacf(b, a, 1 - x) / b;
    }

    function welchTTest(arr1, arr2) {
      const n1 = arr1.length, n2 = arr2.length;
      if (n1 < 3 || n2 < 3) return { diff: 0, pValue: 1 };
      const m1 = arr1.reduce((a, b) => a + b, 0) / n1;
      const m2 = arr2.reduce((a, b) => a + b, 0) / n2;
      const v1 = arr1.reduce((s, x) => s + (x - m1) ** 2, 0) / (n1 - 1);
      const v2 = arr2.reduce((s, x) => s + (x - m2) ** 2, 0) / (n2 - 1);
      const se2 = (v1 / n1) + (v2 / n2);
      if (se2 <= 1e-9) return { diff: m1 - m2, pValue: 1 };
      const t = (m1 - m2) / Math.sqrt(se2);
      const df = (se2 ** 2) / (((v1 / n1) ** 2) / (n1 - 1) + ((v2 / n2) ** 2) / (n2 - 1));
      const pValue = betai(0.5 * df, 0.5, df / (df + t * t));
      return { diff: m1 - m2, pValue: Math.min(1, Math.max(0, pValue)) };
    }

    function fitIRTModel(games, lambdaVal = 10.0) {
      const playerIdsSet = new Set();
      games.forEach(g => (g.members || []).forEach(m => playerIdsSet.add(m.id)));
      const pIds = Array.from(playerIdsSet);
      const P = pIds.length;
      const N = games.length;

      games.forEach(g => {
        const r = g._rosterSize || 6;
        g._s5 = r === 5 ? 1 : 0;
        g._s4 = r === 4 ? 1 : 0;
        g._s3 = r === 3 ? 1 : 0;
        g._s2 = r <= 2 ? 1 : 0;
      });

      const defaultPen = { pen5: -0.09, pen4: -0.22, pen3: -0.40, pen2: -0.65 };
      const defaultDlSlope = -0.28;

      if (N < 6 || P === 0) {
        const avgP = N ? games.reduce((s, g) => s + g._teamPct / 100, 0) / N : 0.5;
        const baseL = logit(avgP);
        games.forEach(g => {
          g._normLogit = logit(g._teamPct / 100) - defaultDlSlope * (g._dl - REF_DL)
            - defaultPen.pen5 * g._s5 - defaultPen.pen4 * g._s4 - defaultPen.pen3 * g._s3 - defaultPen.pen2 * g._s2;
          g._normPct = sigmoid(g._normLogit) * 100;
        });
        return { baseLogitAtRefDl: baseL, refDl: REF_DL, dlSlope: defaultDlSlope, ...defaultPen, weights: new Map(), rmseLogit: 0.42 };
      }

      const idToIdx = new Map();
      pIds.forEach((id, idx) => idToIdx.set(id, idx));

      const dim = P + 6;
      const colInt = P, colDl = P + 1, colS5 = P + 2, colS4 = P + 3, colS3 = P + 4, colS2 = P + 5;
      const extraCols = [colInt, colDl, colS5, colS4, colS3, colS2];

      const avgPInit = games.reduce((s, g) => s + g._teamPct / 100, 0) / N;
      let theta = new Array(dim).fill(0);
      theta[colInt] = logit(avgPInit);
      theta[colDl] = defaultDlSlope;
      theta[colS5] = defaultPen.pen5;
      theta[colS4] = defaultPen.pen4;
      theta[colS3] = defaultPen.pen3;
      theta[colS2] = defaultPen.pen2;

      const priorMean = new Array(dim).fill(0);
      const priorPrec = new Array(dim).fill(lambdaVal);
      priorPrec[colInt] = 0.05; priorMean[colInt] = theta[colInt];
      priorPrec[colDl] = 2.0; priorMean[colDl] = defaultDlSlope;
      priorPrec[colS5] = 4.0; priorMean[colS5] = defaultPen.pen5;
      priorPrec[colS4] = 4.0; priorMean[colS4] = defaultPen.pen4;
      priorPrec[colS3] = 5.0; priorMean[colS3] = defaultPen.pen3;
      priorPrec[colS2] = 6.0; priorMean[colS2] = defaultPen.pen2;

      const gameData = games.map(g => {
        const q = Math.max(1, Number(g._totalQ) || 36);
        const effN = Math.min(45, q) / 3.0;
        const yRate = Math.min(0.995, Math.max(0.005, g._teamPct / 100));
        const active = [];
        (g.members || []).forEach(m => {
          const idx = idToIdx.get(m.id);
          if (idx !== undefined) active.push(idx);
        });
        return { g, effN, yRate, active, xExtra: [1.0, g._dl - REF_DL, g._s5, g._s4, g._s3, g._s2] };
      });

      for (let iter = 0; iter < 6; iter++) {
        const H = Array.from({ length: dim }, () => new Array(dim).fill(0));
        const grad = new Array(dim).fill(0);
        for (let i = 0; i < dim; i++) {
          H[i][i] = priorPrec[i];
          grad[i] = -priorPrec[i] * (theta[i] - priorMean[i]);
        }
        for (let k = 0; k < gameData.length; k++) {
          const gd = gameData[k];
          let eta = 0;
          for (let a = 0; a < gd.active.length; a++) eta += theta[gd.active[a]];
          for (let r = 0; r < 6; r++) eta += theta[extraCols[r]] * gd.xExtra[r];

          const p = sigmoid(eta);
          const w = gd.effN * Math.max(0.02, p * (1 - p));
          const resid = gd.effN * (gd.yRate - p);

          for (let r = 0; r < 6; r++) {
            const cr = extraCols[r];
            grad[cr] += resid * gd.xExtra[r];
            for (let c = r; c < 6; c++) {
              const cc = extraCols[c];
              const v = w * gd.xExtra[r] * gd.xExtra[c];
              H[cr][cc] += v;
              if (cr !== cc) H[cc][cr] += v;
            }
          }
          for (let a = 0; a < gd.active.length; a++) {
            const ia = gd.active[a];
            grad[ia] += resid;
            for (let r = 0; r < 6; r++) {
              const cr = extraCols[r];
              const v = w * gd.xExtra[r];
              H[ia][cr] += v; H[cr][ia] += v;
            }
            for (let b = a; b < gd.active.length; b++) {
              const ib = gd.active[b];
              H[ia][ib] += w;
              if (ia !== ib) H[ib][ia] += w;
            }
          }
        }
        const step = solveLinearSystem(H, grad);
        let maxStep = 0;
        for (let i = 0; i < dim; i++) {
          const d = Math.max(-1.5, Math.min(1.5, step[i]));
          theta[i] += d;
          if (Math.abs(d) > maxStep) maxStep = Math.abs(d);
        }
        if (maxStep < 1e-4) break;
      }

      const beta = theta.slice(0, P);
      const baseLogitAtRefDl = theta[colInt];
      let dlSlope = isFinite(theta[colDl]) ? Math.min(-0.08, Math.max(-0.65, theta[colDl])) : defaultDlSlope;
      let pen5 = isFinite(theta[colS5]) ? Math.min(0.0, Math.max(-0.45, theta[colS5])) : defaultPen.pen5;
      let pen4 = isFinite(theta[colS4]) ? Math.min(pen5 - 0.03, Math.max(-0.75, theta[colS4])) : Math.min(pen5 - 0.08, defaultPen.pen4);
      let pen3 = isFinite(theta[colS3]) ? Math.min(pen4 - 0.05, Math.max(-1.15, theta[colS3])) : Math.min(pen4 - 0.12, defaultPen.pen3);
      let pen2 = isFinite(theta[colS2]) ? Math.min(pen3 - 0.08, Math.max(-1.60, theta[colS2])) : Math.min(pen3 - 0.18, defaultPen.pen2);

      let ssLogit = 0;
      gameData.forEach(gd => {
        const g = gd.g;
        let predEta = baseLogitAtRefDl + dlSlope * (g._dl - REF_DL) + pen5 * g._s5 + pen4 * g._s4 + pen3 * g._s3 + pen2 * g._s2;
        gd.active.forEach(idx => { predEta += beta[idx]; });
        const obsEta = logit(gd.yRate);
        ssLogit += (obsEta - predEta) ** 2;
        g._normLogit = obsEta - dlSlope * (g._dl - REF_DL) - pen5 * g._s5 - pen4 * g._s4 - pen3 * g._s3 - pen2 * g._s2;
        g._normPct = sigmoid(g._normLogit) * 100;
      });

      const rmseLogit = Math.max(0.18, Math.min(0.85, Math.sqrt(ssLogit / N)));
      const weightsMap = new Map();
      pIds.forEach((id, idx) => weightsMap.set(id, beta[idx]));

      return { baseLogitAtRefDl, refDl: REF_DL, dlSlope, pen5, pen4, pen3, pen2, weights: weightsMap, rmseLogit };
    }

    function getSeatPenalty(model, seatCount) {
      if (seatCount >= 6) return 0;
      if (seatCount === 5) return model.pen5;
      if (seatCount === 4) return model.pen4;
      if (seatCount === 3) return model.pen3;
      return model.pen2;
    }

    function renderDistanceButtons() {
      setHtml("distanceButtons", DISTANCES.map(q => {
        const active = q === simTotalQ;
        return `<button type="button" onclick="setSimTotalQ(${q})" class="py-1.5 text-xs font-semibold rounded-lg border transition ${
          active
            ? "bg-indigo-600 text-white border-indigo-400 shadow"
            : "bg-slate-800 text-slate-300 border-slate-700 hover:border-slate-500"
        }">${q} вопр.</button>`;
      }).join(""));
    }

    function setSimTotalQ(q) {
      simTotalQ = q;
      renderDistanceButtons();
      updatePredictionOutput();
    }

    function toggleSimPlayer(id) {
      if (simSelectedIds.has(id)) {
        simSelectedIds.delete(id);
      } else {
        if (simSelectedIds.size + simOtherPlayersCount >= 6) {
          alert("За столом может быть не более 6 игроков.");
          return;
        }
        simSelectedIds.add(id);
      }
      renderSimulatorUI();
    }

    function addOtherPlayer() {
      if (simSelectedIds.size + simOtherPlayersCount >= 6) {
        alert("За столом может быть не более 6 игроков.");
        return;
      }
      simOtherPlayersCount++;
      renderSimulatorUI();
    }

    function removeOtherPlayer(event) {
      if (event) event.stopPropagation();
      if (simOtherPlayersCount > 0) {
        simOtherPlayersCount--;
        renderSimulatorUI();
      }
    }

    function toggleSimEditorByIdx(idx) {
      const ed = simEditorsAlphabetical[idx];
      if (!ed) return;
      if (simSelectedEditors.has(ed.name)) {
        simSelectedEditors.delete(ed.name);
      } else {
        if (simSelectedEditors.size + simOtherEditorsCount >= 6) {
          alert("Можно выбрать не более 6 редакторов.");
          return;
        }
        simSelectedEditors.add(ed.name);
      }
      renderSimEditorsUI();
      updatePredictionOutput();
    }

    function addOtherEditor() {
      if (simSelectedEditors.size + simOtherEditorsCount >= 6) {
        alert("Можно выбрать не более 6 редакторов.");
        return;
      }
      simOtherEditorsCount++;
      renderSimEditorsUI();
      updatePredictionOutput();
    }

    function removeOtherEditor(event) {
      if (event) event.stopPropagation();
      if (simOtherEditorsCount > 0) {
        simOtherEditorsCount--;
        renderSimEditorsUI();
        updatePredictionOutput();
      }
    }

    function clearSimEditors() {
      simSelectedEditors.clear();
      simOtherEditorsCount = 0;
      renderSimEditorsUI();
      updatePredictionOutput();
    }

    function clearAll() {
      simSelectedIds.clear();
      simOtherPlayersCount = 0;
      simSelectedEditors.clear();
      simOtherEditorsCount = 0;
      renderSimEditorsUI();
      renderSimulatorUI();
    }

    function renderSimEditorsUI() {
      const totalSelected = simSelectedEditors.size + simOtherEditorsCount;
      setText("simSelectedEditorsCount", totalSelected);
      const clearBtn = document.getElementById("clearSimEditorsBtn");
      if (clearBtn) clearBtn.classList.toggle("hidden", totalSelected === 0);

      let htmlBtns = simEditorsAlphabetical.map((e, idx) => {
        const active = simSelectedEditors.has(e.name);
        const sign = e.netEffect >= 0 ? "+" : "";
        const effColor = active ? "text-indigo-100" : (e.netEffect >= 0 ? "text-emerald-400" : "text-rose-400");
        return `<button type="button" onclick="toggleSimEditorByIdx(${idx})" class="px-2 py-1 rounded-lg text-[11px] font-medium border transition flex items-center gap-1 ${
          active
            ? "bg-indigo-600 border-indigo-400 text-white shadow"
            : "bg-slate-800/90 border-slate-700 text-slate-300 hover:border-slate-500"
        }">
          <span>${e.name}</span>
          <span class="text-[10px] font-mono ${effColor}">${sign}${e.netEffect.toFixed(1)}%</span>
        </button>`;
      }).join("");

      const otherActive = simOtherEditorsCount > 0;
      htmlBtns += `<button type="button" onclick="addOtherEditor()" class="px-2.5 py-1 rounded-lg text-[11px] font-medium border transition flex items-center gap-1.5 ${
        otherActive
          ? "bg-indigo-600 border-indigo-400 text-white shadow"
          : "bg-slate-800/90 border-slate-600 text-slate-300 hover:border-slate-400"
      }">
        <span>Другой редактор${otherActive ? " ×" + simOtherEditorsCount : ""}</span>
        ${otherActive ? `<span onclick="removeOtherEditor(event)" title="Убрать 1" class="ml-0.5 px-1 rounded bg-slate-900/50 hover:bg-slate-900 text-white font-bold">−</span>` : `<span class="text-[10px] opacity-60">0%</span>`}
      </button>`;

      setHtml("simulatorEditorPool", htmlBtns);
    }

    function renderSimulatorUI() {
      const totalSelectedPlayers = simSelectedIds.size + simOtherPlayersCount;
      setText("simSelectedCount", totalSelectedPlayers);
      const candidates = allPlayersPoolForSim.slice(0, 28);
      let poolHtml = candidates.map(p => {
        const active = simSelectedIds.has(p.id);
        const star = p.id === kaznacheevId ? "⭐ " : "";
        const shortN = (p.name || "").split(" ")[0] || "";
        return `<button type="button" onclick="toggleSimPlayer(${p.id})" class="px-2.5 py-1.5 rounded-lg text-xs font-medium border transition flex items-center gap-1.5 ${
          active
            ? "bg-indigo-600 border-indigo-400 text-white shadow"
            : "bg-slate-800/90 border-slate-700 text-slate-300 hover:border-slate-500"
        }">
          <span>${star}${shortN}</span>
          <span class="text-[10px] opacity-70">(${p.totalGames})</span>
        </button>`;
      }).join("");

      const otherPActive = simOtherPlayersCount > 0;
      poolHtml += `<button type="button" onclick="addOtherPlayer()" class="px-2.5 py-1.5 rounded-lg text-xs font-medium border transition flex items-center gap-1.5 ${
        otherPActive
          ? "bg-indigo-600 border-indigo-400 text-white shadow"
          : "bg-slate-800/90 border-slate-600 text-slate-300 hover:border-slate-400"
      }">
        <span>Другой игрок${otherPActive ? " ×" + simOtherPlayersCount : ""}</span>
        ${otherPActive ? `<span onclick="removeOtherPlayer(event)" title="Убрать 1" class="ml-0.5 px-1 rounded bg-slate-900/50 hover:bg-slate-900 text-white font-bold">−</span>` : `<span class="text-[10px] opacity-60">+1</span>`}
      </button>`;

      setHtml("simulatorPlayerPool", poolHtml);
      updatePredictionOutput();
    }

    function updatePredictionOutput() {
      const slider = document.getElementById("simDlSlider");
      const targetDl = slider ? (parseFloat(slider.value) || REF_DL) : REF_DL;
      let diffLabel = "Рабочий";
      if (targetDl < 2.8) diffLabel = "Лёгкий";
      else if (targetDl >= 6.5) diffLabel = "«Гроб»";
      else if (targetDl >= 4.8) diffLabel = "Сложный";
      setText("simDlLabel", `${targetDl.toFixed(1)} (${diffLabel})`);

      const selectedArr = Array.from(simSelectedIds);
      const seatCount = selectedArr.length + simOtherPlayersCount;
      const missingSeats = Math.max(0, 6 - seatCount);

      const seatBadge = document.getElementById("simSeatBadge");
      if (seatBadge) {
        if (seatCount === 6) {
          seatBadge.textContent = "6 игроков (полный стол)";
          seatBadge.className = "text-emerald-400 font-semibold";
        } else if (seatCount > 0) {
          seatBadge.textContent = `${seatCount} из 6 (некомплект -${missingSeats})`;
          seatBadge.className = "text-amber-400 font-semibold";
        } else {
          seatBadge.textContent = "0 игроков";
          seatBadge.className = "text-slate-400";
        }
      }

      const nameLookup = new Map();
      allPlayersPoolForSim.forEach(p => nameLookup.set(p.id, (p.name || "").split(" ")[0]));
      const rosterNamesList = selectedArr.map(id => nameLookup.get(id) || id);
      if (simOtherPlayersCount > 0) {
        rosterNamesList.push(simOtherPlayersCount > 1 ? `Другой игрок ×${simOtherPlayersCount}` : "Другой игрок");
      }
      setText("simRosterSummary", seatCount > 0 ? rosterNamesList.join(", ") : "не выбран");

      if (seatCount === 0) {
        ["simLowQuestions", "simMidQuestions", "simHighQuestions"].forEach(id => setText(id, "—"));
        ["simLowPct", "simMidPct", "simHighPct"].forEach(id => setText(id, "—%"));
        setText("simMatchedGamesText", "—");
        setText("simSeatPenaltyText", "—");
        setText("simEditorPenaltyText", "0.0% (Другой редактор)");
        return;
      }

      const selectedSet = new Set(selectedArr);
      const relevantGames = selectedArr.length > 0
        ? rawData.games.filter(g => (g.members || []).some(m => selectedSet.has(m.id)))
        : rawData.games;
      const exactOverlapGames = selectedArr.length > 0
        ? relevantGames.filter(g => {
            let overlap = 0;
            (g.members || []).forEach(m => { if (selectedSet.has(m.id)) overlap++; });
            return overlap >= Math.min(2, selectedArr.length);
          })
        : relevantGames;

      const localModel = fitIRTModel(relevantGames, 9.0);
      let sumPlayerLogits = 0;
      selectedArr.forEach(pid => { sumPlayerLogits += (localModel.weights.get(pid) || 0); });

      const dlShiftLogit = localModel.dlSlope * (targetDl - localModel.refDl);
      const seatPenaltyLogit = getSeatPenalty(localModel, seatCount);

      const totalEditorsSelected = simSelectedEditors.size + simOtherEditorsCount;
      let editorShiftPct = 0;
      let editorShiftLogit = 0;
      const selectedEdLabels = [];
      if (totalEditorsSelected > 0) {
        let sumEdEffects = 0;
        simSelectedEditors.forEach(edName => {
          const edInfo = significantEditorsMap.get(edName);
          if (edInfo) {
            sumEdEffects += edInfo.netEffect * 0.75;
            selectedEdLabels.push(edName.split(" ")[0]);
          }
        });
        if (simOtherEditorsCount > 0) {
          selectedEdLabels.push(simOtherEditorsCount > 1 ? `Другой ×${simOtherEditorsCount}` : "Другой");
        }
        editorShiftPct = sumEdEffects / totalEditorsSelected;
        editorShiftLogit = editorShiftPct / 23.0;
      }

      const baseEtaNoSeat = localModel.baseLogitAtRefDl + dlShiftLogit + editorShiftLogit + sumPlayerLogits;
      const midEta = baseEtaNoSeat + seatPenaltyLogit;
      const spreadLogit = 1.15 * localModel.rmseLogit;

      const lowPct = sigmoid(midEta - spreadLogit) * 100;
      const midPct = sigmoid(midEta) * 100;
      const highPct = sigmoid(midEta + spreadLogit) * 100;

      const seatPenaltyPct = (sigmoid(midEta) - sigmoid(baseEtaNoSeat)) * 100;
      const lowQ = (lowPct / 100) * simTotalQ;
      const midQ = (midPct / 100) * simTotalQ;
      const highQ = (highPct / 100) * simTotalQ;
      const seatPenaltyQ = (seatPenaltyPct / 100) * simTotalQ;
      const edPenaltyQ = ((sigmoid(midEta) - sigmoid(midEta - editorShiftLogit)) * 100 / 100) * simTotalQ;

      setText("simLowQuestions", `${lowQ.toFixed(1)}`);
      setText("simLowPct", `${lowPct.toFixed(1)}% из ${simTotalQ}`);
      setText("simMidQuestions", `${midQ.toFixed(1)}`);
      setText("simMidPct", `${midPct.toFixed(1)}% из ${simTotalQ}`);
      setText("simHighQuestions", `${highQ.toFixed(1)}`);
      setText("simHighPct", `${highPct.toFixed(1)}% из ${simTotalQ}`);
      setText("simMatchedGamesText", `Обучено: ${relevantGames.length} игр (${exactOverlapGames.length} совм.)`);

      const seatPenaltyEl = document.getElementById("simSeatPenaltyText");
      if (seatPenaltyEl) {
        if (missingSeats === 0) {
          seatPenaltyEl.textContent = "0.0% (полный стол 6 чел.)";
          seatPenaltyEl.className = "font-semibold text-emerald-300 text-right";
        } else {
          seatPenaltyEl.textContent = `${seatPenaltyPct.toFixed(1)}% (${seatPenaltyQ.toFixed(1)} вопр. за ${seatCount} чел.)`;
          seatPenaltyEl.className = "font-semibold text-amber-300 text-right";
        }
      }

      const edPenaltyEl = document.getElementById("simEditorPenaltyText");
      if (edPenaltyEl) {
        if (totalEditorsSelected === 0 || (simSelectedEditors.size === 0 && simOtherEditorsCount > 0)) {
          const suffix = simOtherEditorsCount > 1 ? `Другой редактор ×${simOtherEditorsCount}` : "Другой редактор";
          edPenaltyEl.textContent = `0.0% (${suffix})`;
          edPenaltyEl.className = "font-semibold text-slate-300 text-right";
        } else {
          const sign = editorShiftPct >= 0 ? "+" : "";
          edPenaltyEl.textContent = `${sign}${editorShiftPct.toFixed(1)}% (${sign}${edPenaltyQ.toFixed(1)} вопр. • ${selectedEdLabels.join(", ")})`;
          edPenaltyEl.className = editorShiftPct >= 0 ? "font-semibold text-emerald-300 text-right" : "font-semibold text-rose-300 text-right";
        }
      }
    }

    function initApp() {
      const names = Object.values(rawData.teamNames || {}).filter(Boolean).join(" + ");
      if (names) setText("teamTitle", names + " • Прогноз");
      setText("modelSampleBadge", `База: ${rawData.games.length} игр`);

      const pStats = new Map();
      rawData.games.forEach(g => {
        const totalQ = Number(g.totalQuestions) || 36;
        const takenQ = Number(g.taken) || 0;
        g._teamPct = totalQ > 0 ? (takenQ / totalQ) * 100 : 0;
        g._totalQ = totalQ;
        const mList = Array.isArray(g.members) ? g.members : [];
        g._rosterSize = mList.length > 0 ? Math.min(6, mList.length) : 6;
        if (typeof g.trueDL === "number" && g.trueDL > 0) {
          g._dl = g.trueDL;
        } else if (totalQ > 0 && Number(g.fieldAvg) > 0) {
          g._dl = Math.min(9.5, Math.max(1.0, +(8.2 - (Number(g.fieldAvg) / totalQ) * 8.5).toFixed(2)));
        } else {
          g._dl = REF_DL;
        }
        mList.forEach(m => {
          if (!m || !m.id) return;
          if (!kaznacheevId && (m.name || "").includes("Казначеев")) kaznacheevId = m.id;
          if (!pStats.has(m.id)) pStats.set(m.id, { id: m.id, name: m.name || ("Игрок " + m.id), totalGames: 0 });
          pStats.get(m.id).totalGames++;
        });
      });

      // Обучаем базовую IRT-модель на всей базе для расчёта значимых редакторов (от 5 игр)
      fitIRTModel(rawData.games, 18.0);
      const edMap = new Map();
      rawData.games.forEach(g => {
        (g.editors || []).forEach(name => {
          const s = String(name || "").trim();
          if (!s) return;
          if (!edMap.has(s)) edMap.set(s, { name: s, gamesCnt: 0, normVals: [] });
          edMap.get(s).gamesCnt++;
          edMap.get(s).normVals.push(g._normPct);
        });
      });
      const allNorms = rawData.games.map(g => g._normPct);
      const baseline = allNorms.length ? allNorms.reduce((a, b) => a + b, 0) / allNorms.length : 50;

      const sigEditors = [];
      edMap.forEach(e => {
        const normPct = e.normVals.reduce((a, b) => a + b, 0) / e.gamesCnt;
        const netEffect = normPct - baseline;
        const tTest = welchTTest(e.normVals, allNorms);
        if (e.gamesCnt >= 5 && (tTest.pValue < 0.15 || Math.abs(netEffect) >= 4.5)) {
          sigEditors.push({ name: e.name, gamesCnt: e.gamesCnt, netEffect });
        }
      });

      sigEditors.forEach(e => significantEditorsMap.set(e.name, e));
      simEditorsAlphabetical = sigEditors.sort((a, b) => a.name.localeCompare(b.name, "ru"));

      allPlayersPoolForSim = Array.from(pStats.values())
        .filter(p => p.totalGames >= 5)
        .sort((a, b) => b.totalGames - a.totalGames);

      // По умолчанию подставляем 6 самых частых игроков, чтобы при открытии сразу были видны цифры
      allPlayersPoolForSim.slice(0, 6).forEach(p => simSelectedIds.add(p.id));

      renderDistanceButtons();
      renderSimEditorsUI();
      renderSimulatorUI();
    }

    window.addEventListener("DOMContentLoaded", initApp);
  </script>
</body>
</html>
"""

def main():
    if not os.path.exists(INPUT_JSON):
        print(f"Ошибка: файл '{INPUT_JSON}' не найден в текущей папке.")
        return

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Оставляем только нужные для прогноза поля (убираем маски и лишнее, чтобы страница грузилась мгновенно)
    slim_games = []
    for g in raw.get("games", []):
        editors = []
        if isinstance(g.get("editors"), list):
            for ed in g["editors"]:
                if isinstance(ed, str) and ed.strip():
                    editors.append(ed.strip())
                elif isinstance(ed, dict):
                    p = ed.get("player") or ed
                    full = " ".join(str(p.get(k) or "").strip() for k in ["surname", "name", "patronymic"] if p.get(k)).strip()
                    if full:
                        editors.append(full)
        slim_games.append({
            "taken": g.get("taken", 0),
            "totalQuestions": g.get("totalQuestions", 36),
            "trueDL": g.get("trueDL"),
            "fieldAvg": g.get("fieldAvg", 0),
            "editors": editors,
            "members": [{"id": m.get("id"), "name": m.get("name", "")} for m in (g.get("members") or []) if m.get("id")]
        })

    payload = {
        "teamNames": raw.get("teamNames", {}),
        "games": slim_games
    }

    json_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    msk_now = datetime.now(timezone(timedelta(hours=3))).strftime("%d.%m.%Y %H:%M МСК")
    final_html = (
        HTML_TEMPLATE
        .replace("__EMBEDDED_DATA__", json_str)
        .replace("__LAST_UPDATED__", msk_now)
    )

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"ГОТОВО! Создан автономный веб-файл '{OUTPUT_HTML}' ({len(final_html) // 1024} КБ).")
    print("Теперь просто перетащи папку с 'index.html' на https://app.netlify.com/drop и получи ссылку для друзей!")

if __name__ == "__main__":
    main()
