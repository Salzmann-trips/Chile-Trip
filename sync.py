#!/usr/bin/env python3
"""Build data/trip.json for the standalone site from an export of the Claude planner's database.

Usage:  python3 tools/sync.py <export_dir> [--include-notes] [--include-examples]

<export_dir> is the folder written by reading the planner's database with an out_dir:
  <export_dir>/items/<id>.json      one file per entry
  <export_dir>/trip/settings.json   trip name, dates, road factor, speed
  <export_dir>/trip/suggestion.json optional suggested route (shown on the Suggestion tab)

The public site gets only the fields it needs. Costs are never published; notes only
with --include-notes (they may hold booking numbers). Example entries are skipped
unless --include-examples is given.
"""
import json, sys, pathlib, datetime

PUBLIC_FIELDS = ["type", "title", "date", "time", "endDate", "endTime", "place", "lat", "lng", "url", "order"]


def body(path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    # Accept either the bare document or a {id, data, version} wrapper.
    if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
        return raw.get("id") or path.stem, raw["data"]
    return path.stem, raw


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        sys.exit(__doc__)
    src = pathlib.Path(args[0])
    root = pathlib.Path(__file__).resolve().parent.parent

    settings = {"title": "Chile trip", "start": "", "end": "", "factor": 1.3, "speed": 65}
    sfile = src / "trip" / "settings.json"
    if sfile.exists():
        settings.update(body(sfile)[1])

    items = []
    for f in sorted((src / "items").glob("*.json")):
        doc_id, d = body(f)
        if d.get("example") and "--include-examples" not in flags:
            continue
        out = {"id": doc_id}
        for k in PUBLIC_FIELDS:
            if d.get(k) not in (None, ""):
                out[k] = d[k]
        if "--include-notes" in flags and d.get("notes"):
            out["notes"] = d["notes"]
        items.append(out)

    # Optional suggested route (written by Claude into trip/suggestion); it holds no private fields.
    suggestion = None
    gfile = src / "trip" / "suggestion.json"
    if gfile.exists():
        g = body(gfile)[1]
        if isinstance(g, dict) and isinstance(g.get("stages"), list):
            suggestion = {k: g[k] for k in ("title", "createdAt", "basis", "intro", "notes", "stages", "skipped") if k in g}

    trip = {
        "settings": {k: settings.get(k) for k in ("title", "start", "end", "factor", "speed")},
        "items": items,
        "suggestion": suggestion,
        "syncedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    dest = root / "data" / "trip.json"
    new = json.dumps(trip, ensure_ascii=False, indent=1)
    old = dest.read_text(encoding="utf-8") if dest.exists() else ""
    # Ignore the timestamp when deciding whether anything changed.
    strip = lambda s: json.dumps({k: v for k, v in json.loads(s).items() if k != "syncedAt"}, sort_keys=True) if s else ""
    if strip(old) == strip(new):
        print("unchanged")
        return
    dest.write_text(new + "\n", encoding="utf-8")
    print(f"updated: {len(items)} entries")


if __name__ == "__main__":
    main()
