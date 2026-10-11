#!/usr/bin/env python3
"""Pulls each player's Tennis Abstract classic page and the courtspeed.com tables
into data/*.json using a headless browser (the pages are drawn by JavaScript).

  python scraper/scrape.py                 # courts + top 100 players
  python scraper/scrape.py --top 200
  python scraper/scrape.py --only FrancesTiafoe BenShelton
  python scraper/scrape.py --debug --only FrancesTiafoe   # also saves raw tables
"""
import argparse, datetime as dt, json, pathlib, re, sys, time

ROOT = pathlib.Path(_file_).resolve().parent.parent
DATA = ROOT / "data"
TA = "https://www.tennisabstract.com/cgi-bin/player-classic.cgi?p={}"
COURT_PAGES = {"cpi": "https://courtspeed.com/", "ace": "https://courtspeed.com/ace-rate",
               "rally": "https://courtspeed.com/rally-length", "weather": "https://courtspeed.com/weather-altitude"}
TABS = ["Last 52 Weeks Splits", "Career Splits", "Charting: Serve", "Charting: Return",
        "Charting: Rally", "Charting: Tactics", "Head-to-Heads"]

DUMP_JS = r"""() => [...document.querySelectorAll('table')].map(t =>
  [...t.rows].map(r => [...r.cells].map(c => c.innerText.trim().replace(/\s+/g, ' ')))
).filter(rows => rows.length > 1)"""
TEXT_JS = "() => document.body.innerText.slice(0, 6000)"

# ---- parsing (pure functions, tested without a browser) -------------------------------
def classify(rows):
    """Return (key, header_row_index) from the header cells, or (None, None)."""
    for i, row in enumerate(rows[:4]):
        t = set(row)
        if {"Date", "Tournament", "Surface"} <= t: return "recent", i
        if "Year" in t and "Hld%" in t: return "seasons", i
        if "Split" in t and "Hld%" in t: return "splits", i
        if "SvImpact" in t: return "ch_serve", i
        if "RDI" in t and "RetWnr%" in t: return "ch_return", i
        if "RallyLen" in t: return "ch_rally", i
        if "SnV Freq" in t: return "ch_tactics", i
        if "Opponent" in t and "Mtgs" in t: return "h2h", i
    return None, None

def records(rows, hi):
    head = list(rows[hi]); body = [r for r in rows[hi + 1:] if len(r) >= 2]
    if body and len(body[0]) == len(head) + 1: head = ["Match"] + head
    seen, names = {}, []
    for h in head:
        seen[h] = seen.get(h, 0) + 1
        names.append(h if seen[h] == 1 else f"{h}_{seen[h]}")
    return [dict(zip(names, r)) for r in body]

def num(s):
    m = re.search(r"-?\d+(?:\.\d+)?", str(s).replace(",", ""))
    return float(m.group()) if m else None

def parse_player(tables, body_text):
    out, splits = {}, []
    for rows in tables:
        key, hi = classify(rows)
        if not key: continue
        recs = records(rows, hi)
        if key == "splits": splits.append(recs)
        elif key not in out: out[key] = recs
    # The two split tables are Last-52 and Career; the career one has more matches.
    def total(recs): return sum(num(r.get("M")) or 0 for r in recs)
    if splits:
        splits.sort(key=total)
        out["splits_last52"] = splits[0]
        out["splits_career"] = splits[-1] if len(splits) > 1 else []
    info = {}
    for k, rx in {"rank": r"Current rank[^\d]{0,5}(\d+)", "peak": r"Peak rank[^\d]{0,5}(\d+)",
                  "elo_rank": r"Elo rank[^\d]{0,5}(\d+)", "elo": r"Elo rank[^\d]{0,5}\d+[^\d]{1,15}(\d{3,4})",
                  "age": r"Age[^\d]{0,5}(\d{2})"}.items():
        m = re.search(rx, body_text or "")
        if m: info[k] = int(m.group(1))
    m = re.search(r"Plays:?\s*(Right|Left)", body_text or "")
    if m: info["hand"] = m.group(1)
    out["info"] = info
    return out

