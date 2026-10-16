#!/usr/bin/env python3
"""H-MTP2 decision 4: the R-row compiled DSpark draft (hgi_sim.ds_mtp_draft) -- unit checks (seconds).

1. P = 1 FIDELITY: every draft body compiled at P = 1 (the bodies exactly as the sim priced them, fix_waits off)
   reproduces the row-serial launch's S2 cycles of results/arch/hbm_mtp_1015/sim1M_B/launches.json exactly.
2. WAIT FIX: the only undeclared RAW hazards in the bodies are the four SM matvecs Kernels.mv adds without an x read
   (dhead.lm_head, markov.head, seed.main_proj, seed.wkv0); with them fixed no compiled body has a schedule race
   except between the per-row copies of ONE record (the rows' HBM stores to row-indexed addresses -- DSKX / DLOG /
   KV ring slot / column slot -- that the timing resolves at one TOKEN / POS; their VM copies are disjoint).
3. BATCHING: on every ladder configuration the R-row draft is no slower than R x the row-serial bodies.

    python3 -m hgi_sim.test_mtp_draft          (from tools/)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from hgi_sim import ds_mtp_draft as D  # noqa: E402
from hgi_sim import ds_mtp_rows as RW  # noqa: E402
from hgi_sim import ds_mtp_verify as V  # noqa: E402
from hgi_sim import timing as T  # noqa: E402


def races(prog):
    with D.mtp_dyn():
        T.footprint = V._footprint
        try:
            s = T.schedule(V.rebuild(prog), V.DT.POS, "S2", cost_fn=V.cost_fn(None))
        finally:
            T.footprint = V._FP
    return [(x["tag"], x["producer"]) for x in s["races"]]


def main():
    L = json.loads(D.LAUNCHES.read_text())
    i0 = next(i for i, x in enumerate(L) if x["kind"] == "seed")
    sim = {}
    for x in L[i0:]:
        nm = x["kind"] + (str(x["Lp"]) if x["kind"] in ("dsa", "dsb") else "")
        sim.setdefault(nm, x["s2_cycles"])
    base = dict(sm_mode="serial", swap=True, rows=())
    for nm in D.NAMES:
        prog, _ = D.compile_body(nm, 1, base, fix_waits=False)
        got = D.time_prog(prog)["cycles"]
        assert abs(got - sim[nm]) < 0.05, (nm, got, sim[nm])
    print(f"1. P = 1: {len(D.NAMES)} bodies == the row-serial launch S2 cycles")
    c = D.ctx()
    fixed = {nm: [c["bodies"][nm][i].tag for i, _, _ in D.undeclared_raw(c["bodies"][nm])] for nm in D.NAMES}
    assert {k: v for k, v in fixed.items() if v} == dict(dhead=["dhead.lm_head"], markov=["markov.head"],
                                                         seed=["seed.main_proj", "seed.wkv0"]), fixed
    for items in ((), ("COLL", "FUSED", "HC", "SU_DMA", "IDX", "ATT", "VM", "SM_K2")):
        cfg = RW.cfg_of(items)
        for nm in D.NAMES:
            for P in (1, D.R):
                bad = {(t, p_) for t, p_ in races(D.compile_body(nm, P, cfg)[0]) if t != p_}
                assert not bad, (items, nm, P, bad)
    print("2. undeclared SM reads: exactly the 4 known; fixed, no schedule race between different records")
    ser = {nm: D.time_prog(D.compile_body(nm, 1, base)[0])["cycles"] for nm in ("dsa0", "dsb0", "dhead", "seed")}
    for items in ((), ("COLL", "FUSED", "HC"), ("COLL", "FUSED", "HC", "SU_DMA", "IDX", "ATT"),
                  ("COLL", "FUSED", "HC", "SU_DMA", "IDX", "ATT", "VM", "SM_HOLD"),
                  ("COLL", "FUSED", "HC", "SU_DMA", "IDX", "ATT", "VM", "SM_K2")):
        cfg = RW.cfg_of(items)
        for nm, P in (("dsa0", D.R), ("dsb0", D.R), ("dhead", D.R), ("seed", V.GAMMA + 1)):
            got = D.time_prog(D.compile_body(nm, P, cfg)[0])["cycles"]
            swaps = (V.SWAP_IN + (V.SWAP_OUT if nm != "dhead" else 0)) * P if cfg["swap"] and nm != "seed" else 0.0
            assert got <= P * ser[nm] + swaps + 1e-6, (items, nm, got, P * ser[nm] + swaps)
    print("3. R-row draft bodies <= R x row-serial (+ the same column swaps) on every ladder configuration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
