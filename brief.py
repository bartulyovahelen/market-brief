#!/usr/bin/env python3
"""
Щоденний бриф ринку відеодистрибуції — хмарна версія (мозок: Gemini).

Працює headless у GitHub Actions: Gemini (з пошуком Google) досліджує ринок,
повертає структуру, скрипт малює україномовну сторінку дня + зберігає сирий JSON.
Тренди визначаються з історії кількох останніх днів. build_calendar.py збирає
клікабельний календар. Workflow комітить результат назад у репозиторій.

Env: GEMINI_API_KEY (безкоштовний ключ з Google AI Studio, GitHub Secret).
"""
import os, re, json, glob, html, time, datetime as dt

from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash"          # безкоштовний рівень. "gemini-3.5-flash" — новіший, якщо доступний.
FALLBACK_MODEL = "gemini-2.5-flash-lite"  # запасна, легша модель — рідше перевантажена
MAX_TRIES = 4                       # скільки разів пробувати, якщо Gemini відповів "зайнято"
HISTORY_DAYS = 5               # скільки попередніх днів читати для трендів
ROOT = os.getcwd()
DIGEST_DIR = os.path.join(ROOT, "digests")
TEMPLATE = os.path.join(ROOT, "day_template.html")
SOURCES = os.path.join(ROOT, "sources.md")

IMP_CLASS = {"high": "imp-high", "medium": "imp-med", "low": "imp-low"}
IMP_ORDER = {"high": 0, "medium": 1, "low": 2}

def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()

def history():
    """Останні HISTORY_DAYS JSON-дайджестів (без сьогоднішнього) для трендів і 'що змінилось'."""
    files = sorted(glob.glob(os.path.join(DIGEST_DIR, "*.json")), reverse=True)
    items = []
    for p in files[:HISTORY_DAYS]:
        try:
            d = json.load(open(p, encoding="utf-8"))
            date = re.search(r"(\d{4}-\d{2}-\d{2})", p).group(1)
            titles = [s.get("title", "") for s in d.get("signals", [])][:6]
            items.append(f"{date}: {d.get('tldr','')} | " + " · ".join(titles))
        except Exception:
            pass
    return "\n".join(items)

def ask_gemini(watchlist, today, hist):
    prompt = f"""Ти — аналітик ринку відеодистрибуції. Звіт пиши УКРАЇНСЬКОЮ.
Назви компаній/продуктів і посилання-джерела лишай в оригіналі (не перекладай).
Аналізуй ВЕСЬ ринок відеодистрибуції нейтрально, без прив'язки до конкретної компанії.
ВИКЛЮЧИ AIR Media-Tech з аналізу. Не вигадуй — якщо тема порожня, так і скажи.
Через пошук знайди події за останні 7 днів. Дата сьогодні: {today}.

Що відстежувати (watchlist і сигнали):
{watchlist}

Контекст останніх днів (для трендів і розділу «що змінилось»):
{hist or "— історії ще немає, це перший бриф —"}

Поверни ЛИШЕ валідний JSON (без markdown-огорожі) такої форми:
{{
  "tldr": "2-3 речення: найважливіше за сьогодні",
  "bars": [{{"label": "Монетизація", "n": 0}}, {{"label": "Алгоритми", "n": 0}}, {{"label": "Контент", "n": 0}}, {{"label": "M&A / фандинг", "n": 0}}],
  "signals": [
    {{"importance": "high|medium|low",
      "theme": "монетизація|алгоритми|контент|M&A|регуляції|продукт",
      "stream": "конкурент|платформа",
      "source": "оригінальна назва джерела/компанії",
      "title": "стислий заголовок українською",
      "why": "один рядок: чому це важливо для ринку",
      "url": "https://..."}}
  ],
  "trends": ["напрям ніші за останні дні, не одна новина", "..."],
  "regions": [{{"region": "Захід", "note": "один рядок або 'без помітних рухів'"}}, {{"region": "Азія", "note": "..."}}, {{"region": "CIS", "note": "..."}}],
  "changed": "що нового проти попередніх днів, або 'Перший бриф — бази для порівняння ще нема.'",
  "bizdev": ["можливість або дія для BizDev у відеодистрибуції загалом", "..."],
  "watch_next": ["що варто моніторити найближчими днями", "..."],
  "sources": [{{"label": "оригінальна назва", "url": "https://..."}}]
}}
Сортуй signals від high до low. Числа в bars мають збігатися з кількістю пунктів.
Неперевірене познач [VERIFY]."""

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    cfg = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.3,
    )
    last_err = None
    for attempt in range(MAX_TRIES):
        # на останній спробі переходимо на запасну, легшу модель
        model = MODEL if attempt < MAX_TRIES - 1 else FALLBACK_MODEL
        try:
            resp = client.models.generate_content(model=model, contents=prompt, config=cfg)
            return resp.text or ""
        except Exception as e:
            last_err = e
            msg = str(e)
            transient = any(s in msg for s in (
                "503", "UNAVAILABLE", "overloaded", "high demand",
                "429", "RESOURCE_EXHAUSTED", "500", "INTERNAL"))
            if attempt < MAX_TRIES - 1 and transient:
                wait = 8 * (attempt + 1)   # 8с, 16с, 24с
                print(f"Gemini зайнятий ({msg[:80]}...) — спроба {attempt+2}/{MAX_TRIES} через {wait}с")
                time.sleep(wait)
                continue
            raise
    raise last_err

