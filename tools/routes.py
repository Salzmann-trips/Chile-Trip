#!/usr/bin/env python3
"""Calculate road routes for each day of the suggested route (OSRM), for the planner's map.

Usage:  python3 tools/routes.py <export_dir> <out.json>

Reads <export_dir>/items/*.json, trip/settings.json, trip/suggestion.json and, if present,
trip/suggestion_routes.json (the routes stored last time). Only days whose stops changed are
recalculated. Writes <out.json> as {"days": {date: {key, km, h, geom}}, "computedAt": ...} and prints
"updated", "unchanged" or "routing unavailable". The day points must match sgDayRoute() in the pages.
"""
import json, sys, math, time, pathlib, datetime, urllib.request

OSRM = "https://router.project-osrm.org/route/v1/driving/"


def body(path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw["data"] if isinstance(raw, dict) and isinstance(raw.get("data"), dict) else raw


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    gfile = src / "trip" / "suggestion.json"
    if not gfile.exists():
        print("unchanged"); return
    sg = body(gfile)
    settings = body(src / "trip" / "settings.json") if (src / "trip" / "settings.json").exists() else {}
    factor = float(settings.get("factor") or 1.35)
    items = {}
    for f in (src / "items").glob("*.json"):
        d = body(f); items[f.stem] = d
    old = {}
    rfile = src / "trip" / "suggestion_routes.json"
    if rfile.exists():
        old = (body(rfile) or {}).get("days", {}) or {}

    def has_loc(i):
        try:
            return i is not None and i.get("lat") not in (None, "") and i.get("lng") not in (None, "") and math.isfinite(float(i["lat"])) and math.isfinite(float(i["lng"]))
        except (TypeError, ValueError):
            return False

    def km(a, b):
        r = math.radians
        dlat, dlng = r(float(b["lat"]) - float(a["lat"])), r(float(b["lng"]) - float(a["lng"]))
        h = math.sin(dlat / 2) ** 2 + math.cos(r(float(a["lat"]))) * math.cos(r(float(b["lat"]))) * math.sin(dlng / 2) ** 2
        return 2 * 6371 * math.asin(math.sqrt(h)) * factor

    stages = sg.get("stages") or []
    by_id = {s.get("id"): s for s in stages}
    wanted = {}
    for si, st in enumerate(stages):
        for di, day in enumerate(st.get("days") or []):
            start = None
            if di == 0 and si > 0:
                start = stages[si - 1]
            elif not (si == 0 and di == 0):
                start = st
            if si > 0 and di == 0 and any(d.get("endStage") == st.get("id") for d in stages[si - 1].get("days") or []):
                start = st
            tour = set(day.get("tour") or [])
            stops = [items[i] for i in day.get("stops") or [] if i not in tour and has_loc(items.get(i))]
            end = None
            if not day.get("noReturn"):
                end = by_id.get(day.get("endStage")) if day.get("endStage") else st
            raw = [p for p in [start, *stops, end] if p is not None]
            pts = [p for k, p in enumerate(raw) if k == 0 or km(raw[k - 1], p) > 1]
            if len(pts) < 2:
                continue
            key = ";".join(f"{float(p['lat']):.5f},{float(p['lng']):.5f}" for p in pts)
            wanted[day["date"]] = (key, pts)

    result, changed, failed = {}, False, False
    for date, (key, pts) in wanted.items():
        if old.get(date, {}).get("key") == key:
            result[date] = old[date]; continue
        coords = ";".join(f"{float(p['lng']):.5f},{float(p['lat']):.5f}" for p in pts)
        try:
            req = urllib.request.Request(f"{OSRM}{coords}?overview=simplified&geometries=geojson&steps=false", headers={"User-Agent": "chile-trip-sync/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                j = json.load(r)
            if j.get("code") != "Ok":
                raise ValueError(j.get("code"))
            rt = j["routes"][0]
            result[date] = {"key": key, "km": round(rt["distance"] / 1000, 1), "h": round(rt["duration"] / 3600, 3),
                            "geom": [[round(c[1], 4), round(c[0], 4)] for c in rt["geometry"]["coordinates"]]}
            changed = True
            time.sleep(0.6)
        except Exception as e:  # network blocked or OSRM error: keep going without this day
            failed = True
            print(f"route {date} failed: {e}", file=sys.stderr)
    if set(result) != set(old):
        changed = True
    out.write_text(json.dumps({"days": result, "computedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}, ensure_ascii=False), encoding="utf-8")
    if failed and not result:
        print("routing unavailable")
    else:
        print("updated" if changed else "unchanged")


if __name__ == "__main__":
    main()
