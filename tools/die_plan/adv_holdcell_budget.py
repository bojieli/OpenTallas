"""adv_holdcell_budget.py -- ADV-HOLDCELL-BUDGET (KV-HOLD-STRUCT 11-25; PRECHECK, report-only: WARN lines, never a FAIL).

Why: on KV the hold-cell volume of a kit (18k-40k cells, 6-9 % of instances on hg / pc / sys_c) is not violation repair.  The base hold
pass closes a kit with 2-3k buffers; the reg-to-reg family margin pass (hold_margin_family: 40 ps on qwen_kvsys, OT_PREGRT_HOLD_R2R_MARGIN)
then pads every zero-logic pair with one HB4 (OT_HOLD_PAD rr1 ends 36,940 / cells 36,837 on pc r85c02c25c; hg_v1p2 24,722; sys_c 26,564),
which is 85-90 % of the hold cells.  And the endpoints the repair cannot close at all are the first FF behind an input port (landing-ring
dch sd_c / s_d, bin, ft station flop): ports are excepted from the repair (pregrt 'port scope'), the hold gate prints PASS at its structural
limit, and the true slack stays negative (pv_v12 2,335 endpoints -119.2).  Neither shows in the plan; both are known after the FIRST kit of
a type, so the check reads the newest retained kit of the type (adv_harvest_hold.py cache) and reports it against the plan about to launch.

Per placed soft type (exact type first, else the newest kit of the same base type: __cl / __pv cohort suffixes stripped):
  pad share   = pad_cells / insts of that kit            WARN at >= PAD_PCT (5 %)   -> structural form instead of a pad per pair:
                                                          lockup latch (clock.zl_lockup / ft_hop_lockup / reset.relay_lockup),
                                                          tap co-location (clock.tap_landing_seam), same-tap seating
  port open   = open_n endpoints, open_wns < 0           WARN (class PORT-OPEN)    -> sender contract (clock.ring_hold.sender_ps_types)
                                                          vs the ring tap tree is the structural gap; a pad cannot close it
  no kit      = counted in the summary only.
Absent cache: one 'not checked' line.  Cache: adv_harvest_hold.py OUT.json DIE ROOT...; env OT_ADV_HOLD_CACHE or adv_cache/hold_cache.json.

    findings(raw, plan_path, tree=None, hold_cache=None|path|dict, **_kw) -> ["WARN ADV-HOLDCELL-BUDGET ..."]
"""
import json
import os
import re
from pathlib import Path

CHECK = "HOLDCELL-BUDGET"
PAD_PCT = 5.0
MAX_LINES = 25
SUFFIX = re.compile(r"(?:__(?:cl|pv|r)[0-9a-f]{6,})+$")
CACHE_ENV = "OT_ADV_HOLD_CACHE"
CACHE_DEFAULTS = ("adv_cache/hold_cache.json", "/srv/opentallas-scratch2/claude/precheck-cache/hold_cache.json")


def _w(obj, msg):
    return f"WARN ADV-{CHECK} {obj}: {msg}"


def base_type(tn):
    return SUFFIX.sub("", tn)


def load_cache(src):
    if isinstance(src, dict):
        return src
    cands = [src] if src else []
    if os.environ.get(CACHE_ENV):
        cands.insert(0, os.environ[CACHE_ENV])
    here = Path(__file__).resolve().parent
    cands += [str(here / CACHE_DEFAULTS[0]), CACHE_DEFAULTS[1]]
    for c in cands:
        if c and os.path.isfile(c):
            try:
                with open(c) as f:
                    return json.load(f)
            except (OSError, ValueError):
                return None
    return None


def _last(entry):
    return (entry or {}).get("last") if isinstance(entry, dict) else None


def findings(raw, plan_path, tree=None, hold_cache=None, **_kw):
    cache = load_cache(hold_cache)
    if not cache or not isinstance(cache.get("hold"), dict):
        return [f"WARN ADV-{CHECK} not checked: no hold cache (adv_harvest_hold.py OUT.json DIE ROOT...)"]
    die = (raw.get("die") or {}).get("name")
    recs = cache["hold"].get(die) or {}
    types = raw.get("partition_types") or {}
    placed = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
    pad_hits, open_hits = [], []
    measured = unmeasured = 0
    for name, t in types.items():
        if t.get("hard") or (placed and name not in placed):
            continue
        last = _last(recs.get(base_type(name)))
        if not last or not last.get("insts"):
            unmeasured += 1
            continue
        measured += 1
        pct = 100.0 * last.get("pad_cells", 0) / last["insts"]
        ex = last.get("exact") or "?"
        if pct >= PAD_PCT:
            pad_hits.append((pct, name, f"{last['pad_cells']:,} planned-pad cells = {pct:.1f}% of {last['insts']:,} insts "
                             f"({last.get('pad_ends', 0):,} endpoints at R2R margin {last.get('margin')} ps; "
                             f"{last.get('hold_cells', 0):,} hold cells in all; kit {ex}): use a lockup / tap-co-location form on the "
                             f"zero-logic seams, not an HB4 per pair"))
        if last.get("open_n", 0) > 0 and last.get("open_wns", 0.0) < 0.0:
            open_hits.append((last["open_wns"], name, f"PORT-OPEN {last['open_n']:,} endpoints the repair cannot close, worst "
                              f"{last['open_wns']:.1f} ps (first FF behind an input port; hold_gate may still print PASS; kit {ex}): "
                              f"fix the sender contract / ring tap arrival, a pad does not reach it"))
    out = [_w(n, m) for _, n, m in sorted(pad_hits, key=lambda h: (-h[0], h[1]))[:MAX_LINES]]
    out += [_w(n, m) for _, n, m in sorted(open_hits, key=lambda h: (h[0], h[1]))[:MAX_LINES]]
    out.append(f"WARN ADV-{CHECK} summary: {len(pad_hits)} types over {PAD_PCT:g}% pad share, {len(open_hits)} with open port endpoints, "
               f"{measured} measured, {unmeasured} no retained kit")
    return out