def parse_court_table(rows):
    if not rows: return None
    hi = 0
    for i, r in enumerate(rows[:3]):
        if len(r) > 4: hi = i; break
    return {"headers": rows[hi], "rows": rows[hi + 1:]}

# ---- browser --------------------------------------------------------------------------
def dump_page(page, click=()):
    for name in click:
        try:
            page.get_by_text(name, exact=True).first.click(timeout=2500)
            page.wait_for_timeout(350)
        except Exception:
            pass
    return page.evaluate(DUMP_JS), page.evaluate(TEXT_JS)

def scrape_player(page, slug):
    last = None
    for attempt in range(2):
        try:
            page.goto(TA.format(slug), wait_until="load", timeout=60000)
            page.wait_for_selector("table", state="attached", timeout=45000)
            page.wait_for_timeout(2500)
            tables, text = dump_page(page, TABS)
            data = parse_player(tables, text)
            if "recent" not in data or not data.get("seasons"):
                raise RuntimeError("page loaded but expected tables missing; tables found: %d" % len(tables))
            return data, tables
        except Exception as e:
            last = e
            try:
                title = page.title()
                snippet = page.evaluate("() => document.body.innerText.slice(0, 250)").replace("\n", " ")
                print(f"  diag [{slug}] title={title!r} body={snippet!r}", flush=True)
            except Exception:
                pass
            if attempt == 0: page.wait_for_timeout(8000)
    raise last

def scrape_courts(page):
    courts = {}
    for key, url in COURT_PAGES.items():
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            tables, _ = dump_page(page)
            best = max(tables, key=len) if tables else None
            courts[key] = parse_court_table(best) if best else None
        except Exception as e:
            courts[key] = None; print(f"  courts/{key}: {e}", file=sys.stderr)
    courts["fetched_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    return courts

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=100)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--delay", type=float, default=4.0, help="seconds between players")
    ap.add_argument("--no-courts", action="store_true")
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright
    seed = json.load(open(ROOT / "scraper" / "players_seed.json"))["players"]
    todo = [p for p in seed if (p["slug"] in a.only if a.only else p["rank"] <= a.top)]
    (DATA / "players").mkdir(parents=True, exist_ok=True)
    errors = {}; streak = 0
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        page = br.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", locale="en-US").new_page()
        if not a.no_courts:
            (DATA / "courts.json").write_text(json.dumps(scrape_courts(page)))
        for p in todo:
            try:
                data, raw = scrape_player(page, p["slug"])
                data.update(name=p["name"], slug=p["slug"], fetched_at=dt.datetime.now(dt.timezone.utc).isoformat())
                (DATA / "players" / f"{p['slug']}.json").write_text(json.dumps(data))
                if a.debug: (DATA / f"raw_{p['slug']}.json").write_text(json.dumps(raw))
                print("ok  ", p["name"], flush=True); streak = 0
            except Exception as e:
                errors[p["slug"]] = str(e)[:200]; streak += 1; print("FAIL", p["name"], str(e)[:120], flush=True)
                if streak >= 5: print("5 failures in a row, stopping. See diag lines above.", flush=True); break
            time.sleep(a.delay)
        br.close()
    # index: every seed player, flagged when we hold data for them
    idx = []
    for p in seed:
        f = DATA / "players" / f"{p['slug']}.json"
        item = dict(p, has_data=f.exists())
        if f.exists():
            d = json.load(open(f)); item["fetched_at"] = d.get("fetched_at"); item["ta_rank"] = d.get("info", {}).get("rank")
        idx.append(item)
    (DATA / "index.json").write_text(json.dumps({"updated": dt.datetime.now(dt.timezone.utc).isoformat(), "players": idx}))
    (DATA / "errors.json").write_text(json.dumps(errors, indent=1))
    print(f"done: {len(todo) - len(errors)} ok, {len(errors)} failed")

if _name_ == "_main_":
    main()
