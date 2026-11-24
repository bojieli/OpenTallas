#!/usr/bin/env python3
"""adv_cell_budget.py -- PRECHECK-CELLCAP (COORD 11-23 22:3x): static mapped-cell projection of every soft type, slot overhead included.

Why: S81 kv_leaf t2 measured 658,649 mapped cells as handed (517,668 with hard exit relays) and about 340k of it was die
feed-through placed in its slot (15 ft clock landings + 111 ft stations + glue); QC fw and KV pv / hg types also met the
400k OpenROAD cap only at synthesis or placement.  Every term below is already in the plan, so the projection runs before
launch.  ADVISORY: WARN ADV-CELL-BUDGET lines only, never a FAIL.

projected synth cells of a soft type = max(content + slot overhead, retained kit synth count, plan type.cells)

  slot overhead (ASAP7 RVT, yosys + abc; ASAP7 has QN-only flops, so every stage bit is one DFF + one INV):
    ft stations       K_STAGE x sum(ft_slots[].width x stations)                 ot_dp_st W = 2W + 2 cells (t2 whole3: 111
                                                                                   stations, 86,374 cells, model 86,152)
    internal stations K_STAGE x sum(internal_stations[].bits x len(regs_um))     bits missing -> the named bus width, else unsized
    clock landings    per band max(LAND_MIN, LAND_K x padded flops - LAND_B)     padded = clock.landing_contract.bands[].
                                                                                   padded_data_storage_flops, else 5 x ring_width,
                                                                                   else 5 x (width + 64)  (t2 whole3: 19 landings
                                                                                   186,608 cells incl. their dsel / wen submodules)
    relays            K_STAGE x sum(relay_depth[] bits x D)
  content: a measured whole-type content (cell_budget_modules.json "types", keyed by base type, slot terms excluded), else the
           soft contents[] (not a hard core instance) whose module has a measured count there ("modules": summed, "modules k/n"
           says how many were found, a partial sum is a lower bound).  Hard cores and macros cost 0.  A define-specific count
           (rec.defines) wins when the type carries that verilog define.
  kit:     the retained synth count of this type (or its __cl/__pv base) from the PRECHECK cells cache, if younger than 72 h.
           The kit's own plan overhead is not retained, so a kit count is a floor, never adjusted.  plan type.cells is a floor
           only on a type without hard cores (with cores it counts their content).
  K_STAGE is 1.15 instead of 2 on types whose chains alternate polarity (dly_alt_pol, OT_DLY_CPL, OT_ST_QNALT).

Flag: projected synth > FLAG_SYNTH (350k); place ~ synth x PLACE_GROWTH (1.28 measured floorplan -> place) against the 400k
cap.  The line names the largest terms so the owner sees whether the slot (feed-through, landings) or the content is the lever.

    python3 -I tools/die_plan/adv_cell_budget.py PLAN.json [--types REGEX] [--all] [--json OUT]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

CHECK = "CELL-BUDGET"
FLAG_SYNTH = 350_000
PLACE_GROWTH = 1.28
CAP = 400_000
K_STAGE = 2.0                 # DFF(QN) + INV per stage bit
K_STAGE_ALT = 1.15            # alternating-polarity chains (KV dly_alt_pol, QC OT_DLY_CPL / OT_ST_QNALT): the INV per stage goes
ALT_DEFINES = ("OT_DLY_CPL", "OT_ST_QNALT")
KIT_MAX_AGE_S = 72 * 3600     # an older kit count predates tonight's hard-core / split structure (S81 svc 5.1M flat kits of 11-20)
LAND_K, LAND_B, LAND_MIN = 5.0, 500.0, 660.0    # t2 whole3: 1104 b 28,526 / 597 b 15,7xx / 276 b 7,714 / 70 b 2,670 / W=2 659
LAND_SMALL_P = 320            # a 320-flop padded band is the W<=64 minimum ring: the W=2 monitor landing, 659 cells
LITE_K, LITE_B = 20.0, 60.0
HERE = Path(__file__).resolve().parent
MODULES_FILE = HERE / "cell_budget_modules.json"
SUFFIX = re.compile(r"(?:__(?:cl|pv)[0-9a-f]{6,})+$")


def _i(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _bits(b):
    if isinstance(b, (list, tuple)) and len(b) == 2 and all(isinstance(x, int) for x in b):
        return abs(b[1] - b[0]) + 1
    if isinstance(b, (list, tuple)):
        return len(b)
    return _i(b)


def band_cells(b, narrow=False):
    """mapped cells of one clock-landing band (ot_dp_clk_landing_cas + its submodules).  A narrow-ring type's small bands
    (ring_place not 'ff') are lite landings: ~20 cells per bit (KV pv D28 model: 49 / 702 / 3,040 cells)."""
    w = _i(b.get("width"))
    if narrow and b.get("ring_place") != "ff" and w:
        return LITE_B + LITE_K * w
    p = _i(b.get("padded_data_storage_flops"))
    if not p:
        roles = b.get("clock_roles") or {}
        p = _i(roles.get("forwarded_write_flops")) + _i(roles.get("local_read_flops"))
    if not p and _i(b.get("ring_width")):
        p = 5 * _i(b["ring_width"])
    if not p and w:
        p = 5 * (w + 64)
    if not p or p <= LAND_SMALL_P:
        return LAND_MIN
    return max(LAND_MIN, LAND_K * p - LAND_B)


def stage_k(t):
    defs = {str(x) for x in t.get("verilog_defines") or []}
    return K_STAGE_ALT if t.get("dly_alt_pol") or defs & set(ALT_DEFINES) else K_STAGE


def overhead(t):
    """{term: cells} of the plan content placed in the type's slot, plus 'unsized' internal station rows."""
    k = stage_k(t)
    ft = sum(_i(f.get("width")) * _i(f.get("stations")) for f in t.get("ft_slots") or [] if isinstance(f, dict))
    widths = {b.get("name"): _i(b.get("width")) for b in t.get("buses") or [] if isinstance(b, dict)}
    ist = unsized = 0
    for s in t.get("internal_stations") or []:
        if not isinstance(s, dict):
            continue
        n = len(s.get("regs_um") or [])
        b = _i(s.get("bits"))
        if not b:
            conn = str(s.get("conn") or "")
            b = widths.get(conn[4:], 0) if conn.startswith("bus:") else 0
        if b:
            ist += n * b
        elif n:
            unsized += 1
    bands = (((t.get("clock") or {}).get("landing_contract") or {}).get("bands")) or {}
    narrow = bool((t.get("clock") or {}).get("landing_ring_narrow"))
    land = sum(band_cells(b, narrow) for b in bands.values() if isinstance(b, dict)) if isinstance(bands, dict) else 0
    rel = sum(_bits(r.get("bits")) * _i(r.get("D")) for r in t.get("relay_depth") or [] if isinstance(r, dict))
    return dict(ft_stations=round(k * ft), internal_stations=round(k * ist), landings=round(land),
                relays=round(k * rel), stage_bits=ft + ist + rel, k_stage=k, n_landings=len(bands) if isinstance(bands, dict) else 0, unsized_ist=unsized)


