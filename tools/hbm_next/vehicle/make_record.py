#!/usr/bin/env python3
"""TOKEN-PASS-HBMDS (10-18): results/rtl/hbm_ds_layer_tput_1018/record.json from priced_layers.json + coverage.json +
the stage-0 die vehicle run (stage0/times.json, run.log)."""
import json, sys
from pathlib import Path

D = Path(sys.argv[1] if len(sys.argv) > 1 else "results/rtl/hbm_ds_layer_tput_1018")
P = json.loads((D / "priced_layers.json").read_text())
C = json.loads((D / "coverage.json").read_text())
S0 = {}
if (D / "stage0/times.json").exists():
    S0 = json.loads((D / "stage0/times.json").read_text())
    S0["run_tail"] = (D / "stage0/run.log").read_text().splitlines()[-4:] if (D / "stage0/run.log").exists() else []
REP = {"0": "L0", "2": "L2 CSA+indexer", "14": "L14 Engram", "3": "MoE FFN layer (L3)", "head": "LM head"}
layers = {}
for k, nm in REP.items():
    c = C["layers"][k]
    layers[nm] = dict(segment=k, priced_cycles=P["segments"][k]["cycles"], records=c["records"],
                      grades=c["grade_records"], measured_cycles=None, bit_exact=None, schedule_assertions=None,
                      runnable_fraction=c["runnable_fraction_of_layer"],
                      blocking_datapath_gaps=c["datapath_gap_span_cycles"],
                      verdict="NOT RUN: no record of this layer can execute natively on the d4g GEN2 die RTL "
                              "(blocking datapath gaps above; every record also lacks a d4g programme compiler)")
rec = dict(
    schema="opentallas.hbm_ds_layer_tput.v1", lane="TOKEN-PASS-HBMDS", date="2026-10-18",
    grade="PILOT (not-final RTL; GEN2 smoke netlist, landing step NOT in the die: chain LANDING_NOT_USED)",
    rtl=dict(die_branch="claude/hd4g-gen2-1018", die_rev="7c124deae", landing_branch="claude/hland-1018 ea280c58d (not merged "
             "into the GEN2 netlist used here)", netlist="GEN2 full_smoke pb/die.v (contract_die_v.py; 1,198 inst, 97 masters, "
             "12,351 edges, 32 gaps)", contract_summary=C["contract_summary"]),
    priced=dict(variant=P["variant"], ar_cycles=P["ar_cycles"], ar_tok_s=P["ar_tok_s"],
                per_segment_cycles={k: P["per_segment"][k] for k in ("0", "1", "2", "3", "14", "head") if k in P["per_segment"]}),
    layers=layers,
    vehicle=dict(stage0=dict(what="whole die top hbm_v16_die under Verilator 5.050, off-chip models only, reset + idle clocking",
                             build_attempts_1018=[
                                 "flat (one namespace): MODDUP/param clashes -> per-master namespaces + per-master DEFINES "
                                 "(views.json env) + same-name variant uniquify (die_filelist/flatten_masters)",
                                 "flat, per-master namespaces: parse+link+width PASS (0 errors); elaboration OOM at 96 GB "
                                 "(ot-epyc4, 3 min) and at 380 GB (ot-epyc5, 13 min) -> a flat whole-die Verilator model is "
                                 "not tractable",
                                 "--hierarchical (one hier_block per master parametrisation): ~120 blocks verilate at "
                                 "0.3-14 GB / 2-220 s each; NBA guard needed --unroll-count 16384; OOM at 200 GB (j32) and "
                                 "300 GB (j12) -> relaunched j6 / 300 GB (pending)"],
                             **S0),
                 interface="lanes/TOKEN-PASS-HBMDS.md + tools/hbm_next/vehicle/"),
    behavioural=["HBM PHY ot_hbm3e_phy_rc_e8p5: (* blackbox *) abstract, no DRAM model yet (allowed: PHY/off-chip)",
                 "PLL ot_hbm_pll_bb: behavioural model from tb_hfd_ckgen.sv (allowed: analog macro)",
                 "SerDes/UCIe PMA far ends: quiet test drivers (allowed: off-chip)",
                 "no on-chip behavioural substitute is used; every on-chip gap stays OPEN (undriven) -> layer NOT RUN"],
    missing_for_a_native_layer=dict(
        compiler="no d4g layer compiler: nothing lowers the DS layer records (hgi_sim / ds_native) into SU programme, SFU store, "
                 "VM calendar, COLLQ slot, IDX calendar, HC and host command images for the d4g static masters",
        datapath_gaps={g: C["gaps"][g] for g in sorted({g for v in C["layers"].values() for g in v["datapath_gap_span_cycles"]})},
        loader_gaps=sorted({g for v in C["layers"].values() for r in v["rows"] for g in r["open_gaps"]}
                           - {g for v in C["layers"].values() for g in v["datapath_gap_span_cycles"]})),
    token_compose=dict(terms=[], note="no measured layer term yet: every DS representative layer is NOT RUN on d4g GEN2 RTL "
                       "(coverage.json); the composition keeps the priced terms"),
    wall_time_cost=dict(priced_layers_s=270, flat_die_elab="OOM > 380 GB", hier_block_verilate="0.3-14 GB, 2-220 s per "
                        "master parametrisation (~120+ blocks)", layer_run="n/a (no layer runs)"),
    mutants="none: no layer runs, so no layer mutant can be witnessed (stage-0 has no layer semantics)",
)
(D / "record.json").write_text(json.dumps(rec, indent=1) + "\n")
print(json.dumps({k: (v["priced_cycles"], v["grades"]) for k, v in layers.items()}, indent=0))
