#!/usr/bin/env python3
"""adv_stale_bins.py -- PRE static advisory ADV-STALE-BINS (QC-CB-SPREAD-R2 11-24, COORD flow review #5; an estimator, never a gate).

Class CB-TAPBINS: density taps (clock.tap_mode "density") are solved from clock.sink_bins_file.  Where the bins come from an older
build, the taps are sized for the wrong load and the kit's cap pass finds "no tap with room within 200 um": QC C1h/C1i, 54 of 92
types kept a tap over 1,000 sinks after the cap pass, 19 over 5,000 (cbf_q01 bins 58.9k vs 74.3k placed regs, t92 4,074 sinks;
sle_hc2 root clk 17,747).  Per type with a clock.sink_bins_file:

  bins        = the file's n (else the sum of its bin weights)
  placed regs = n_regs of the newest placed kit of the type (flops cache placed_bins / placed; exact type, else the newest kit
                of the base type, __cl/__pv stripped)
  WARN when |placed / bins - 1| > 5 %, and when the placed kit's largest tap fanout (placed regs on the kit's taps, nearest
  tap, flops cache placed.max_load) is over 1,000.  Fix: re-bin from the placed kit (sink_bins_from_place.py dump / bins
  --native-only, sink_bins_compose.py) so the density solve re-sizes the taps.

    findings(raw, plan_path, tree=None, flops_cache=None|path|dict, frac=0.05, fanout_max=1000)
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adv_tap_load as ATL  # noqa: E402  (cache loader + base-type lookup)

CHECK = "STALE-BINS"
FRAC = 0.05
FANOUT_MAX = 1000
MAX_LINES = 25


def _w(obj, msg):
    return f"WARN ADV-{CHECK} {obj}: {msg}"


def bins_path(f, plan_path, tree=None):
    """the bins file: absolute as given, else under the tree root, else beside the plan or under any ancestor of it."""
    p = Path(f)
    if p.is_absolute():
        return p if p.is_file() else None
    cands = [Path(tree) / f] if tree else []
    if plan_path:
        d = Path(plan_path).resolve().parent
        cands += [d / f, d / p.name] + [a / f for a in d.parents]
    for c in cands:
        if c.is_file():
            return c
    return None


def bins_count(doc):
    if isinstance(doc.get("n"), (int, float)) and doc["n"] > 0:
        return float(doc["n"])
    return float(sum(float(b[2]) if len(b) > 2 else 1.0 for b in doc.get("bins") or []))


def findings(raw, plan_path, tree=None, flops_cache=None, frac=FRAC, fanout_max=FANOUT_MAX, max_lines=MAX_LINES, **_kw):
    try:
        return _findings(raw, plan_path, tree, flops_cache, frac, fanout_max, max_lines)
    except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


def _findings(raw, plan_path, tree, flops_cache, frac, fanout_max, max_lines):
    cache, src = ATL.load_cache(flops_cache)
    if not cache:
        return [_w("not checked", f"no flops cache (set {ATL.CACHE_ENV} or run harvest_flops.py + merge_flops.py)")]
    pl, pb = cache.get("placed") or {}, cache.get("placed_bins") or {}
    by_base = {}
    for n in set(pl) | set(pb):
        by_base.setdefault(ATL.base_type(n), []).append(n)
    placed_types = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
    hits, n_cmp, n_stale, n_fan, n_nofile, n_nokit = [], 0, 0, 0, 0, 0
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        ck = t.get("clock") if isinstance(t, dict) else None
        if not isinstance(ck, dict) or not ck.get("sink_bins_file") or (placed_types and tn not in placed_types):
            continue
        rec_b, basis_b = ATL.lookup(pb, tn, by_base)
        rec_p, basis_p = ATL.lookup(pl, tn, by_base)
        regs = (rec_b or {}).get("n_regs") or (rec_p or {}).get("n_regs")
        if not regs:
            n_nokit += 1
            continue
        bp = bins_path(ck["sink_bins_file"], plan_path, tree)
        if bp is None:
            n_nofile += 1
            hits.append((0.0, _w(tn, f"clock.sink_bins_file {ck['sink_bins_file']} not found (plan dir, its ancestors, tree)")))
            continue
        try:
            nb = bins_count(json.loads(bp.read_text()))
        except (OSError, ValueError) as e:
            hits.append((0.0, _w(tn, f"sink bins {bp.name} unreadable: {type(e).__name__}")))
            continue
        n_cmp += 1
        why, score = [], 0.0
        r = regs / nb if nb else float("inf")
        if abs(r - 1.0) > frac:
            n_stale += 1
            why.append(f"sink bins {nb:,.0f} vs {regs:,.0f} placed regs ({basis_b or basis_p}) = x{r:.2f}, off by more than "
                       f"{frac:.0%}: density taps sized on stale bins")
            score = max(score, abs(r - 1.0))
        ml = (rec_p or {}).get("max_load")
        if ml and ml > fanout_max:
            n_fan += 1
            why.append(f"largest tap fanout {ml:,} sinks ({(rec_p or {}).get('max_tap', '?')}, placed kit {basis_p}) > {fanout_max}")
            score = max(score, ml / fanout_max - 1.0)
        if why:
            hits.append((score, _w(tn, "; ".join(why) + "; fix: re-bin from the placed kit (sink_bins_from_place.py --native-only, "
                                   "sink_bins_compose.py) and re-solve the density taps (CB-TAPBINS)")))
    hits.sort(key=lambda h: -h[0])
    out = [m for _, m in hits[:max_lines]]
    out.append(_w("summary", f"{n_stale} of {n_cmp} types with sink bins off placed regs by > {frac:.0%}, {n_fan} with a placed tap "
                             f"fanout > {fanout_max}; {n_nokit} without a placed kit, {n_nofile} bins files missing; cache "
                             f"{Path(src).name if src and src != '<dict>' else src} {cache.get('made', '')}"))
    return out


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        _raw = json.load(f)
    for ln in findings(_raw, sys.argv[1], sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None,
                       flops_cache=sys.argv[3] if len(sys.argv) > 3 else None):
        print(ln)