def load_modules(path=None):
    """{"modules": {module: rec}, "types": {base type: rec}} of measured content counts (rec = {cells, defines?, src})."""
    p = Path(path) if path else MODULES_FILE
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        return {"modules": {}, "types": {}}
    ok = lambda tab: {k: v for k, v in (tab or {}).items() if isinstance(v, dict) and _i(v.get("cells"))}  # noqa: E731
    return {"modules": ok(d.get("modules")), "types": ok(d.get("types"))}


def module_cells(rec, defines):
    """measured count of a module under the type's verilog_defines (a define-specific count wins)."""
    for d in defines:
        if _i((rec.get("defines") or {}).get(d)):
            return _i(rec["defines"][d])
    return _i(rec.get("cells"))


def content(tn, t, modules):
    """(cells, basis word) of the type's soft content: a measured whole-type content (types table, slot excluded), else the
    soft contents with a measured module count (a partial sum is a lower bound)."""
    defines = [str(x) for x in t.get("verilog_defines") or []]
    trec = (modules.get("types") or {}).get(SUFFIX.sub("", tn))
    if trec:
        return module_cells(trec, defines), "measured type content"
    hard = {h.get("inst") for h in t.get("hard_cores") or [] if isinstance(h, dict)}
    soft = [c for c in t.get("contents") or [] if isinstance(c, dict) and c.get("inst") not in hard]
    cells = found = 0
    for c in soft:
        rec = (modules.get("modules") or {}).get(str(c.get("module") or ""))
        if rec:
            cells += module_cells(rec, defines)
            found += 1
    return cells, f"modules {found}/{len(soft)}"


def kit_cells(tn, cache_cells, now=None):
    """(synth cells, kit type name) of the newest retained kit of this type or its base, if younger than KIT_MAX_AGE_S."""
    import time
    now = time.time() if now is None else now
    if not cache_cells:
        return None, None
    rec = cache_cells.get(tn)
    name = tn
    if not rec:
        base = SUFFIX.sub("", tn)
        cands = [n for n in cache_cells if n != tn and SUFFIX.sub("", n) == base]
        if not cands:
            return None, None
        name = max(cands, key=lambda n: ((cache_cells[n] or {}).get("last") or {}).get("t0", 0))
        rec = cache_cells[name]
    last = (rec or {}).get("last") if isinstance(rec, dict) and "last" in rec else rec
    c = _i((last or {}).get("cells"))
    t0 = float((last or {}).get("t0") or 0)
    if not c or now - t0 > KIT_MAX_AGE_S:
        return None, None
    return c, f"{name} {time.strftime('%m-%d %H:%M', time.localtime(t0))} {(last or {}).get('stage') or ''}".strip()


