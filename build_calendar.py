#!/usr/bin/env python3
"""Scan ./digests/*.html and (re)build ./index.html — a clickable month calendar.

Each date that has a digest file becomes a clickable cell linking to that day's page.
Run after writing a new digest. Stdlib only.
"""
import os, re, glob, calendar, datetime as dt

ROOT = os.getcwd()
DIGEST_DIR = os.path.join(ROOT, "digests")
OUT = os.path.join(ROOT, "index.html")
DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})\.html$")

def collected_dates():
    days = set()
    for p in glob.glob(os.path.join(DIGEST_DIR, "*.html")):
        m = DATE_RE.search(os.path.basename(p))
        if m:
            days.add(dt.date(int(m[1]), int(m[2]), int(m[3])))
    return days

def month_grid(year, month, days_with_digest, today):
    cal = calendar.Calendar(firstweekday=0)  # Monday
    cells = []
    for d in cal.itermonthdates(year, month):
        if d.month != month:
            cells.append('<div class="cell out"></div>')
            continue
        iso = d.isoformat()
        cls = "cell"
        if d == today:
            cls += " today"
        if d in days_with_digest:
            cells.append(f'<a class="{cls} has" href="digests/{iso}.html">'
                         f'<span class="dn">{d.day}</span><span class="dot"></span></a>')
        else:
            cells.append(f'<div class="{cls}"><span class="dn">{d.day}</span></div>')
    head = "".join(f'<div class="dow">{w}</div>' for w in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
    title = f"{calendar.month_name[month]} {year}"
    return (f'<section class="month"><h2>{title}</h2>'
            f'<div class="grid">{head}{"".join(cells)}</div></section>')

def build():
    days = collected_dates()
    today = dt.date.today()
    months = sorted({(d.year, d.month) for d in days}, reverse=True)
    if (today.year, today.month) not in months:
        months.insert(0, (today.year, today.month))
    body = "".join(month_grid(y, m, days, today) for (y, m) in months)
    latest = max(days) if days else None
    latest_link = (f'<a class="latest" href="digests/{latest.isoformat()}.html">'
                   f'Open latest brief ({latest.isoformat()}) →</a>') if latest else ""
    html = TEMPLATE.replace("{{BODY}}", body).replace("{{LATEST}}", latest_link)\
                   .replace("{{COUNT}}", str(len(days)))\
                   .replace("{{UPDATED}}", dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"index.html rebuilt — {len(days)} digest(s).")

TEMPLATE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Market Brief — Calendar</title><style>
:root{--bg:#0f1216;--card:#171b21;--line:#262c35;--ink:#e8ecf1;--mut:#9aa6b2;
--accent:#5b9dff;--accent2:#7ee0c0}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:760px;margin:0 auto;padding:36px 20px 64px}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--mut);font-size:14px;margin-bottom:20px}
.latest{display:inline-block;margin:0 0 24px;color:var(--accent);text-decoration:none;font-size:15px}
.month{margin:28px 0}.month h2{font-size:14px;text-transform:uppercase;letter-spacing:.08em;
color:var(--mut);margin:0 0 12px}
.grid{display:grid;grid-template-columns:repeat(7,1fr);gap:6px}
.dow{color:var(--mut);font-size:11px;text-align:center;padding-bottom:4px}
.cell{aspect-ratio:1/1;border:1px solid var(--line);border-radius:9px;background:var(--card);
display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--mut);
position:relative;text-decoration:none}
.cell.out{border:none;background:transparent}
.cell .dn{font-size:14px}
.cell.has{color:var(--ink);border-color:#33405a;cursor:pointer}
.cell.has:hover{border-color:var(--accent);background:#1c2230}
.cell.has .dot{width:6px;height:6px;border-radius:50%;
background:linear-gradient(90deg,var(--accent),var(--accent2));margin-top:5px}
.cell.today{box-shadow:inset 0 0 0 1px var(--accent2)}
.foot{color:var(--mut);font-size:12px;margin-top:32px;border-top:1px solid var(--line);padding-top:14px}
</style></head><body><div class="wrap">
<h1>Video-Distribution Market Brief</h1>
<div class="sub">Daily competitor &amp; platform digest · click a highlighted day to open it</div>
{{LATEST}}
{{BODY}}
<div class="foot">{{COUNT}} digest(s) · updated {{UPDATED}} · highlighted days have a brief</div>
</div></body></html>"""

if __name__ == "__main__":
    os.makedirs(DIGEST_DIR, exist_ok=True)
    build()
