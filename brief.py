#!/usr/bin/env python3
"""
Daily video-distribution market brief — cloud edition (Gemini brain).

Runs headless in GitHub Actions: Gemini (with Google Search grounding) researches
two streams, returns structured JSON, and this script renders it into a dated HTML
page. build_calendar.py then rebuilds the clickable calendar. The workflow commits
the result back to the repo.

Env: GEMINI_API_KEY (free key from Google AI Studio, stored as a GitHub Secret).
"""
import os, re, json, glob, html, datetime as dt

from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash"   # free tier. "gemini-3.5-flash" = newer if available.
ROOT = os.getcwd()
DIGEST_DIR = os.path.join(ROOT, "digests")
TEMPLATE = os.path.join(ROOT, "day_template.html")
SOURCES = os.path.join(ROOT, "sources.md")

def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()

def previous_date():
    dates = []
    for p in glob.glob(os.path.join(DIGEST_DIR, "*.html")):
        m = re.search(r"(\d{4}-\d{2}-\d{2})\.html$", p)
        if m:
            dates.append(m.group(1))
    return max(dates) if dates else None

def ask_gemini(watchlist, today, prev):
    prompt = f"""You are a market-intelligence analyst. Using web search, build today's
video-distribution market brief for {today}. Geography: global + Asia + Ukraine/CIS.
Recency: only developments from the last 7 days{f' (newer than the {prev} brief)' if prev else ''}.
EXCLUDE AIR Media-Tech from all analysis. Do NOT fabricate — if a stream is quiet, say so.

Watchlist and signals:
{watchlist}

Return ONLY valid JSON (no markdown fences), with this exact shape:
{{
  "tldr": "2-4 sentences, the single most important thing today",
  "bars": [{{"label": "Competitor moves", "n": 0}}, {{"label": "Algorithm changes", "n": 0}}, {{"label": "Funding / M&A", "n": 0}}],
  "stream_a": [{{"source": "...", "title": "...", "why": "one line why it matters", "url": "https://..."}}],
  "stream_b": [{{"source": "...", "title": "...", "why": "...", "url": "https://..."}}],
  "changed": "what is new vs the previous brief, or 'First brief — no prior baseline.'",
  "conclusions": ["implication for Holywater BizDev", "..."],
  "sources": [{{"label": "...", "url": "https://..."}}]
}}
Bars numbers must match the count of items you list. Mark anything unconfirmed with [VERIFY] inside the text."""

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.3,
        ),
    )
    return resp.text or ""

def parse_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    # grab the outermost JSON object if there's stray prose
    a, b = t.find("{"), t.rfind("}")
    if a != -1 and b != -1:
        t = t[a:b + 1]
    return json.loads(t)

def esc(s):
    return html.escape(str(s), quote=False)

def render_items(items):
    if not items:
        return "<li>No significant developments in this stream today.</li>"
    out = []
    for it in items:
        url = it.get("url", "")
        link = f' <a href="{esc(url)}" target="_blank">↗</a>' if url else ""
        out.append(
            f'<li><b>{esc(it.get("source",""))} — {esc(it.get("title",""))}</b>{link}'
            f'<span class="why">{esc(it.get("why",""))}</span></li>'
        )
    return "".join(out)

def render_bars(bars):
    nums = [max(0, int(b.get("n", 0))) for b in bars] or [0]
    top = max(nums) or 1
    out = []
    for b in bars:
        n = max(0, int(b.get("n", 0)))
        pct = int(100 * n / top)
        out.append(
            f'<div class="bar"><span>{esc(b.get("label",""))}</span>'
            f'<span class="track"><span class="fill" style="width:{pct}%"></span></span>'
            f'<span class="n">{n}</span></div>'
        )
    return "".join(out)

def render_sources(sources):
    if not sources:
        return "—"
    return "".join(
        f'<a href="{esc(s.get("url",""))}" target="_blank">{esc(s.get("label","source"))}</a>'
        for s in sources
    )

def main():
    today = dt.date.today().isoformat()
    today_human = dt.date.today().strftime("%A, %d %B %Y")
    prev = previous_date()
    watchlist = read(SOURCES)

    raw = ask_gemini(watchlist, today, prev)
    try:
        data = parse_json(raw)
    except Exception as e:
        print(f"JSON parse failed ({e}); writing raw fallback.")
        data = {"tldr": "Automated parse failed — raw model output below.",
                "bars": [], "stream_a": [{"source": "raw", "title": raw[:400], "why": "", "url": ""}],
                "stream_b": [], "changed": "", "conclusions": [], "sources": []}

    page = read(TEMPLATE)
    repl = {
        "{{DATE_ISO}}": today,
        "{{DATE_HUMAN}}": today_human,
        "{{TLDR}}": esc(data.get("tldr", "")),
        "{{BARS}}": render_bars(data.get("bars", [])),
        "{{STREAM_A}}": render_items(data.get("stream_a", [])),
        "{{STREAM_B}}": render_items(data.get("stream_b", [])),
        "{{CHANGED}}": esc(data.get("changed", "")) or "First brief — no prior baseline.",
        "{{CONCLUSIONS}}": "".join(f"<li>{esc(c)}</li>" for c in data.get("conclusions", [])) or "<li>—</li>",
        "{{SOURCES}}": render_sources(data.get("sources", [])),
        "{{GENERATED_AT}}": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }
    for k, v in repl.items():
        page = page.replace(k, v)

    os.makedirs(DIGEST_DIR, exist_ok=True)
    out = os.path.join(DIGEST_DIR, f"{today}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {out}")

if __name__ == "__main__":
    main()