def project(tn, t, modules, cache_cells=None, now=None):
    ov = overhead(t)
    slot = ov["ft_stations"] + ov["internal_stations"] + ov["landings"] + ov["relays"]
    cc, cword = content(tn, t, modules)
    struct = cc + slot
    kit, kit_name = kit_cells(tn, cache_cells, now)
    plan_cells = 0 if t.get("hard_cores") else _i(t.get("cells"))     # with hard cores type.cells counts their content too
    est, basis = struct, f"content {cc:,} ({cword}) + slot {slot:,}"
    if kit and kit > est:
        est, basis = kit, f"retained kit synth {kit:,} ({kit_name})"
    if plan_cells and plan_cells > est:
        est, basis = plan_cells, f"plan type.cells {plan_cells:,}"
    return dict(type=tn, est=est, basis=basis, structural=struct, content=cc, content_basis=cword,
                slot=slot, kit=kit, plan_cells=plan_cells or None, place=round(est * PLACE_GROWTH), **ov)


def _cache(cells_cache, die):
    """{type: record} of this die from the PRECHECK cells cache (a path, a loaded cache dict, or None = the default file)."""
    if isinstance(cells_cache, dict):
        cache = cells_cache
    else:
        try:
            from adv_density import load_cache
        except ImportError:
            return {}
        cache, _ = load_cache(cells_cache)
    return (((cache or {}).get("cells") or {}).get(die)) or {}


def rows(raw, cells_cache=None, modules=None, types=None, everything=False, now=None):
    T = raw.get("partition_types") or {}
    placed = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
    mods = load_modules() if modules is None else modules
    cache = _cache(cells_cache, (raw.get("die") or {}).get("name"))
    pat = re.compile(types) if types else None
    out = []
    for tn, t in T.items():
        if not isinstance(t, dict) or t.get("hard"):
            continue
        if pat and not pat.search(tn):
            continue
        if not everything and placed and tn not in placed:
            continue
        out.append(project(tn, t, mods, cache, now))
    return out


def _terms(r):
    terms = [("ft stations", r["ft_stations"]), (f"{r['n_landings']} landings", r["landings"]),
             ("internal stations", r["internal_stations"]), ("relays", r["relays"]), ("content", r["content"])]
    return ", ".join(f"{k} {v:,}" for k, v in sorted(terms, key=lambda kv: -kv[1]) if v)


def findings(raw, plan_path, tree=None, cells_cache=None, **_kw):
    rr = rows(raw, cells_cache=cells_cache)
    hits = sorted((r for r in rr if r["est"] > FLAG_SYNTH), key=lambda r: -r["est"])
    out = []
    for r in hits:
        slot_word = f"; slot alone {r['slot']:,} ({_terms(r)})" if r["slot"] else ""
        out.append(f"WARN ADV-{CHECK} {r['type']}: projected {r['est']:,} synth cells > {FLAG_SYNTH:,} "
                   f"(place ~{r['place']:,} vs {CAP:,} cap) from {r['basis']}{slot_word}")
    if rr:
        slot_heavy = sum(1 for r in rr if r["slot"] > FLAG_SYNTH)
        out.append(f"WARN ADV-{CHECK} summary: {len(hits)} of {len(rr)} soft types projected over {FLAG_SYNTH:,} synth "
                   f"({slot_heavy} on slot overhead alone); max {max(r['est'] for r in rr):,}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--types")
    ap.add_argument("--all", action="store_true", help="also types no partition places")
    ap.add_argument("--cells-cache")
    ap.add_argument("--modules")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    sys.path.insert(0, str(HERE))
    rr = rows(raw, cells_cache=a.cells_cache, modules=load_modules(a.modules) if a.modules else None,
              types=a.types, everything=a.all)
    rr.sort(key=lambda r: -r["est"])
    for r in rr:
        flag = "OVER" if r["est"] > FLAG_SYNTH else "ok"
        print(f"{flag:4s} {r['type']:44s} est {r['est']:>9,}  slot {r['slot']:>9,}  [{_terms(r)}]  basis: {r['basis']}")
    if a.json:
        Path(a.json).write_text(json.dumps(rr, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
