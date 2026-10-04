#!/usr/bin/env python3
"""DeepSeek-V4.1 multi-token prediction on the hardwired decode core: with and
without MTP, ROM and HBM targets, side by side.

    python3 tools/hdc_v41_mtp_report.py --parts DIR --phys DIR [--output PATH]

Inputs (all measured; the formulas below are the only arithmetic):

* cycles: the RTL campaign parts (tools/rtl_hdc_v41_mtp_campaign.py): the
  one-position baseline (`--plain`, cycles per token) and, per target, lane
  multiplier m and gamma, the speculative step (draft cycles, verify-pass
  cycles, their sum);
* clock, area, power: the ASAP7 routes at 0.9 ns of the blocks MTP changes
  (matrix engine at 2 lane groups, quantised engine, hyper-connection engine,
  each at m = 1 and m = 4; the accept unit); the core runs at the slowest of
  its closed blocks' Fmax, capped by the 0.9 ns target;
* energy per step: logic = the V4.1 die's signed-off logic power
  (results/physical_abi3/asap7/signoff/energy_per_token.json, TT) times the
  step time, its replicated units scaled by their copies; weight reads = the
  weight words the program reads per step (each lane-multiplied op once) times
  the word's bytes times the store's energy per byte (ROM, or HBM for the QE
  weights of the HBM comparator); on-die SRAM as in the signoff record per
  position processed.

tok/s is reported as a FUNCTION of the acceptance length tau (tokens emitted
per step, 1 .. gamma+1): the reduced vehicle's seeded-random DSpark weights
accept nothing, and a shipped-model tau must come from a citation or a
measurement.  tokens/s at tau = f / (cycles_per_step / tau).  Batch 64: the
core time-shares its users (per-user rate / 64, aggregate = the batch-1 rate).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as I  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41_mtp_performance.json"
ENERGY = ROOT / "results/physical_abi3/asap7/signoff/energy_per_token.json"
ME_WORD_B, HE_WORD_B = 64 * 2, 24 * 4        # BF16 lanes per ME ROM word; FP32 HE word
QE_FP8_B, QE_FP4_B = 17 * 32, 9 * 32         # HBM sectors per QE word (the ROM reads the same words)
REPLICATED = ("matrix_engine (u_me)", "block-dot lanes (16)", "activation quantiser")   # scale with m


def weight_bytes(prog, entry=0, end=None):
    """Bytes of weights a program section reads: ME (weight ROM), QE LINQ, HE;
    a lane-multiplied op reads once.  Returns {me, qe, he}."""
    b = {"me": 0, "qe": 0, "he": 0}
    for f in prog[entry:end]:
        u = f["unit"]
        if u == I.UNIT_CTL and f.get("ctl", 0) == I.CTL_END:
            break
        if u == I.UNIT_ME and not f.get("me_wsrc", 0):
            b["me"] += f.get("me_tiles", 0) * f.get("me_k", 0) * I.INTERLEAVE * ME_WORD_B
        elif u == I.UNIT_QE and f.get("qe_mode", 0) == I.QE_LINQ:
            b["qe"] += f.get("qe_tiles", 0) * f.get("qe_nb", 0) * I.INTERLEAVE * (QE_FP4_B if f.get("qe_fp4") else
                                                                                  QE_FP8_B)
        elif u == I.UNIT_HE:
            b["he"] += f.get("he_k", 0) * I.INTERLEAVE * HE_WORD_B
    return b


def phys(d):
    j = json.loads((Path(d) / "physical.json").read_text())
    m = j["place_and_route"]["metrics"]
    return {"status": j["status"], "fmax_mhz": round(m["fmax_hz"] / 1e6, 1), "setup_wns_ns": m["setup_wns_ns"],
            "standard_cell_area_um2": m["standard_cell_area_um2"], "instance_count": m["instance_count"],
            "power_w": m["power_total_w"], "drc_errors": m["drc_errors"]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parts", type=Path, required=True)
    ap.add_argument("--phys", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=OUT)
    a = ap.parse_args()
    parts = {p.stem: json.loads(p.read_text()) for p in sorted(a.parts.glob("*.json"))}
    routes = {}
    for d in sorted(a.phys.iterdir()):
        if (d / "physical.json").exists():
            routes[d.name] = phys(d)
    # the core clock: the 0.9 ns target, lowered to the slowest routed block of each m
    period = 0.9
    fclk = {}
    for m in (1, 4):
        fs = [r["fmax_mhz"] for n, r in routes.items() if n.endswith(f"_m{m}") or n == "accept8"]
        fclk[m] = min([1000 / period] + fs) * 1e6
    en = json.loads(ENERGY.read_text())["architectures"]["deepseek_v41_rom_array_die"]
    terms = json.loads(ENERGY.read_text())["energy_terms"]
    logic_w = {k: v["TT"]["total_j"] / en["token_time_s"] for k, v in en["logic"].items()}
    sram_j_per_pos = en["memory"]["KV and vector memory SRAM"]["energy_j"]

    import hdc_golden_v41 as V
    import hdc_program_v41 as P
    model = V.Model()
    rows = []
    for tgt in ("rom", "hbm"):
        plain = parts.get(f"{tgt}_plain")
        if not plain:
            continue
        lay0 = P.Layout(model)
        prog0 = P.Builder(lay0, qchunk=P.QCHUNK if tgt == "hbm" else None).build()
        wb0 = weight_bytes(prog0)
        c0 = sum(r["rtl"]["cycles_per_token"] for r in plain["runs"]) / len(plain["runs"])
        rows.append(dict(target=tgt, mtp=False, m=1, gamma=0, cycles_per_token=c0, weight_bytes=wb0, runs=plain))
        for name, p in parts.items():
            if p.get("mode") == "plain" or p.get("target") != tgt:
                continue
            its = [x for r in p["runs"] for x in r["rtl"].get("per_iter", [])]
            if not its:
                continue
            lay = P.mtp_layout(model, p["gamma"])
            prog, entry = P.build_mtp(lay, p["gamma"], p["mp"], qchunk=P.QCHUNK if tgt == "hbm" else None)
            dyn = [n for n in range(entry, len(prog)) if prog[n]["unit"] == 0 and prog[n].get("ctl") == I.CTL_DYN][0]
            rows.append(dict(target=tgt, mtp=True, m=p["mp"], gamma=p["gamma"], part=name,
                             cycles_per_step=sum(x["cycles"] for x in its) / len(its),
                             draft_cycles=sum(x["draft_cycles"] for x in its) / len(its),
                             verify_cycles=sum(x["cycles"] - x["draft_cycles"] for x in its) / len(its),
                             weight_bytes_draft=weight_bytes(prog, entry, dyn),
                             weight_bytes_verify=weight_bytes(prog, dyn + 1),
                             reduced_vehicle_acceptance={r["drafter"]: r["isa"]["accepted"] for r in p["runs"]},
                             pass_=p["pass"]))

    def energy(row, tau):
        """J per emitted token at acceptance length tau."""
        m = row["m"]
        f = fclk[4 if m > 1 else 1]
        if row["mtp"]:
            t = row["cycles_per_step"] / f
            wb = {k: row["weight_bytes_draft"][k] + row["weight_bytes_verify"][k] for k in ("me", "qe", "he")}
            positions = row["gamma"] + 1
            ntok = tau
        else:
            t = row["cycles_per_token"] / f
            wb, positions, ntok = row["weight_bytes"], 1, 1
        logic = sum(w * (m if k in REPLICATED else 1) for k, w in logic_w.items()) * t
        rom_b = wb["me"] + wb["he"] + (wb["qe"] if row["target"] == "rom" else 0)
        hbm_b = wb["qe"] if row["target"] == "hbm" else 0
        mem = rom_b * terms["rom_read_j_per_byte"]["value"] + hbm_b * terms["hbm_j_per_byte"]["value"] + \
            positions * sram_j_per_pos
        return {"logic_j": logic / ntok, "weights_and_sram_j": mem / ntok, "total_j": (logic + mem) / ntok}

    table = []
    for r in rows:
        f = fclk[4 if r["m"] > 1 else 1]
        if r["mtp"]:
            taus = list(range(1, r["gamma"] + 2))
            per = {str(t): {"cycles_per_token": round(r["cycles_per_step"] / t, 1),
                            "tok_s_user_batch1": round(f * t / r["cycles_per_step"], 1),
                            "tok_s_user_batch64": round(f * t / r["cycles_per_step"] / 64, 2),
                            "aggregate_tok_s_batch64": round(f * t / r["cycles_per_step"], 1),
                            "energy_per_token_uj": round(energy(r, t)["total_j"] * 1e6, 2)} for t in taus}
            table.append({"target": r["target"], "mtp": True, "lane_multiplier_m": r["m"], "gamma": r["gamma"],
                          "clock_mhz": round(f / 1e6, 1), "cycles_per_verify_pass": round(r["verify_cycles"]),
                          "draft_cycles_per_step": round(r["draft_cycles"]),
                          "cycles_per_step": round(r["cycles_per_step"]),
                          "weight_bytes_per_step": {k: r["weight_bytes_draft"][k] + r["weight_bytes_verify"][k]
                                                    for k in ("me", "qe", "he")},
                          "by_acceptance_length_tau": per,
                          "breakeven_tau": None, "rtl_part": r["part"], "rtl_pass": r["pass_"],
                          "reduced_vehicle_acceptance_functional_check_only": r["reduced_vehicle_acceptance"]})
        else:
            e = energy(r, 1)
            table.append({"target": r["target"], "mtp": False, "lane_multiplier_m": 1, "clock_mhz": round(f / 1e6, 1),
                          "cycles_per_token": round(r["cycles_per_token"], 1),
                          "tok_s_user_batch1": round(f / r["cycles_per_token"], 1),
                          "tok_s_user_batch64": round(f / r["cycles_per_token"] / 64, 2),
                          "aggregate_tok_s_batch64": round(f / r["cycles_per_token"], 1),
                          "energy_per_token_uj": round(e["total_j"] * 1e6, 2),
                          "energy_split_uj": {k: round(v * 1e6, 2) for k, v in e.items()},
                          "weight_bytes_per_token": r["weight_bytes"], "rtl_pass": r["runs"]["pass"]})
    base = {t["target"]: t for t in table if not t["mtp"]}
    for t in table:
        if t["mtp"] and t["target"] in base:
            b = base[t["target"]]["cycles_per_token"]
            t["breakeven_tau"] = round(t["cycles_per_step"] / b, 3)       # tau at which MTP matches one-position decode
            t["speedup_over_one_position"] = {k: round(b / v["cycles_per_token"], 3)
                                              for k, v in t["by_acceptance_length_tau"].items()}
    ratio = {}
    if "rom" in base and "hbm" in base:
        ratio["without_mtp_rom_over_hbm_tok_s"] = round(base["rom"]["tok_s_user_batch1"] /
                                                        base["hbm"]["tok_s_user_batch1"], 3)
        for t in table:
            if t["mtp"] and t["target"] == "rom":
                h = [x for x in table if x["mtp"] and x["target"] == "hbm" and x["lane_multiplier_m"] ==
                     t["lane_multiplier_m"] and x["gamma"] == t["gamma"]]
                if h:
                    ratio[f"with_mtp_m{t['lane_multiplier_m']}_g{t['gamma']}_rom_over_hbm_tok_s"] = round(
                        h[0]["cycles_per_step"] and t["by_acceptance_length_tau"]["1"]["tok_s_user_batch1"] /
                        h[0]["by_acceptance_length_tau"]["1"]["tok_s_user_batch1"], 3)
    res = {"schema": "opentallas.hdc-v41-mtp-performance.v1",
           "claim_boundary": "cycles are RTL-measured (Verilator) on the reduced V4.1 vehicle; the clock is the "
                             "slowest routed MTP-changed block at 0.9 ns ASAP7 (not the whole core); energy is the "
                             "signoff record's measured logic power times step time plus per-byte weight/SRAM terms; "
                             "tok/s is a function of the acceptance length tau, which must come from a citation or a "
                             "shipped-model measurement (the reduced vehicle's DSpark weights are seeded random).",
           "routes": routes, "clock_hz_by_m": fclk, "table": table, "rom_over_hbm": ratio,
           "inputs": {"parts": sorted(parts), "energy_record": str(ENERGY.relative_to(ROOT))}}
    a.output.write_text(json.dumps(res, indent=1) + "\n")
    for t in table:
        print(json.dumps({k: t[k] for k in t if k not in ("by_acceptance_length_tau", "runs",
                                                            "reduced_vehicle_acceptance_functional_check_only")}))
    print(json.dumps(ratio))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
