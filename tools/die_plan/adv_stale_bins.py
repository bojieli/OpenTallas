#!/usr/bin/env python3
"""adv_stale_bins.py -- PRE static advisory ADV-STALE-BINS (QC-CB-SPREAD-R2 11-24, COORD flow review #5; an estimator, never a gate).

Class CB-TAPBINS: density taps (clock.tap_mode "density") are solved from clock.sink_bins_file.  Where the bins come from an older
build, the taps are sized for the wrong load and the kit's cap pass finds "no tap with room within 200 um": QC C1h/C1i, 54 of 92
types kept a tap over 1,000 sinks after the cap pass, 19 over 5,000 (cbf_q01 bins 58.9k vs 74.3k placed regs, t92 4,074 sinks;
sle_hc2 root clk 17,747).  Per type with a clock.sink_bins_file:

  bins        = the file's n (else the sum of its bin weights)
  kit sinks   = the CLOCK-NET sinks the newest kit of the type split over its taps (CTS log OT_CLOCK_TAPS summary line), from
                kit_sinks.py --kitwave JSON (kit_sinks= path(s) / dict, env OT_ADV_KIT_SINKS, default KIT_SINKS_DEFAULT);
                exact type, else the newest kit of the base type (__cl/__pv stripped)
  WARN when |kit sinks / bins - 1| > 5 %, and when that kit's largest tap after the cap pass is over 1,000 sinks -- the
  fanout only when the kit is NEWER than the bins file (a kit built before a re-bin measured the old taps; counted, not listed).
  Recalibrated 11-24 (COORD): v1 compared placed n_regs (all flops, incl. edge-clock rings / non-clock regs) and the placed
  load on the old kit taps, and fired on 110 of 115 QC types.  No clock-net count -> the type is not checked (counted).
  Fix: re-bin from the placed kit (sink_bins_from_place.py dump / bins --native-only, sink_bins_compose.py) and re-solve.

    findings(raw, plan_path, tree=None, kit_sinks=None|path[,path]|dict, frac=0.05, fanout_max=1000)
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
KIT_SINKS_ENV = "OT_ADV_KIT_SINKS"
KIT_SINKS_DEFAULT = "/srv/opentallas-scratch2/claude/precheck-cache/kit_sinks.json"


def load_kit_sinks(src):
    """{type: {sinks, taps, max_tap, max_sinks, mtime, log}} merged newest-first from dict / comma paths / env / default."""
    if isinstance(src, dict):
        return src, "<dict>"
    paths = [p for p in (src or os.environ.get(KIT_SINKS_ENV) or KIT_SINKS_DEFAULT).split(",") if p]
    out, used = {}, []
    for p in paths:
        try:
            d = json.loads(Path(p).read_text())
        except (OSError, ValueError):
            continue
        used.append(Path(p).name)
        for k, v in d.items():
            if isinstance(v, dict) and (k not in out or v.get("mtime", 0) > out[k].get("mtime", 0)):
                out[k] = v
    return (out, ",".join(used)) if used else (None, None)


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


def findings(raw, plan_path, tree=None, kit_sinks=None, frac=FRAC, fanout_max=FANOUT_MAX, max_lines=MAX_LINES, **_kw):
    try:
        return _findings(raw, plan_path, tree, kit_sinks, frac, fanout_max, max_lines)
    except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


def _findings(raw, plan_path, tree, kit_sinks, frac, fanout_max, max_lines):
    ks, src = load_kit_sinks(kit_sinks)
    if not ks:
        return [_w("not checked", f"no kit clock-sink map (kit_sinks.py --kitwave JSON; set {KIT_SINKS_ENV} or write {KIT_SINKS_DEFAULT})")]
    by_base = {}
    for n in ks:
        by_base.setdefault(ATL.base_type(n), []).append(n)
    placed_types = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
    hits, n_cmp, n_stale, n_fan, n_old, n_nofile, n_nokit = [], 0, 0, 0, 0, 0, 0
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        ck = t.get("clock") if isinstance(t, dict) else None
        if not isinstance(ck, dict) or not ck.get("sink_bins_file") or (placed_types and tn not in placed_types):
            continue
        rec, basis = ATL.lookup(ks, tn, by_base)
        if not rec or not rec.get("sinks"):
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
        sk = float(rec["sinks"])
        r = sk / nb if nb else float("inf")
        if abs(r - 1.0) > frac:
            n_stale += 1
            why.append(f"sink bins {nb:,.0f} vs {sk:,.0f} clock-net sinks of kit {basis} = x{r:.2f}, off by more than {frac:.0%}")
            score = max(score, abs(r - 1.0))
        ms = rec.get("max_sinks")
        if ms and ms > fanout_max:
            if float(rec.get("mtime") or 0) >= bp.stat().st_mtime:
                n_fan += 1
                why.append(f"kit largest tap after the cap pass {ms:,} sinks ({rec.get('max_tap', '?')}) > {fanout_max}")
                score = max(score, ms / fanout_max - 1.0)
            else:
                n_old += 1
        if why:
            hits.append((score, _w(tn, "; ".join(why) + "; fix: re-bin from the placed kit (sink_bins_from_place.py --native-only, "
                                   "sink_bins_compose.py) and re-solve the density taps (CB-TAPBINS)")))
    hits.sort(key=lambda h: -h[0])
    out = [m for _, m in hits[:max_lines]]
    out.append(_w("summary", f"{n_stale} of {n_cmp} types with sink bins off kit clock-net sinks by > {frac:.0%}, {n_fan} with a kit tap "
                             f"> {fanout_max} after the cap pass ({n_old} more on kits older than their bins: not listed); {n_nokit} "
                             f"without a kit clock-sink count, {n_nofile} bins files missing; kit sinks {src}"))
    return out


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        _raw = json.load(f)
    for ln in findings(_raw, sys.argv[1], sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None,
                       kit_sinks=sys.argv[3] if len(sys.argv) > 3 else None):
        print(ln)
