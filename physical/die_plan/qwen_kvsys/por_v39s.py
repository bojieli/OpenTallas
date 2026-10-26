#!/usr/bin/env python3
"""KV plan delta v3.9s item (a) (PATH-KV-POR 10-25): the SYS_C POR seam = ONE die reset pad.

    python3 por_v39s.py            (in physical/die_plan/qwen_kvsys; idempotent)

PATH-KV DECISION 2026-10-25 14:19 (points 1-5) with CLOCK-RESET amendments A/B (14:32), reset decision 2 (whole-die
root + neighbour wavefront, static offsets, START broadcast control-only, no constant ties):
  die_io.json   io_pad_por_n {kind die_root_pad, iface reset, part = the reset root partition (hub_C), rect over the
                gen_phys.die_root_pins 'rst_n' pin, pad_port = the as-built top port pad_por_n}: the die reset ROOT pin;
                the bound top's separate rst_n and pad_por_n inputs merge into it (one reset false path).
  reset.source  pad io_pad_por_n; analog_loads = the PLL por_n (u_pll.por_n, the only declared raw analog load besides
                u_rst_root); por_pins "por_n" (every other digital power-on reset leaf input is rebound by bind.py to its
                partition's delivered wavefront reset: sys_c u_d2d_kv.por_n, hub_Wi host, hub_C kvs_ctl); lock = PLL
                locked through the root lock qualifier ot_dp_lockq (2-flop sync + 16 stable cycles, sticky): the root
                releases synchronously after sync(por) AND lock-stable; loss of lock later = HOST status.
  start_role    bootstrap for the types holding rebound POR leaves (kv3_sys_c: D2D + UCIe phy_rst_n tap = amendment B;
                kv3_hub_Wi host; kv3_hub_C kvs_ctl): power-on resets cannot wait for START.  (Codex candidate
                codex/kv-plan-1309@aef2c30627 carries these three among its 33 bootstrap types.)
Cycle effect: every published release offset shifts by +lock_stages (16 + 3 = 19) clocks (root entry 2 -> 21); the
three types' control state releases at the raw wavefront offset instead of S + offset (reset_offsets_v39s.json)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
import gen_phys  # noqa: E402
import schema as S  # noqa: E402

PAD = "io_pad_por_n"
BOOT = ("kv3_sys_c", "kv3_hub_Wi", "kv3_hub_C")


def main():
    fp, fio = HERE / "die_plan.json", HERE / "die_io.json"
    raw = json.loads(fp.read_text())
    io = json.loads(fio.read_text())
    raw["reset"]["source"] = {
        "part": "@die", "bus": "rst_n", "pad": PAD,
        "analog_loads": [{"inst": "u_pll", "pin": "por_n",
                          "note": "PLL analog power-on reset: the clock source cannot be synchronised to itself"}],
        "por_pins": "por_n",
        "lock": {"inst": "u_pll", "pin": "locked", "stable_cycles": 16},
        "note": "PATH-KV DECISION 10-25 14:19 + CLOCK-RESET A/B 14:32: one reset pad = die reset root pin; raw loads "
                "{u_rst_root.async_rst_n, u_pll.por_n}; por_n leaves rebound to the wavefront; lock qualifies the "
                "root release synchronously (por_gate.py)"}
    for tn in BOOT:
        raw["partition_types"][tn].setdefault("reset", {})["start_role"] = "bootstrap"
    P = S.Plan(raw, fp)
    x, y = next((x, y) for n, _L, x, y in gen_phys.die_root_pins(P) if n == "rst_n")
    import reset_tree as RT
    root = RT.wf_solve(P)["root"]
    h = 4.32
    ent = dict(name=PAD, kind="die_root_pad", iface="reset", part=root,
               rect_um=[round(x - h, 4), round(y - h, 4), round(x + h, 4), round(y + h, 4)], sites=1, signals=1,
               pad_port="pad_por_n",
               basis="the die's ONE external reset pad (power-on reset) = the die reset root pin gen_phys.die_root_pins "
                     "'rst_n' (spine root + 8.64 um, M8); bump/RDL to the pin",
               note="PATH-KV-POR v3.9s(a): raw loads only u_rst_root.async_rst_n + u_pll.por_n in the root partition")
    io = [w for w in io if w.get("name") != PAD] + [ent]
    fp.write_text(json.dumps(raw, indent=1) + "\n")
    fio.write_text(json.dumps(io, indent=1) + "\n")
    print(f"{PAD} at ({x:.3f}, {y:.3f}) part {root}; bootstrap {list(BOOT)}")


if __name__ == "__main__":
    main()