def parse_json(text):
    t = re.sub(r"^```(?:json)?", "", text.strip()).strip()
    t = re.sub(r"```$", "", t).strip()
    a, b = t.find("{"), t.rfind("}")
    if a != -1 and b != -1:
        t = t[a:b + 1]
    return json.loads(t)

def esc(s):
    return html.escape(str(s), quote=False)

def render_signals(signals):
    if not signals:
        return "<li>Сьогодні без помітних сигналів.</li>"
    sig = sorted(signals, key=lambda s: IMP_ORDER.get(s.get("importance", "low"), 2))
    out = []
    for s in sig:
        cls = IMP_CLASS.get(s.get("importance", "low"), "imp-low")
        url = s.get("url", "")
        link = f' <a href="{esc(url)}" target="_blank">↗</a>' if url else ""
        theme = esc(s.get("theme", ""))
        stream = esc(s.get("stream", ""))
        out.append(
            f'<li class="sig"><span class="dot {cls}"></span><div class="sig-body">'
            f'<div class="sig-head"><b>{esc(s.get("source",""))} — {esc(s.get("title",""))}</b>{link}</div>'
            f'<div class="meta"><span class="chip">{theme}</span>'
            f'<span class="chip ghost">{stream}</span></div>'
            f'<span class="why">{esc(s.get("why",""))}</span></div></li>'
        )
    return "".join(out)

def render_bars(bars):
    nums = [max(0, int(b.get("n", 0))) for b in bars] or [0]
    top = max(nums) or 1
    out = []
    for b in bars:
        n = max(0, int(b.get("n", 0)))
        out.append(
            f'<div class="bar"><span>{esc(b.get("label",""))}</span>'
            f'<span class="track"><span class="fill" style="width:{int(100*n/top)}%"></span></span>'
            f'<span class="n">{n}</span></div>'
        )
    return "".join(out)

def render_list(items, empty="—"):
    if not items:
        return f"<li>{empty}</li>"
    return "".join(f"<li>{esc(x)}</li>" for x in items)

def render_sources(sources):
    if not sources:
        return "—"
    return "".join(
        f'<a href="{esc(s.get("url",""))}" target="_blank">{esc(s.get("label","джерело"))}</a>'
        for s in sources
    )

def render_regions(regions):
    if not regions:
        return '<div class="reg"><b>—</b><span>—</span></div>'
    return "".join(
        f'<div class="reg"><b>{esc(r.get("region",""))}</b>'
        f'<span>{esc(r.get("note",""))}</span></div>'
        for r in regions
    )

def main():
    today = dt.date.today().isoformat()
    today_human = dt.date.today().strftime("%d.%m.%Y")
    watchlist = read(SOURCES)
    hist = history()

    raw = ask_gemini(watchlist, today, hist)
    try:
        data = parse_json(raw)
    except Exception as e:
        print(f"JSON parse failed ({e}); raw fallback.")
        data = {"tldr": "Автоматичний розбір не вдався — нижче сирий вивід.",
                "bars": [], "signals": [{"importance": "low", "theme": "—", "stream": "—",
                "source": "raw", "title": raw[:300], "why": "", "url": ""}],
                "trends": [], "changed": "", "bizdev": [], "watch_next": [], "sources": []}

    # сирий JSON — для трендів наступних днів
    os.makedirs(DIGEST_DIR, exist_ok=True)
    with open(os.path.join(DIGEST_DIR, f"{today}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    page = read(TEMPLATE)
    repl = {
        "{{DATE_ISO}}": today,
        "{{DATE_HUMAN}}": today_human,
        "{{TLDR}}": esc(data.get("tldr", "")),
        "{{BARS}}": render_bars(data.get("bars", [])),
        "{{SIGNALS}}": render_signals(data.get("signals", [])),
        "{{TRENDS}}": render_list(data.get("trends", [])),
        "{{REGIONS}}": render_regions(data.get("regions", [])),
        "{{CHANGED}}": esc(data.get("changed", "")) or "Перший бриф — бази для порівняння ще нема.",
        "{{BIZDEV}}": render_list(data.get("bizdev", [])),
        "{{WATCH}}": render_list(data.get("watch_next", [])),
        "{{SOURCES}}": render_sources(data.get("sources", [])),
        "{{GENERATED_AT}}": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }
    for k, v in repl.items():
        page = page.replace(k, v)

    with open(os.path.join(DIGEST_DIR, f"{today}.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote digests/{today}.html and .json")

if __name__ == "__main__":
    main()
