"""adv_sinkbin_age.py -- PRE ADV-SINKBIN-AGE (C-TAP-LOAD / P-STALE-TABLE, COORD 11-27; REPORT-ONLY, never a gate).

A density type's taps are solved from clock.sink_bins_file.  72 QC types still used bins written BEFORE the type was placed
(hf1c / n46v0 / placed-1120 bins of an older kit or of the base type), so the taps were sized for registers that moved.  Per
placed soft type with a clock.sink_bins_file this check compares

  bins time   recorded provenance first:  the bins doc's own stamp (created / mtime / ts / epoch, epoch seconds or ISO), else a
              stamp inside its provenance strings (source / placed_kit / hf1c_from / ...: a kit epoch "-1795235359" or a
              "MM-DD" wave date, day-granular stamps count to the END of that day), else the file mtime (basis "file mtime":
              weak, a copied tree resets it; counted separately);
  placed time the newest PLACED DB of the type itself: precheck-cache flops_cache.json placed_bins[type].ts (the kit's placement
              dump) and kit_sinks.json[type].mtime (its CTS log), or placed_times= {type: epoch} from the caller.

WARN when a placed DB is newer than the bins by more than slack_s (default 1 h).  A type with bins but no placed-DB record, and
a density type with no bins file, are NOT-CHECKED (counted, never a pass).

    findings(raw, plan_path, tree=None, cache=None, kit_sinks=None, placed_times=None, bins_times=None, slack_s=3600)
    python3 -I adv_sinkbin_age.py PLAN [TREE]       prints the per-type TSV summary and the summary line
"""
import datetime
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_stale_bins as _SB  # noqa: E402
import adv_tap_load as _ATL  # noqa: E402

CHECK = "SINKBIN-AGE"
SLACK_S = 3600.0
MAX_LINES = 25
DOC_KEYS = ("created", "mtime", "ts", "epoch", "made")
EPOCH = re.compile(r"(?<![0-9])(1[6-9][0-9]{8})(?![0-9])")
WAVE_DAY = re.compile(r"(?<![0-9])(0[1-9]|1[0-2])-([0-3][0-9])(?![0-9-])")


def _w(obj, msg):
    return f"WARN ADV-{CHECK} {obj}: {msg}"


def _stamp(v):
    """epoch seconds from a number / ISO string, else None"""
    if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 1e9:
        return float(v)
    if isinstance(v, str):
        try:
            d = datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
        return (d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)).timestamp()
    return None


def _strings(o, depth=0):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict) and depth < 3:
        for k, v in o.items():
            if k != "bins":
                yield from _strings(v, depth + 1)
    elif isinstance(o, list) and depth < 3:
        for v in o[:20]:
            yield from _strings(v, depth + 1)


def bins_time(doc, path=None, today=None):
    """(epoch, basis) of when the bins were measured: recorded provenance, else the file mtime, else (None, 'none')"""
    for k in DOC_KEYS:
        t = _stamp(doc.get(k))
        if t:
            return t, f"doc {k}"
    strs = list(_strings({k: v for k, v in doc.items() if k != "bins"}))
    ep = [int(m) for s in strs for m in EPOCH.findall(s)]
    if ep:
        return float(max(ep)), "provenance epoch"
    today = today or datetime.datetime.now(datetime.timezone.utc)
    days = []
    for s in strs:
        for mo, d in WAVE_DAY.findall(s):
            try:
                dt = datetime.datetime(today.year, int(mo), int(d), tzinfo=datetime.timezone.utc)
            except ValueError:
                continue
            if dt > today + datetime.timedelta(days=1):
                dt = dt.replace(year=dt.year - 1)
            days.append(dt)
    if days:
        return max(days).timestamp() + 86400.0, "provenance day"      # day-granular: counted to the end of that day
    if path is not None:
        try:
            return Path(path).stat().st_mtime, "file mtime"
        except OSError:
            pass
    return None, "none"


def placed_time(tn, cache, kit_sinks, placed_times):
    """(epoch, what) of the newest placed DB record of the type itself, else (None, '')"""
    c = []
    if placed_times and tn in placed_times:
        c.append((float(placed_times[tn]), "caller placed time"))
    pb = ((cache or {}).get("placed_bins") or {}).get(tn) or {}
    if pb.get("ts"):
        c.append((float(pb["ts"]), f"placed kit {str(pb.get('kit', '?')).split(':')[-1][:50]}"))
    ks = (kit_sinks or {}).get(tn) or {}
    if ks.get("mtime"):
        c.append((float(ks["mtime"]), "kit CTS log"))
    return max(c) if c else (None, "")


