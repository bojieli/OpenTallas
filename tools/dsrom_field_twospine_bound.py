#!/usr/bin/env python3
"""DS-ROM two-spine field study (CLAUDE TWO-SPINE, 2026-10-06): geometry bound, no RTL. OWNER 2026-10-06: REJECT (NO-GO on two spines).

Proposal: two field spines a layer die, each serving half the field, to halve the far frame's round trip (139/140
stages on the wired r8 die).  x starts at the hub VM and every row returns to the hub VM (SU / HC read it there), so
for ANY spine organisation a frame's field round trip is >= 2 x ceil(Manhattan(VM centre, frame column feed) /
430.56 um) + the fixed stages (entry meso 2 + slot stations + column return register + root stages + hub meso 2).
A spine away from the VM only adds a VM -> spine and a spine -> VM leg.

This tool builds the r8 layer and 1-stack dies (tools/dsrom_s81_fulldie.py --gen r8, f157.68, unchanged), writes the
per-frame round trip against that floor, and composes AR / MTP (tools/dsrom_field_reprice_r8.py node rule,
tools/dsrom_1m_allmeasured.compose, tools/three_machine_compose.py conditional row) for:
  base   the committed r8 re-price (main);
  floor  every frame at min(its r8 round trip, the Manhattan floor)  -- the best any spine count / trunk can reach;
  half   the proposal's claim taken literally: every round trip halved + 3 merge cycles (physically unreachable;
         an upper bound on the lever).

    python3 tools/dsrom_field_twospine_bound.py      (~1 min, 1 core)  -> results/rtl/dsrom_field_twospine_20261006/
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_field_reprice_r8 as R  # noqa: E402

OUT = ROOT / "results/rtl/dsrom_field_twospine_20261006"
GK = "f157.68"
MERGE = 3


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def frame_floor():
    import dsrom_s81_fulldie as S
    out = {}
    for die in R.DIES:
        S.configure(die, "r8")
        S.slot_geometry(R.GEOMS[GK]["elem_h"])
        S.set_pairs(R.GEOMS[GK]["pairs"])
        m = S.build()
        S.finalize_r8(m)
        by = {it.name: it for it in m["insts"]}
        vm = m["hub"]["vm"]
        vx, vy = vm.x + vm.w / 2, vm.y + vm.h / 2
        for r, f in m["frames"].items():
            it = by[f"cf{r}"]
            cx, cy = it.x + it.w / 2, it.y + it.h / 2
            md = abs(cx - vx) + abs(cy - vy)
            xs, rs = m["x_stages"][r], m["r_stages"][r]
            fixed = 2 + f["last_slot"] + 1 + 1 + f.get("ret_stages", 0) + 2
            one = math.ceil(md / R.STAGE_UM - 1e-9)
            out[f"{die}:{int(r)}"] = dict(half=f["half"], tier=f["tier"], col=f["col"], frame_um=[round(cx, 1), round(cy, 1)],
                                          vm_um=[round(vx, 1), round(vy, 1)], manhattan_um=round(md, 1),
                                          manhattan_stages_one_way=one, x_trunk=xs, return_trunk=rs, fixed=fixed,
                                          rt=xs + rs + fixed, floor_rt=2 * one + fixed,
                                          excess=xs + rs + fixed - (2 * one + fixed))
    return out


def relevered(td, AD):
    """a scratch copy of the recovery levers with field_spine / field_spine_pq node times re-priced from the
    patched reprice table (tools/dsrom_field_reprice_r8.relever semantics; their stored us follow the committed one)"""
    import shutil
    import dsrom_1m_measure as M
    import three_machine_compose as TM
    g, _, _ = M.s58_graph()
    rec_dir = td / "recovery"
    shutil.copytree(TM.RECOVERY / "levers", rec_dir / "levers")
    for lever in R.LEVER_CONFIG:
        f = rec_dir / "levers" / f"{lever}.json"
        lr = json.loads(f.read_text())
        rec = json.loads((ROOT / lr["measurement"]["record"]).read_text())
        for name, (sec, src, cls, _m) in AD.field_rows(g, rec, geom=GK).items():
            lr["nodes"][name] = dict(lr["nodes"][name], us=round(sec * 1e6, 6))
        f.write_text(json.dumps(lr))
    return rec_dir


def wire(geo, hub, rt_of):
    W = {}
    for d, g in geo.items():
        h = hub[d]
        for r, f in g["frames"].items():
            w = rt_of(d, int(r), f["rt"]) - R.BST_IN_VEHICLE + h["hr_added_by_tier_half"][f"{f['half']}{f['tier']}"] \
                + h["gather_capture_added"] + h["capture_vm_added"]
            W[int(r)] = max(W.get(int(r), 0), w)
    return W


def main():
    import dsrom_1m_allmeasured as D
    import dsrom_1m_allmeasured_adapters as AD
    import three_machine_compose as TM
    fl = frame_floor()
    geo = R.load_geo(GK)
    hub = R.hub_terms(geo)
    for d, g in geo.items():          # the generator rebuild must reproduce the committed geometry
        for r, f in g["frames"].items():
            assert fl[f"{d}:{r}"]["rt"] == f["rt"], (d, r, fl[f"{d}:{r}"]["rt"], f["rt"])
    kinds = dict(base=lambda d, r, rt: rt,
                 floor=lambda d, r, rt: min(rt, fl[f"{d}:{r}"]["floor_rt"]),
                 half=lambda d, r, rt: math.ceil(rt / 2) + MERGE)
    rp = json.loads((R.OUT / "reprice.json").read_text())
    regs = {c: R.load_regions(R.OUT / p) for c, (p, _) in R.CONFIGS.items()}
    joint = json.loads((ROOT / "results/arch/three_machine_compose/compose.json").read_text())["ds_rom"]["conditional_all"]["levers"]
    rows = {}
    try:
        for k, fn in kinds.items():
            W = wire(geo, hub, fn)
            rec = copy.deepcopy(rp)
            for c, reg in regs.items():
                new = R.summarise(R.node_table(reg, lambda r: W[r]))
                for v in new.values():
                    v["old_total_cycles"] = None
                rec["geoms"][GK]["configs"][c] = new
            with tempfile.TemporaryDirectory(dir=OUT) as td:
                p = Path(td) / "reprice.json"
                p.write_text(json.dumps(rec))
                AD.REPRICE, AD.FIELD_GEOM = p, GK
                AD._RP.clear()
                h = TM._row(D.compose(TM._args(TM.RECOVERY), write_output=False))
                with tempfile.TemporaryDirectory() as t2:
                    j = TM._row(TM._with_flipped(relevered(Path(t2), AD), Path(t2), joint))
            rows[k] = dict(wire_per_region=dict(max=max(W.values()), mean=round(sum(W.values()) / len(W), 2)),
                           headline=h, conditional_all=j)
            print(k, rows[k]["wire_per_region"], "AR", h["AR_tok_s"], "MTP", h["MTP_tok_s"], "| cond", j["AR_tok_s"],
                  j["MTP_tok_s"], flush=True)
    finally:
        AD.REPRICE = R.OUT / "reprice.json"
        AD._RP.clear()
    for k in ("floor", "half"):
        rows[k]["delta_pct_vs_base"] = {
            f"{s}_{m}": round(100 * (rows[k][s][m] / rows["base"][s][m] - 1), 2)
            for s in ("headline", "conditional_all") for m in ("AR_tok_s", "MTP_tok_s")}
    far = {k: fl[k] for k in ("layer:127", "layer:73", "layer1:73", "layer1:127")}
    excess = sorted(({"frame": k, **{x: v[x] for x in ("half", "tier", "col", "x_trunk", "return_trunk", "rt",
                                                         "manhattan_stages_one_way", "floor_rt", "excess")}}
                     for k, v in fl.items() if v["excess"] > 0), key=lambda e: (-e["rt"], e["frame"]))
    rec = dict(schema="opentallas.dsrom-field-twospine.v1",
               verdict="REJECT",
               reason=("x leaves the hub VM and every row returns to it, so the round trip is >= 2 x Manhattan(VM, "
                       "frame) + fixed stages for any spine count; a second spine cannot halve it. Even the literal "
                       "claim (every round trip halved + 3 merge cycles) stays below the >= 5% AR gate."),
               gate="ADOPT only if >= 5% AR, exact, routes (owner rule for optional levers)",
               farthest_frames=far, rows=rows,
               trunk_straightening=dict(note="the reachable part: r8 x / return trunks above the Manhattan floor "
                                             "(owner of tools/dsrom_s81_fulldie.py main line: Claude S81-RERUN)",
                                        frames_with_excess=excess),
               inputs={R.rel(R.OUT / "reprice.json"): sha(R.OUT / "reprice.json"),
                       "tools/dsrom_s81_fulldie.py": sha(ROOT / "tools/dsrom_s81_fulldie.py")},
               tool_sha256={R.rel(Path(__file__)): sha(Path(__file__))})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "twospine_bound.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("deltas", {k: rows[k]["delta_pct_vs_base"] for k in ("floor", "half")})
    print("far", {k: (v["rt"], v["floor_rt"], v["manhattan_stages_one_way"]) for k, v in far.items()})


if __name__ == "__main__":
    main()
