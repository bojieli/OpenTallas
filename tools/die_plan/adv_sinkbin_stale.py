"""adv_sinkbin_stale.py -- PRECHECK ADV-SINKBIN-STALE (COORD 11-25; an estimator, report only, never a gate).

Repeat class CB-TAPBINS: density taps (clock.tap_mode "density") are solved from clock.sink_bins_file, and the bins were
written for an older shape of the type: KV-SINKBINS (kv3_pv bins from the D29 placement, 78 of 255 taps on bins the A5t6
form no longer fills, placed taps up to 17,980 sinks), QC st_a (under-declared taps), QC STB-SPLIT (bins pre-split: 17-45 %
of each st_b type's sinks inside the 4 station children).  ADV-STALE-BINS compares bins with the newest KIT; this check needs
no kit: it compares the bins with the PLAN.  Per type with a clock.sink_bins_file, WARN when any of

  PREDATES  the bins predate the type's latest re-shape / split / station row:
              - the bins doc names another type (doc "type" != the type: written before a split / rename) that is gone
                from the plan or has another outline / hard-core placement (a param variant sharing its parent's
                unchanged geometry is not stale), or
              - row times are given (row_times= {type: epoch | "YYYY-MM-DD[ HH:MM]"}, path, or env OT_ADV_SINKBIN_ROWS) and
                the bins time (doc "created"/"mtime" epoch, else the file mtime) is older than the type's row time;
  INSIDE    > 5 % of the bins' sinks lie in a hard core / lef child (adv_site_in_macro.core_rects, shrunk by half a bin
            so edge bins of sinks beside the core do not count) or outside the type outline (grown by half a bin);
  FANOUT    a tap carries > 1,000 sinks: the largest tap after the cap pass of the newest kit of the type (exact, else
            its base type) built AFTER the bins file (kit_sinks.py --kitwave map, as ADV-STALE-BINS: kit_sinks= /
            env OT_ADV_KIT_SINKS / precheck-cache default).  The plan's own density solve balances to
            clock.tap_target_sinks by construction, so a > 1,000 tap only shows on the placed netlist.

Fix: re-bin from a kit placed on the CURRENT form (sink_bins_from_place.py --native-only + sink_bins_compose.py), re-solve
the density taps, then remap references (KV-SINKBINS / STB-SPLIT rule).
findings(raw, plan_path, tree=None, row_times=None, **kw) -> WARN lines, never raises.
"""
import datetime
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_site_in_macro as _SIM  # noqa: E402
import adv_stale_bins as _SB  # noqa: E402
import adv_tap_load as _ATL  # noqa: E402