def _fmt(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%m-%d %H:%M")


def census(raw, plan_path, tree=None, cache=None, kit_sinks=None, placed_times=None, bins_times=None, slack_s=SLACK_S):
    """-> (rows, summary): rows per placed soft type with a clock, each dict(type, verdict in STALE|FRESH|NOT-CHECKED, ...)"""
    cache = cache if isinstance(cache, dict) else (_ATL.load_cache(cache)[0] or {})
    kit_sinks = kit_sinks if isinstance(kit_sinks, dict) else (_SB.load_kit_sinks(kit_sinks)[0] or {})
    placed = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
    rows = []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        ck = t.get("clock") if isinstance(t, dict) else None
        if not ck or t.get("hard") or (placed and tn not in placed):
            continue
        row = dict(type=tn, mode=ck.get("tap_mode", "grid"))
        f = ck.get("sink_bins_file")
        if not f:
            if row["mode"] == "density":
                rows.append(dict(row, verdict="NOT-CHECKED", why="density type without sink bins"))
            continue
        row["bins_file"] = f
        p = _SB.bins_path(f, plan_path, tree)
        if p is None:
            rows.append(dict(row, verdict="NOT-CHECKED", why="sink bins file not found"))
            continue
        if bins_times and tn in bins_times:
            bt, basis = float(bins_times[tn]), "caller bins time"
        else:
            try:
                doc = json.loads(Path(p).read_text())
            except (OSError, ValueError):
                rows.append(dict(row, verdict="NOT-CHECKED", why="sink bins file unreadable"))
                continue
            bt, basis = bins_time(doc, p)
        pt, what = placed_time(tn, cache, kit_sinks, placed_times)
        if bt is None or pt is None:
            rows.append(dict(row, verdict="NOT-CHECKED", basis=basis, why="no placed-DB record" if pt is None else "no bins time"))
            continue
        gap = pt - bt
        rows.append(dict(row, verdict="STALE" if gap > slack_s else "FRESH", basis=basis, bins_t=bt, placed_t=pt,
                         placed_what=what, gap_h=round(gap / 3600.0, 1)))
    cnt = Counter(r["verdict"] for r in rows)
    stale = [r for r in rows if r["verdict"] == "STALE"]
    return rows, dict(types=len(rows), stale=cnt["STALE"], fresh=cnt["FRESH"], not_checked=cnt["NOT-CHECKED"],
                      stale_by_basis=dict(Counter(r["basis"] for r in stale)),
                      weak_mtime_basis=sum(1 for r in rows if r.get("basis") == "file mtime"))


def _findings(raw, plan_path, tree=None, max_lines=MAX_LINES, **kw):
    rows, s = census(raw, plan_path, tree, **kw)
    stale = sorted((r for r in rows if r["verdict"] == "STALE"), key=lambda r: -r["gap_h"])
    out = [_w(r["type"], f"sink bins ({r['basis']} {_fmt(r['bins_t'])}) are {r['gap_h']:g} h older than the type's latest placed DB "
                         f"({r['placed_what']} {_fmt(r['placed_t'])}); fix: re-bin from the newest placement "
                         f"(sink_bins_from_place.py --native-only + sink_bins_compose.py) and re-solve the taps") for r in stale[:max_lines]]
    nc = [r for r in rows if r["verdict"] == "NOT-CHECKED"]
    if nc:
        out.append(_w("NOT-CHECKED", f"{len(nc)} types have no usable bins time or placed-DB record (not passed): "
                                     + ", ".join(f"{r['type']} ({r['why']})" for r in nc[:6]) + (" ..." if len(nc) > 6 else "")))
    out.append(_w("summary", f"{s['stale']} of {s['types']} types with sink bins older than their latest placed DB (report-only), "
                             f"{s['fresh']} fresh, {s['not_checked']} NOT-CHECKED; stale by bins-time basis {s['stale_by_basis']}; "
                             f"{s['weak_mtime_basis']} types judged on a file mtime only"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    _plan = Path(sys.argv[1])
    _raw = json.loads(_plan.read_text())
    _rows, _s = census(_raw, str(_plan), sys.argv[2] if len(sys.argv) > 2 else None)
    for _r in _rows:
        print("\t".join(str(_r.get(k, "")) for k in ("type", "mode", "verdict", "basis", "gap_h", "placed_what", "why")))
    print(json.dumps(_s))
