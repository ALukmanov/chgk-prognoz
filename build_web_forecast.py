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
    <div class="