CHECK = "ADV-SINKBIN-STALE"
FRAC = 0.05
FANOUT_MAX = 1000
MAX_LINES = 25
ROWS_ENV = "OT_ADV_SINKBIN_ROWS"


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def _epoch(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        for f in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(v.strip()[:19], f).timestamp()
            except ValueError:
                pass
    return None


def load_row_times(src):
    if isinstance(src, dict):
        return src
    p = src or os.environ.get(ROWS_ENV)
    if not p:
        return {}
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return {}


def _geom(t):
    return (t.get("outline_um"), sorted((str(h.get("inst")), tuple(h.get("origin_um") or ()), h.get("orient", "R0"))
                                        for h in t.get("hard_cores") or [] if isinstance(h, dict)))


def judge_type(tn, t, doc, bins_time=None, row_time=None, frac=FRAC, fanout_max=FANOUT_MAX, types=None, kit=None):
    """-> dict(predates=[why], n, inside, outside, frac_in, max_tap, max_load, ...).  types = the plan's partition_types
    (for the bins-type geometry compare); kit = kit_sinks record {max_sinks, max_tap, mtime} or None."""
    ck = t.get("clock") or {}
    half = float(doc.get("bin_um") or 10.8) / 2.0
    W, H = (float(v) for v in t["outline_um"])
    rects = [(x0 + half, y0 + half, x1 - half, y1 - half, nm) for x0, y0, x1, y1, _h, nm in _SIM.core_rects(t)]
    rects = [r for r in rects if r[0] < r[2] and r[1] < r[3]]
    n = inside = outside = 0.0
    by_core = {}
    for b in doc.get("bins") or []:
        x, y = float(b[0]), float(b[1])
        c = float(b[2]) if len(b) > 2 else 1.0
        n += c
        if x < -half or y < -half or x > W + half or y > H + half:
            outside += c
        else:
            for x0, y0, x1, y1, nm in rects:
                if x0 < x < x1 and y0 < y < y1:
                    inside += c
                    by_core[nm] = by_core.get(nm, 0.0) + c
                    break
    pre = []
    dt = doc.get("type")
    if dt and dt != tn:
        other = (types or {}).get(dt)
        if other is None:
            pre.append(f"bins written for type {dt}, not in this plan (split / renamed since)")
        elif _geom(other) != _geom(t):
            pre.append(f"bins written for type {dt}, whose outline / hard-core placement differs from this type's")
    if row_time is not None and bins_time is not None and bins_time < row_time:
        pre.append(f"bins {datetime.datetime.fromtimestamp(bins_time):%m-%d %H:%M} older than the type's row "
                   f"{datetime.datetime.fromtimestamp(row_time):%m-%d %H:%M}")
    ms, old_kit = 0.0, False
    if kit and kit.get("max_sinks"):
        if bins_time is None or float(kit.get("mtime") or 0) >= bins_time:
            ms = float(kit["max_sinks"])
        else:
            old_kit = True
    r = dict(predates=pre, n=n, inside=inside, outside=outside, frac_in=(inside + outside) / n if n else 0.0,
             by_core=sorted(by_core.items(), key=lambda kv: -kv[1])[:3], max_tap=(kit or {}).get("max_tap"),
             max_load=ms, old_kit=old_kit)
    r["is_inside"] = r["frac_in"] > frac
    r["is_fanout"] = r["max_load"] > fanout_max
    r["hit"] = bool(pre) or r["is_inside"] or r["is_fanout"]
    return r


def findings(raw, plan_path, tree=None, row_times=None, kit_sinks=None, frac=FRAC, fanout_max=FANOUT_MAX, max_lines=MAX_LINES,
             **_kw):
    try:
        return _findings(raw, plan_path, tree, row_times, kit_sinks, frac, fanout_max, max_lines)
    except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


def _findings(raw, plan_path, tree, row_times, kit_sinks, frac, fanout_max, max_lines):
    rt = load_row_times(row_times)
    ks, ks_src = _SB.load_kit_sinks(kit_sinks)
    ks = ks or {}
    by_base = {}
    for k in ks:
        by_base.setdefault(_ATL.base_type(k), []).append(k)
    types = raw.get("partition_types") or {}
    n_nokit = n_oldkit = 0
    placed = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
    hits, n_chk, n_nofile = [], 0, 0
    cnt = dict(predates=0, inside=0, fanout=0)
    for tn, t in sorted(types.items()):
        ck = t.get("clock") if isinstance(t, dict) else None
        if not isinstance(ck, dict) or not ck.get("sink_bins_file") or (placed and tn not in placed):
            continue
        bp = _SB.bins_path(ck["sink_bins_file"], plan_path, tree)
        if bp is None:
            n_nofile += 1
            continue
        try:
            doc = json.loads(bp.read_text())
        except (OSError, ValueError):
            n_nofile += 1
            continue
        n_chk += 1
        bt = _epoch(doc.get("created")) or _epoch(doc.get("mtime")) or bp.stat().st_mtime
        kit, _basis = _ATL.lookup(ks, tn, by_base) if ks else (None, None)
        n_nokit += kit is None
        r = judge_type(tn, t, doc, bt, _epoch(rt.get(tn)), frac, fanout_max, types, kit)
        n_oldkit += r["old_kit"]
        if not r["hit"]:
            continue
        why, score = [], 0.0
        if r["predates"]:
            cnt["predates"] += 1
            why.append("PREDATES " + "; ".join(r["predates"]))
            score += 1.0
        if r["is_inside"]:
            cnt["inside"] += 1
            cores = ", ".join(f"{nm} {c:,.0f}" for nm, c in r["by_core"])
            why.append(f"INSIDE {r['inside'] + r['outside']:,.0f} of {r['n']:,.0f} bin sinks ({r['frac_in']:.0%}) in cores"
                       f"/children ({r['inside']:,.0f}{': ' + cores if cores else ''}) or off the outline ({r['outside']:,.0f})")
            score += r["frac_in"] * 10
        if r["is_fanout"]:
            cnt["fanout"] += 1
            why.append(f"FANOUT kit {_basis} largest tap {r['max_load']:,.0f} sinks ({r['max_tap']}) > {fanout_max}")
            score += r["max_load"] / fanout_max
        hits.append((score, _w(tn, f"{bp.name}: " + " | ".join(why))))
    hits.sort(key=lambda h: -h[0])
    out = [m for _, m in hits[:max_lines]]
    out.append(_w("summary", f"{len(hits)} of {n_chk} types with sink bins stale (PREDATES {cnt['predates']}, INSIDE > {frac:.0%} "
                             f"{cnt['inside']}, FANOUT > {fanout_max} {cnt['fanout']}); {n_nofile} bins files not found; kit sinks "
                             f"{ks_src or 'none'}: {n_nokit} types without a kit, {n_oldkit} with a kit older than the bins (not judged)"
                             f"{'' if rt else '; no row times given (PREDATES = bins type only)'}"))
    return out


if __name__ == "__main__":
    import time
    t0 = time.time()
    raw_ = json.load(open(sys.argv[1]))
    ls = findings(raw_, sys.argv[1], sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None,
                  row_times=sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None,
                  kit_sinks=sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None)
    print(f"{time.time() - t0:.1f}s")
    for ln in ls:
        print(ln)
