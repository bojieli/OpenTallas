#!/usr/bin/env python3
"""Compose the Qwen3-8B HBM accelerator tile die's power from the measured W12 tile element (P8191, TP4 AR).

Inputs (results/rtl/hbm_accel_qwen_die_power_20261006/):
  stages.json             per traced stage: cycles, fabric clock edges (ME_IDLE_GATE), die stream words, exactness
  activity/<st>_tNNNN.json  per traced tile: replay exactness + negative control, ROM/KV reads, SAIF windows, flop map
  ports.json              toggle density of the tile's bus ports per stage
  power_<corner>.json     OpenSTA design power of the routed tile_tp4_t4 per SAIF label (watts while clocked)

Every tile term is measured (routed netlist + SPEF + the exact decode's register activity).  The rest of the die is
composed from measured quantities where they exist and otherwise carries the floorplan's assumption, graded per term.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FP = ROOT / "results/rtl/hbm_accel_qwen_die_floorplan_20261005"
OUT_DIR = ROOT / "results/rtl/hbm_accel_qwen_die_power_20261006"
F = 1.2e9
T = 1 / F
NT = 1536
COOL_W = 474.56
# traced tile -> (split-tree class, tiles of the die it stands for); k1 traced twice (tiles 0 and 1000)
CLASSES = {0: ("k1", 384), 1000: ("k1", 384), 1: ("k2", 384), 3: ("k3", 192), 7: ("k4", 96), 15: ("k5", 48),
           31: ("none", 48)}
# TP4 AR token at P8191 (results/rtl/qwen_hbmacc_p8191_20261004/measured_composition.json b_TP4_iso_silicon):
# stage type -> (count, traced stage whose tile energy it carries)
TOKEN = {"L0": (5, "L0"), "L5": (1, "L20"), "L6": (1, "L20"), "L20": (29, "L20"), "head": (1, "head")}
STAGE_PITCH_UM = 430.56
WIRE_F_PER_UM = 0.2e-15     # configs/hardware/technology.json operand_delivery basis: 0.2 pF/mm
REPEATER = 1.6              # same basis: repeater overhead on long wires
VDD = {"TT": 0.70, "SS": 0.63, "FF": 0.77}
PHY_PJ_B = {"oconnor_micro2017_io_both_ends": 0.80, "chae_jssc2024_4nm_hbm3": 0.29}
IDLE_W_STACK = 2.8          # configs/hardware/power_scenarios.json memory.idle_w_per_stack (assumed)
STACKS = 4
WORD_BYTES = 98304
# die wire classes (feasibility q3a wire_by_class) -> the bus activity they carry
WIRE_ACT = {"corridor": "bcast", "corridor_hop": "bcast", "head_chain": "bcast",
            "tree_block": "tree", "tree_spine": "tree", "spine_port": "tree",
            "fill": "fill", "fill_hop": "fill", "phy_dfi": "fill",
            "collective": "small", "link": "small", "stream_status": "small", "load": "small", "host": "small",
            "hub": "small", "clock_trunk": "clock"}
FABRIC_CLOCKED = {"bcast", "tree"}   # registers clocked by the gated fabric clock; the rest run every cycle


def tile_class(i: int, G: int = 6144, LT: int = 2, TCUT: int = 7) -> str:
    for k in range(1, TCUT - LT + 1):
        if i % (1 << k) == (1 << (k - 1)) - 1 and (i >> k) < (G >> (LT + k)):
            return f"k{k}"
    return "none"


def macro_table(corner: str) -> dict:
    out = {}
    for m, n in (("ot_sram_1rw_2048x128_m4", 8), ("ot_sram_1r1w_1024x256_m2_r2c2", 2)):
        t = json.loads((ROOT / f"physical/asap7_memory_macros/{m}/{m}.json").read_text())["timing"][corner.lower()]
        out[m] = dict(n=n, read_j=t["read_energy_fj"] * 1e-15, write_j=t["write_energy_fj"] * 1e-15,
                      leak_w=t["leakage_nw"] * 1e-9)
    return out


def tile_macro(act: dict, stream_words: int, cycles: int, corner: str) -> dict:
    """SRAM energy of one tile over one stage.  Code reads: bank 0 is the resident 1RW array (one 512 b word =
    4 macros: 2 group-pair columns x 2 wide), bank >= 1 the 1R1W window/tail (2 macros); KV reads 2,048 b = 8 x
    256 b 1R1W reads; window fill: one 512 b share of every die stream word = 2 1R1W writes.  Read energy is the
    liberty's clk internal power (the macro's read energy), write energy the memory compiler's, leakage the liberty's."""
    me = macro_table(corner)
    a, b = me["ot_sram_1rw_2048x128_m4"], me["ot_sram_1r1w_1024x256_m2_r2c2"]
    by_bank = {int(k): v for k, v in act["reads"]["rom_reads_by_bank"].items()}
    e = dict(code_resident_j=by_bank.get(0, 0) * 4 * a["read_j"],
             code_window_j=sum(v for k, v in by_bank.items() if k >= 1) * 2 * b["read_j"],
             kv_j=act["reads"]["kv_reads"] * 8 * b["read_j"], fill_j=stream_words * 2 * b["write_j"])
    e["dynamic_j"] = sum(e.values())
    e["leak_w"] = a["n"] * a["leak_w"] + b["n"] * b["leak_w"]
    e["leak_j"] = e["leak_w"] * cycles * T
    # bound: the liberty has no `when` on the clk internal power, so a macro on an ungated clock pays its read
    # energy on every edge it sees -- every macro on every fabric clock edge
    e["every_edge_bound_j"] = act["records"] * (a["n"] * a["read_j"] + b["n"] * b["read_j"])
    return e


def compose(d: Path) -> dict:
    stages = json.loads((d / "stages.json").read_text())
    acts = {p.stem: json.loads(p.read_text()) for p in sorted((d / "activity").glob("*.json"))}
    ports = json.loads((d / "ports.json").read_text())
    wire = json.loads((FP / "feasibility.json").read_text())["cases"]["q3a/b_k16_i50"]["wire_by_class"]
    wst = json.loads((FP / "wire_stages.json").read_text())["qwen_8k"]["b_TP4_iso_silicon"]
    fpp = json.loads((FP / "floorplan.json").read_text())["power"]
    token_cycles = wst["priced_cycles"]
    t_token = token_cycles * T
    res = {"schema": "opentallas.hbm-accel-qwen-die-power.v1", "clock_hz": F, "cooling_limit_w": COOL_W,
           "token": dict(cycles=token_cycles, seconds=t_token, basis="floorplan-priced TP4 AR token at P8191 "
                         "(wire_stages.json qwen_8k.b_TP4_iso_silicon.priced_cycles, routed-bound wire stages)",
                         stages=TOKEN, ar_tok_s=wst["ar_tok_s_priced"]),
           "corners": {}}
    for corner in ("TT", "SS", "FF"):
        pf = d / f"power_{corner}.json"
        if not pf.exists():
            continue
        vals = json.loads(pf.read_text())["values"]

        def P(label, grp="total", part="total"):
            return vals[f"{label}.{grp}.{part}_w"]
        cr: dict = {"vectorless_tile_w": P("vectorless"), "stages": {}}
        for st, s in stages.items():
            tiles = {}
            for tile, (cls, n) in CLASSES.items():
                key = f"{st}_t{tile:04d}"
                if key not in acts:
                    continue
                a = acts[key]
                assert tile_class(tile) == cls, (tile, cls)
                assert a["replay_exact"] and a["negative_control"]["detected"], key
                lab = f"{st}/t{tile:04d}"
                p_on = P(f"{lab}/full")
                p_leak = P(f"{lab}/full", "total", "leakage")
                wins = {w: P(f"{lab}/{w}") for w in a["saifs"] if w != "full"}
                mac = tile_macro(a, s["stream_words"], s["cycles"], corner)
                e_logic = (p_on - p_leak) * a["records"] * T + p_leak * s["cycles"] * T
                tiles[key] = dict(cls=cls, n=n, clocked_cycles=a["records"], p_clocked_w=p_on, p_leak_w=p_leak,
                                  groups_w={g: P(f"{lab}/full", g) for g in ("sequential", "combinational", "clock")},
                                  p_window_max_w=max(wins.values()) if wins else p_on,
                                  window_max=max(wins, key=wins.get) if wins else "full",
                                  e_logic_j=e_logic, macro=mac, e_tile_j=e_logic + mac["dynamic_j"] + mac["leak_j"])
            w = NT / sum(v["n"] for v in tiles.values())
            die = lambda f: w * sum(v["n"] * f(v) for v in tiles.values())  # noqa: E731
            e_stage = die(lambda v: v["e_tile_j"])
            cr["stages"][st] = dict(
                cycles=s["cycles"], fabric_clocked_cycles=s["edges"], duty=s["edges"] / s["cycles"], tiles=tiles,
                die_tiles_clocked_w=die(lambda v: v["p_clocked_w"]),
                die_tiles_window_peak_w=die(lambda v: v["p_window_max_w"]),
                die_tiles_leak_w=die(lambda v: v["p_leak_w"] + v["macro"]["leak_w"]),
                die_macro_dynamic_j=die(lambda v: v["macro"]["dynamic_j"]),
                die_macro_every_edge_bound_j=die(lambda v: v["macro"]["every_edge_bound_j"]),
                die_tiles_energy_j=e_stage, die_tiles_stage_avg_w=e_stage / (s["cycles"] * T),
                groups_clocked_w={g: die(lambda v, g=g: v["groups_w"][g]) for g in ("sequential", "combinational", "clock")})
        # ---- token: tiles + macros (measured)
        e_tiles = sum(cnt * cr["stages"][src]["die_tiles_energy_j"] for cnt, src in TOKEN.values())
        clocked = sum(cnt * cr["stages"][src]["fabric_clocked_cycles"] for cnt, src in TOKEN.values())
        p_tiles_avg = e_tiles / t_token
        ref = cr["stages"]["L20"]
        # ---- die wire + stage registers (composed: routed lengths x measured activity and per-flop energy)
        v = VDD[corner]
        flops_tile = acts["L20_t0000"]["saifs"]["full"]["map"]["flops"]
        t0 = ref["tiles"]["L20_t0000"]
        # per register per clocked cycle: the tile's clock network + flop internal power at its measured activity
        e_ff = (t0["groups_w"]["clock"] + t0["groups_w"]["sequential"]) / flops_tile * T
        dens = {}
        for st in stages:
            pk = [ports[k] for k in ports if k.startswith(st + "_t")]
            mean = lambda g: sum(p[g]["toggles_per_bit_per_clocked_cycle"] or 0 for p in pk) / len(pk)  # noqa: E731
            dens[st] = dict(bcast=(379 * mean("ib") + 128 * mean("xl")) / 507,
                            tree=(mean("t_out") + mean("n_y") + mean("n_a") + mean("n_b")) / 4)
        buses = json.loads((FP / "floorplan.json").read_text())["bus_classes"]
        stream_bits_pk = max(st_["stream_words"] * WORD_BYTES * 8 / st_["cycles"] for st_ in stages.values())
        stream_bits_per_cycle = sum(cnt * stages[src]["stream_words"] for cnt, src in TOKEN.values()) * WORD_BYTES * 8 / token_cycles
        wires = {}
        for cls, info in wire.items():
            kind = WIRE_ACT.get(cls, "small")
            c = info["wire_m"] * 1e6 * WIRE_F_PER_UM * REPEATER
            regs = info["wire_m"] * 1e6 / STAGE_PITCH_UM if kind != "clock" else 0.0
            if kind in FABRIC_CLOCKED:
                # transitions per wire per core cycle averaged over the token
                tr = sum(cnt * dens[src][kind] * stages[src]["edges"] for cnt, src in TOKEN.values()) / token_cycles
                duty = clocked / token_cycles
                tr_pk = max(dens[s][kind] for s in stages)
            elif kind == "fill":
                # random stream data: 0.5 transitions per bit transfer; utilisation = stream bits per cycle over the
                # class's parallel wires (floorplan bus_classes); a fill hop carries on average half its column's words
                n_w = buses[cls]["wires"]
                share = 0.5 if cls == "fill_hop" else 1.0
                tr = 0.5 * min(1.0, share * stream_bits_per_cycle / n_w)
                tr_pk = 0.5 * min(1.0, share * stream_bits_pk / n_w)
                duty = 1.0
            elif kind == "clock":
                tr, duty, tr_pk = 2.0 * clocked / token_cycles, 1.0, 2.0
            else:
                tr, duty, tr_pk = 0.05, 1.0, 0.05
            p_wire = 0.5 * c * v * v * tr * F
            p_regs = regs * e_ff * duty * F
            p_wire_pk = 0.5 * c * v * v * tr_pk * F
            p_regs_pk = regs * e_ff * F
            wires[cls] = dict(wire_m=info["wire_m"], kind=kind, cap_f=c, stage_registers=regs, transitions_per_cycle=tr,
                              avg_w=p_wire + p_regs, peak_w=p_wire_pk + p_regs_pk)
        p_wire_avg = sum(x["avg_w"] for x in wires.values())
        p_wire_pk = sum(x["peak_w"] for x in wires.values())
        # ---- HBM PHY (published host-interface energy) + per-stack idle (assumed)
        hbm_Bps = sum(cnt * stages[src]["stream_words"] for cnt, src in TOKEN.values()) * WORD_BYTES / t_token
        hbm_pk_Bps = max(s["stream_words"] * WORD_BYTES / (s["cycles"] * T) for s in stages.values())
        phy = {k: dict(avg_w=hbm_Bps * 8 * pj * 1e-12 + IDLE_W_STACK * STACKS, peak_w=hbm_pk_Bps * 8 * pj * 1e-12 + IDLE_W_STACK * STACKS)
               for k, pj in PHY_PJ_B.items()}
        # ---- floorplan assumptions kept (not measured): stream services, spine (core/port/scale/SU), hub, heads, waypoints
        assumed = {k: fpp["by_kind"][k] for k in ("svc", "spine", "hub", "head", "waypoint")}
        p_assumed = sum(assumed.values())
        phy_sel = phy["oconnor_micro2017_io_both_ends"]
        die_avg = p_tiles_avg + p_wire_avg + phy_sel["avg_w"] + p_assumed
        peak_tiles = max(s["die_tiles_window_peak_w"] for s in cr["stages"].values())
        clocked_tiles = max(s["die_tiles_clocked_w"] for s in cr["stages"].values())
        macro_pk = max((s["die_macro_dynamic_j"] / max(1, s["fabric_clocked_cycles"]) / T) for s in cr["stages"].values())
        die_peak = peak_tiles + macro_pk + p_wire_pk + phy_sel["peak_w"] + p_assumed
        die_clocked = clocked_tiles + macro_pk + p_wire_pk + phy_sel["peak_w"] + p_assumed
        static = ref["die_tiles_leak_w"]
        other_avg = p_wire_avg + phy_sel["avg_w"] + p_assumed
        cr["token"] = dict(
            fabric_duty=clocked / token_cycles, tiles_energy_j=e_tiles, tiles_avg_w=p_tiles_avg,
            die_wire_avg_w=p_wire_avg, die_wire_peak_w=p_wire_pk, wires=wires, e_register_clocked_j=e_ff,
            port_density=dens, hbm_avg_Bps=hbm_Bps, hbm_peak_Bps=hbm_pk_Bps, phy=phy, assumed_floorplan_w=assumed,
            die_avg_w=die_avg, die_avg_w_per_mm2=die_avg / 828.17, tiles_avg_w_per_mm2=p_tiles_avg / 669.077,
            die_peak_window_w=die_peak, die_in_phase_clocked_w=die_clocked,
            tiles_in_phase_clocked_w=clocked_tiles, tiles_window_peak_w=peak_tiles,
            tiles_clocked_w_per_mm2=clocked_tiles / 669.077, tiles_static_w=static,
            margin_avg_w=COOL_W - die_avg, verdict_avg="PASS" if die_avg <= COOL_W else "FAIL",
            verdict_peak="PASS" if die_peak <= COOL_W else "EXCEEDS (sub-microsecond; thermal budget is time-averaged)",
            # duty the fabric could run at (batched fill of idle stages) before the time-averaged budget binds
            die_J_per_token=die_avg * t_token, tiles_J_per_token=e_tiles,
            # OpenSTA propagates the mapped register activity through the logic probabilistically: on the routed argmax
            # the combinational part came out up to 2.1x the gate-level value (docs/POWER_CLOCK_SIGNOFF.md), so the
            # combinational share is an upper bound; halving it gives the lower edge of the tile figure
            tiles_clocked_combinational_w=max(s_["groups_clocked_w"]["combinational"] for s_ in cr["stages"].values()),
            tiles_avg_w_if_comb_halved=p_tiles_avg - 0.5 * sum(
                cnt * cr["stages"][src]["groups_clocked_w"]["combinational"] * cr["stages"][src]["fabric_clocked_cycles"] * T
                for cnt, src in TOKEN.values()) / t_token,
            # the floorplan's static IR solve loaded the tiles at the assumed 702.53 W; linear scaling to the measured
            # in-phase window peak (derived, not re-solved)
            ir_worst_mv_scaled_to_window_peak=23.54 * peak_tiles / fpp["by_kind"]["tile"],
            max_fabric_duty_at_budget=min(1.0, (COOL_W - other_avg - static) / max(1e-9, (clocked_tiles - static))),
        )
        res["corners"][corner] = cr
    res["inputs"] = dict(stages=stages, ports=ports, wire_by_class={k: v["wire_m"] for k, v in wire.items()},
                         floorplan_power_assumed=fpp)
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, default=OUT_DIR)
    a = ap.parse_args()
    r = compose(a.dir)
    (a.dir / "die_power.json").write_text(json.dumps(r, indent=1) + "\n")
    for c, cr in r["corners"].items():
        t = cr["token"]
        print(f"{c}: tiles clocked {t['tiles_in_phase_clocked_w']:.1f} W ({t['tiles_clocked_w_per_mm2']:.3f} W/mm2), "
              f"window peak {t['tiles_window_peak_w']:.1f}; duty {t['fabric_duty']:.3f}; token avg tiles {t['tiles_avg_w']:.1f} W, "
              f"wire {t['die_wire_avg_w']:.1f}, die avg {t['die_avg_w']:.1f} W ({t['verdict_avg']}), die peak {t['die_peak_window_w']:.1f}, "
              f"max duty at budget {t['max_fabric_duty_at_budget']:.3f}")


if __name__ == "__main__":
    main()
