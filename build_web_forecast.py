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
    body { background-color: #0f172a; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; overflow-x: hidden; }
    .card { background-color: #1e293b; border: 1px solid #334155; border-radius: 1rem; }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }

    /* Анимации филина */
    @keyframes owl-peek {
      0% { transform: translate(110%, 110%) rotate(14deg); }
      15% { transform: translate(8px, 8px) rotate(-4deg); }
      22% { transform: translate(0, 0) rotate(0deg); }
      78% { transform: translate(0, 0) rotate(0deg); }
      85% { transform: translate(8px, 8px) rotate(-4deg); }
      100% { transform: translate(110%, 110%) rotate(14deg); }
    }

    @keyframes bubble-fade {
      0% { opacity: 0; transform: scale(0.85) translateY(8px); }
      10% { opacity: 1; transform: scale(1) translateY(0); }
      90% { opacity: 1; transform: scale(1) translateY(0); }
      100% { opacity: 0; transform: scale(0.85) translateY(8px); }
    }

    .owl-container {
      position: fixed;
      bottom: -8px;
      right: -6px;
      z-index: 100;
      cursor: pointer;
      transform: translate(110%, 110%) rotate(14deg);
      transition: transform 0.45s ease;
      user-select: none;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      pointer-events: auto;
    }

    .owl-container.active {
      animation: owl-peek 8s cubic-bezier(0.25, 1, 0.5, 1) forwards;
    }

    .owl-container.clicked {
      transform: translate(0, 0) rotate(0deg) !important;
      animation: none !important;
    }

    .speech-bubble {
      background-color: #f1f5f9;
      color: #0f172a;
      padding: 9px 12px;
      border-radius: 14px;
      font-size: 13px;
      font-weight: 600;
      width: 185px;
      max-width: calc(100vw - 28px);
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.55);
      border: 2px solid #6366f1;
      opacity: 0;
      pointer-events: none;
      transform-origin: bottom right;
      margin-bottom: 6px;
      margin-right: 18px;
      position: relative;
      line-height: 1.25;
    }

    @media (max-width: 640px) {
      .speech-bubble {
        width: 155px;
        font-size: 11.5px;
        padding: 7px 10px;
        margin-right: 12px;
      }
    }

    .speech-bubble::after {
      content: '';
      position: absolute;
      bottom: -8px;
      right: 26px;
      border-width: 8px 8px 0;
      border-style: solid;
      border-color: #f1f5f9 transparent;
    }

    .speech-bubble::before {
      content: '';
      position: absolute;
      bottom: -11px;
      right: 25px;
      border-width: 9px 9px 0;
      border-style: solid;
      border-color: #6366f1 transparent;
      z-index: -1;
    }

    .speech-bubble.show {
      animation: bubble-fade 4.5s ease forwards;
    }

    /* Анимации спящего кота по центру */
    @keyframes cat-breathe {
      0%, 100% { transform: scale(1, 1); }
      50% { transform: scale(1.03, 0.97); }
    }

    @keyframes cat-zzz {
      0% { opacity: 0; transform: translate(0, 4px) scale(0.8); }
      40% { opacity: 1; }
      100% { opacity: 0; transform: translate(10px, -16px) scale(1.15); }
    }

    @keyframes cat-run-away {
      0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
      18% { transform: translate(-50%, -78%) scale(1.12) rotate(-8deg); opacity: 1; }
      35% { transform: translate(-45%, -52%) scale(1.04) rotate(6deg); opacity: 1; }
      100% { transform: translate(160vw, -58%) scale(0.85) rotate(14deg); opacity: 0; }
    }

    .cat-overlay {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%) scale(0.7);
      z-index: 120;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.6s ease, transform 0.6s cubic-bezier(0.22, 1, 0.36, 1);
      cursor: pointer;
      user-select: none;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .cat-overlay.visible {
      opacity: 1;
      transform: translate(-50%, -50%) scale(1);
      pointer-events: auto;
    }

    .cat-overlay.scared {
      pointer-events: none;
      animation: cat-run-away 0.85s cubic-bezier(0.45, 0, 0.85, 0.5) forwards;
    }

    .cat-body-breathe {
      transform-origin: center bottom;
      animation: cat-breathe 2.6s ease-in-out infinite;
    }

    .cat-zzz-1 { animation: cat-zzz 2.8s ease-in-out infinite; }
    .cat-zzz-2 { animation: cat-zzz 2.8s ease-in-out 1.4s infinite; }
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
          <span class="px-2.5 py-0.5 text-[11px] font-semibold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Логистическая IRT-модель • Time Decay 1.5 г.</span>
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
        <button type="button" onclick="clearAll()" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-600 px-3 py-1.5 rounded-lg transition">
          Сбросить
        </button>
      </div>
    </div>

    <!-- Основной блок прогноза -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-5">
      <!-- Левая колонка: Настройки -->
      <div class="lg:col-span-6 space-y-4">
        <div class="card p-4 space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-xs font-semibold text-slate-200 uppercase tracking-wider">1. Игроки за столом (<span id="simSelectedCount">0</span> / 6)</span>
            <span class="text-[11px] text-slate-400">От 1 до 6 чел.</span>
          </div>
          <div id="simulatorPlayerPool" class="flex flex-wrap gap-1.5 sm:gap-2 max-h-52 overflow-y-auto pr-1"></div>
        </div>

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

  <!-- Персонаж 1: Филин во фраке и очках (облачко жёстко привязано к нему) -->
  <div id="owlContainer" class="owl-container" onclick="onOwlClick()">
    <div id="speechBubble" class="speech-bubble">А кто-нибудь помнит форму вопроса?</div>
    <svg viewBox="0 0 150 150" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-28 h-28 sm:w-36 sm:h-36 drop-shadow-2xl">
      <!-- Фрак и плечи -->
      <path d="M24 146 C26 98, 124 98, 126 146 Z" fill="#18181b" stroke="#09090b" stroke-width="2.5" />
      <path d="M52 104 L98 104 L75 142 Z" fill="#f8fafc" />
      <!-- Лацканы фрака -->
      <path d="M52 104 L38 118 L54 128 L68 142" fill="#27272a" stroke="#09090b" stroke-width="2" />
      <path d="M98 104 L112 118 L96 128 L82 142" fill="#27272a" stroke="#09090b" stroke-width="2" />
      <!-- Бабочка -->
      <path d="M62 107 L75 113 L62 119 Z" fill="#09090b" />
      <path d="M88 107 L75 113 L88 119 Z" fill="#09090b" />
      <circle cx="75" cy="113" r="3.5" fill="#18181b" stroke="#09090b" stroke-width="1.5" />
      <!-- Пуговицы -->
      <circle cx="75" cy="126" r="1.8" fill="#0f172a" />
      <circle cx="75" cy="134" r="1.8" fill="#0f172a" />

      <!-- Длинные пучки-ушки филина -->
      <path d="M40 46 L16 20 L48 34 L34 26 L56 38 Z" fill="#7c4a21" stroke="#1c1108" stroke-width="2.5" stroke-linejoin="round" />
      <path d="M110 46 L134 20 L102 34 L116 26 L94 38 Z" fill="#7c4a21" stroke="#1c1108" stroke-width="2.5" stroke-linejoin="round" />
      <path d="M22 24 L38 38 M128 24 L112 38" stroke="#1c1108" stroke-width="2.5" stroke-linecap="round" />

      <!-- Голова филина (пёстрая) -->
      <ellipse cx="75" cy="68" rx="40" ry="36" fill="#9a6434" stroke="#1c1108" stroke-width="3" />
      <!-- Светлый лицевой диск -->
      <path d="M41 66 C41 48, 66 48, 75 62 C84 48, 109 48, 109 66 C109 88, 92 98, 75 96 C58 98, 41 88, 41 66 Z" fill="#c99762" />
      <!-- Тёмные пестрины на лбу и щеках -->
      <path d="M62 38 L65 44 M75 35 L75 43 M88 38 L85 44 M54 44 L59 49 M96 44 L91 49" stroke="#29170a" stroke-width="3" stroke-linecap="round" />
      <path d="M44 82 L49 87 M54 90 L58 94 M106 82 L101 87 M96 90 L92 94" stroke="#29170a" stroke-width="2.5" stroke-linecap="round" />

      <!-- Огненно-оранжевые глаза филина -->
      <circle cx="57" cy="66" r="13.5" fill="#f97316" stroke="#1c1108" stroke-width="2.5" />
      <circle cx="57" cy="66" r="10.5" fill="#fb923c" />
      <circle id="owlPupilL" cx="58" cy="66" r="5.5" fill="#09090b" />
      <circle cx="54.5" cy="62.5" r="2" fill="#ffffff" />

      <circle cx="93" cy="66" r="13.5" fill="#f97316" stroke="#1c1108" stroke-width="2.5" />
      <circle cx="93" cy="66" r="10.5" fill="#fb923c" />
      <circle id="owlPupilR" cx="92" cy="66" r="5.5" fill="#09090b" />
      <circle cx="88.5" cy="62.5" r="2" fill="#ffffff" />

      <!-- Суровые брови филина -->
      <path id="owlBrowL" d="M40 53 L71 61" stroke="#29170a" stroke-width="4.5" stroke-linecap="round" />
      <path id="owlBrowR" d="M110 53 L79 61" stroke="#29170a" stroke-width="4.5" stroke-linecap="round" />

      <!-- Круглые очки в тёмной оправе -->
      <circle cx="57" cy="66" r="16.5" stroke="#1e293b" stroke-width="3.5" fill="none" />
      <circle cx="93" cy="66" r="16.5" stroke="#1e293b" stroke-width="3.5" fill="none" />
      <path d="M73.5 66 L76.5 66" stroke="#1e293b" stroke-width="3.5" />

      <!-- Тёмный крючковатый клюв -->
      <path id="owlBeak" d="M70 71 Q75 68 80 71 L75 88 Z" fill="#1e293b" stroke="#09090b" stroke-width="2" stroke-linejoin="round" />

      <!-- Когтистая лапа на краю -->
      <path d="M114 108 C126 104, 138 112, 134 126 C128 134, 114 134, 110 124 Z" fill="#9a6434" stroke="#1c1108" stroke-width="2.5" />
      <path d="M132 110 L141 112 M134 118 L143 120 M131 126 L139 128" stroke="#18181b" stroke-width="3" stroke-linecap="round" />
    </svg>
  </div>

  <!-- Персонаж 2: Мурчащий кот (появляется по центру после 60 сек бездействия) -->
  <div id="catOverlay" class="cat-overlay" onclick="scareCat()">
    <div class="px-3 py-1 rounded-full bg-slate-900/90 border border-indigo-500/40 text-[11px] text-indigo-200 mb-1 shadow-lg">
      Мур-р-р... (нажми, чтобы прогнать)
    </div>
    <svg viewBox="0 0 220 175" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-[70vw] max-w-[360px] sm:w-[44vw] sm:max-w-[460px] h-auto drop-shadow-2xl">
      <!-- Zzz -->
      <text x="112" y="34" fill="#cbd5e1" font-size="16" font-weight="700" class="cat-zzz-1">Z</text>
      <text x="132" y="24" fill="#94a3b8" font-size="12" font-weight="700" class="cat-zzz-2">z</text>

      <!-- Подушка -->
      <ellipse cx="110" cy="128" rx="84" ry="34" fill="#475569" stroke="#1e293b" stroke-width="3.5" />
      <ellipse cx="110" cy="124" rx="74" ry="26" fill="#64748b" />

      <g class="cat-body-breathe">
        <!-- Пушистое тело клубком -->
        <ellipse cx="122" cy="100" rx="54" ry="38" fill="#d6ccc2" stroke="#29170a" stroke-width="3" />
        <!-- Рыжее пятно на спине -->
        <path d="M105 64 C132 60, 162 72, 168 96 C150 92, 130 96, 114 106 Z" fill="#e6a16b" />
        <!-- Пушистый хвост -->
        <path d="M168 104 C180 132, 128 148, 86 134 C78 130, 80 116, 94 118 C122 124, 152 118, 156 100 Z" fill="#e6a16b" stroke="#29170a" stroke-width="3" stroke-linejoin="round" />
        <path d="M84 128 C78 122, 86 114, 100 118 L98 133 C92 134, 86 132, 84 128 Z" fill="#fff7ed" />

        <!-- Голова кота -->
        <circle cx="78" cy="86" r="30" fill="#fff7ed" stroke="#29170a" stroke-width="3" />
        <!-- Рыжие ушки и шапочка -->
        <path d="M52 72 L46 42 L72 58 Z" fill="#e6a16b" stroke="#29170a" stroke-width="3" stroke-linejoin="round" />
        <path d="M53 66 L50 50 L65 59 Z" fill="#fda4af" />
        <path d="M86 58 L108 42 L106 72 Z" fill="#e6a16b" stroke="#29170a" stroke-width="3" stroke-linejoin="round" />
        <path d="M92 59 L104 50 L102 66 Z" fill="#fda4af" />
        <path d="M50 78 C54 56, 80 52, 92 64 C84 68, 76 74, 72 80 C64 76, 56 76, 50 78 Z" fill="#e6a16b" />

        <!-- Спящие глаза (по умолчанию) -->
        <g id="catEyesSleep">
          <path d="M60 86 Q66 80 72 86" stroke="#29170a" stroke-width="3" stroke-linecap="round" />
          <path d="M84 86 Q90 80 96 86" stroke="#29170a" stroke-width="3" stroke-linecap="round" />
        </g>

        <!-- Испуганные глаза (при клике) -->
        <g id="catEyesScared" style="display:none;">
          <circle cx="66" cy="84" r="6.5" fill="#fef08a" stroke="#29170a" stroke-width="2.5" />
          <circle cx="66" cy="84" r="2.2" fill="#09090b" />
          <circle cx="90" cy="84" r="6.5" fill="#fef08a" stroke="#29170a" stroke-width="2.5" />
          <circle cx="90" cy="84" r="2.2" fill="#09090b" />
        </g>

        <!-- Носик и рот -->
        <path d="M75 92 L81 92 L78 96 Z" fill="#fb7185" />
        <path id="catMouth" d="M71 98 Q74.5 102 78 97 Q81.5 102 85 98" stroke="#29170a" stroke-width="2.5" stroke-linecap="round" />

        <!-- Усы -->
        <path d="M44 88 L56 90 M42 96 L56 95 M112 88 L100 90 M114 96 L100 95" stroke="#29170a" stroke-width="2" stroke-linecap="round" />
        <!-- Лапка под мордой -->
        <ellipse cx="64" cy="116" rx="13" ry="8" fill="#fff7ed" stroke="#29170a" stroke-width="2.5" />
      </g>
    </svg>
  </div>

  <script>
    const EMBEDDED_DATA = __EMBEDDED_DATA__;
    const DISTANCES = [36, 45, 48, 60, 72, 75, 81, 90];
    const REF_DL = 3.5;
    const HALF_LIFE_DAYS = 547.5; // 1.5 года (~75 игр при темпе 1 игра/нед.)

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

    // --- Филин ---
    const owlPhrases = [
      { text: "Я в сМЯКении!", mood: "shock" },
      { text: "Где мой сидр?", mood: "angry" },
      { text: "Зачем я это записал?", mood: "confused" },
      { text: "Сейчас трезвый дядя всё расскажет", mood: "tired" },
      { text: "А кто-нибудь помнит форму вопроса?", mood: "question" }
    ];

    let owlTimer = null;
    let owlHideTimer = null;
    let isOwlActive = false;

    function triggerOwlPeek() {
      if (isOwlActive || isCatVisible) return;
      const owl = document.getElementById("owlContainer");
      if (!owl) return;

      isOwlActive = true;
      owl.className = "owl-container active";
      setOwlMood("normal");

      owlTimer = setTimeout(() => {
        if (owl.classList.contains("active") && !owl.classList.contains("clicked")) {
          owl.className = "owl-container";
          isOwlActive = false;
        }
      }, 8000);
    }

    function onOwlClick() {
      const owl = document.getElementById("owlContainer");
      const bubble = document.getElementById("speechBubble");
      if (!owl || !bubble) return;

      clearTimeout(owlTimer);
      clearTimeout(owlHideTimer);

      owl.className = "owl-container clicked";
      const rand = owlPhrases[Math.floor(Math.random() * owlPhrases.length)];
      bubble.textContent = rand.text;
      setOwlMood(rand.mood);

      bubble.classList.remove("show");
      void bubble.offsetWidth;
      bubble.classList.add("show");

      owlHideTimer = setTimeout(() => {
        owl.className = "owl-container";
        bubble.classList.remove("show");
        isOwlActive = false;
      }, 4500);
    }

    function setOwlMood(mood) {
      const pupilL = document.getElementById("owlPupilL");
      const pupilR = document.getElementById("owlPupilR");
      const beak = document.getElementById("owlBeak");
      const browL = document.getElementById("owlBrowL");
      const browR = document.getElementById("owlBrowR");
      if (!pupilL || !pupilR || !beak) return;

      // Сброс базовых позиций
      pupilL.setAttribute("r", "5.5"); pupilL.setAttribute("cx", "58"); pupilL.setAttribute("cy", "66");
      pupilR.setAttribute("r", "5.5"); pupilR.setAttribute("cx", "92"); pupilR.setAttribute("cy", "66");
      beak.setAttribute("d", "M70 71 Q75 68 80 71 L75 88 Z");
      if (browL) browL.setAttribute("d", "M40 53 L71 61");
      if (browR) browR.setAttribute("d", "M110 53 L79 61");

      if (mood === "shock") {
        pupilL.setAttribute("r", "2.5"); pupilL.setAttribute("cx", "57");
        pupilR.setAttribute("r", "2.5"); pupilR.setAttribute("cx", "93");
        beak.setAttribute("d", "M68 72 L82 72 L75 92 Z");
        if (browL) browL.setAttribute("d", "M42 48 L68 52");
        if (browR) browR.setAttribute("d", "M108 48 L82 52");
      } else if (mood === "angry") {
        pupilL.setAttribute("cx", "60");
        pupilR.setAttribute("cx", "90");
        if (browL) browL.setAttribute("d", "M40 50 L72 64");
        if (browR) browR.setAttribute("d", "M110 50 L78 64");
      } else if (mood === "confused") {
        pupilL.setAttribute("cx", "61"); pupilL.setAttribute("cy", "64");
        pupilR.setAttribute("cx", "89"); pupilR.setAttribute("cy", "68");
        if (browL) browL.setAttribute("d", "M42 50 L70 56");
        if (browR) browR.setAttribute("d", "M108 56 L80 58");
      } else if (mood === "tired") {
        pupilL.setAttribute("r", "4"); pupilL.setAttribute("cy", "69");
        pupilR.setAttribute("r", "4"); pupilR.setAttribute("cy", "69");
        if (browL) browL.setAttribute("d", "M42 58 L70 59");
        if (browR) browR.setAttribute("d", "M108 58 L80 59");
      }
    }

    // --- Мурчащий кот (60 сек бездействия) ---
    let idleTimer = null;
    let isCatVisible = false;
    let audioCtx = null;
    let purrNodes = null;

    function unlockAudio() {
      try {
        if (!audioCtx) {
          const AC = window.AudioContext || window.webkitAudioContext;
          if (AC) audioCtx = new AC();
        }
        if (audioCtx && audioCtx.state === "suspended") {
          audioCtx.resume();
        }
      } catch (e) {}
    }

    function startPurrSound() {
      try {
        unlockAudio();
        if (!audioCtx || audioCtx.state !== "running") return;
        stopPurrSound();

        // Мягкий синтез мурчания: 26 Гц основной тон + модуляция дыханием (0.4 Гц)
        const osc = audioCtx.createOscillator();
        osc.type = "sawtooth";
        osc.frequency.value = 26;

        const filter = audioCtx.createBiquadFilter();
        filter.type = "lowpass";
        filter.frequency.value = 135;

        const breathLfo = audioCtx.createOscillator();
        breathLfo.type = "sine";
        breathLfo.frequency.value = 0.38;

        const breathGain = audioCtx.createGain();
        breathGain.gain.value = 0.045;

        const masterGain = audioCtx.createGain();
        masterGain.gain.value = 0.075;

        osc.connect(filter);
        filter.connect(masterGain);
        breathLfo.connect(breathGain);
        breathGain.connect(masterGain.gain);
        masterGain.connect(audioCtx.destination);

        osc.start();
        breathLfo.start();
        purrNodes = { osc, breathLfo, masterGain };
      } catch (e) {}
    }

    function stopPurrSound() {
      if (!purrNodes) return;
      try {
        purrNodes.osc.stop();
        purrNodes.breathLfo.stop();
        purrNodes.masterGain.disconnect();
      } catch (e) {}
      purrNodes = null;
    }

    function showPurringCat() {
      const cat = document.getElementById("catOverlay");
      if (!cat || isCatVisible) return;
      isCatVisible = true;
      const sleepEyes = document.getElementById("catEyesSleep");
      const scaredEyes = document.getElementById("catEyesScared");
      const mouth = document.getElementById("catMouth");
      if (sleepEyes) sleepEyes.style.display = "block";
      if (scaredEyes) scaredEyes.style.display = "none";
      if (mouth) mouth.setAttribute("d", "M71 98 Q74.5 102 78 97 Q81.5 102 85 98");

      cat.className = "cat-overlay visible";
      startPurrSound();
    }

    function scareCat() {
      const cat = document.getElementById("catOverlay");
      if (!cat || !isCatVisible) return;
      stopPurrSound();

      const sleepEyes = document.getElementById("catEyesSleep");
      const scaredEyes = document.getElementById("catEyesScared");
      const mouth = document.getElementById("catMouth");
      if (sleepEyes) sleepEyes.style.display = "none";
      if (scaredEyes) scaredEyes.style.display = "block";
      if (mouth) mouth.setAttribute("d", "M74 101 Q78 96 82 101");

      cat.className = "cat-overlay visible scared";
      setTimeout(() => {
        cat.className = "cat-overlay";
        isCatVisible = false;
        resetIdleTimer();
      }, 900);
    }

    function resetIdleTimer() {
      unlockAudio();
      if (isCatVisible) return; // Если кот уже на экране, ждём клика по нему
      clearTimeout(idleTimer);
      idleTimer = setTimeout(showPurringCat, 60000);
    }

    ["click", "touchstart", "mousemove", "keydown", "scroll"].forEach(evt => {
      window.addEventListener(evt, resetIdleTimer, { passive: true });
    });

    // --- Утилиты и IRT-модель ---
    function formatShortName(fullName) {
      const parts = (fullName || "").trim().split(/\s+/).filter(Boolean);
      if (parts.length === 0) return "";
      if (parts.length === 1) return parts[0];
      return `${parts[0]} ${parts[1][0]}.`;
    }

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

      let sumWP = 0, sumWInit = 0;
      games.forEach(g => {
        const tw = typeof g._timeW === "number" ? g._timeW : 1.0;
        sumWP += tw * (g._teamPct / 100);
        sumWInit += tw;
      });
      const avgPInit = sumWInit > 0 ? sumWP / sumWInit : 0.5;
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
        const tw = typeof g._timeW === "number" ? g._timeW : 1.0;
        const effN = (Math.min(45, q) / 3.0) * tw;
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
      let sumTimeW = 0;
      gameData.forEach(gd => {
        const g = gd.g;
        const tw = typeof g._timeW === "number" ? g._timeW : 1.0;
        let predEta = baseLogitAtRefDl + dlSlope * (g._dl - REF_DL) + pen5 * g._s5 + pen4 * g._s4 + pen3 * g._s3 + pen2 * g._s2;
        gd.active.forEach(idx => { predEta += beta[idx]; });
        const obsEta = logit(gd.yRate);
        ssLogit += tw * (obsEta - predEta) ** 2;
        sumTimeW += tw;
        g._normLogit = obsEta - dlSlope * (g._dl - REF_DL) - pen5 * g._s5 - pen4 * g._s4 - pen3 * g._s3 - pen2 * g._s2;
        g._normPct = sigmoid(g._normLogit) * 100;
      });

      const rmseLogit = Math.max(0.18, Math.min(0.85, Math.sqrt(ssLogit / Math.max(1e-6, sumTimeW))));
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
        const shortN = formatShortName(p.name);
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
      allPlayersPoolForSim.forEach(p => nameLookup.set(p.id, formatShortName(p.name)));
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

      let maxDateMs = 0;
      rawData.games.forEach(g => {
        const ts = g.date ? Date.parse(g.date) : NaN;
        g._ts = isFinite(ts) ? ts : null;
        if (g._ts && g._ts > maxDateMs) maxDateMs = g._ts;
      });

      const pStats = new Map();
      rawData.games.forEach(g => {
        if (maxDateMs > 0 && g._ts) {
          const ageDays = Math.max(0, (maxDateMs - g._ts) / 86400000);
          g._timeW = Math.pow(0.5, ageDays / HALF_LIFE_DAYS);
        } else {
          g._timeW = 1.0;
        }
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

      allPlayersPoolForSim.slice(0, 6).forEach(p => simSelectedIds.add(p.id));

      renderDistanceButtons();
      renderSimEditorsUI();
      renderSimulatorUI();

      // Запуск филина раз в 20–25 секунд и таймера бездействия для кота
      function scheduleNextOwl() {
        const delay = 20000 + Math.floor(Math.random() * 5000);
        setTimeout(() => {
          triggerOwlPeek();
          scheduleNextOwl();
        }, delay);
      }
      scheduleNextOwl();
      resetIdleTimer();
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
            "date": str(g.get("dateEnd") or g.get("dateStart") or "")[:10],
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

if __name__ == "__main__":
    main()
