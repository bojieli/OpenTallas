#!/usr/bin/env python3
"""S81-FIX2/XG (10-21): kit specs s81sl_xgtxo (MAIN, xg5fa outline/macro map 734.4 x 777.6) and s81sl_xgtxo_b (FALLBACK,
xg5fb map 648 x 864) for ot_s81sl_xgt_xo = ot_s81sl_rstopt_xo + ot_s81sl_xs4.  Base specs: claude/s81-xg5fp-1021
ab6b3f7b4 physical/ref_tile/s81sl_xg5f{a,b}/spec.json (same macro instance paths u_s.g_bank/g_mac/g_ex, same pins).
usage: gen_specs.py <xg5fa spec.json> <xg5fb spec.json>   (cwd = repo root), then tools/ref_tile/ref_tile.py gen <kit>/spec.json"""
import copy, json, sys
from pathlib import Path

W = "results/rtl/s81_xgtxo_1021/bench"
SL = "rtl/dsrom_sys/s81_dv/slice"
SRAM = "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2"
ROM = "physical/asap7_memory_macros_v2/ot_rom_4096x72_m8"
EXP = "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1"


def benches():
    out = []

    def b(name, cmd, expect, wit, rx, ram=16, thr=8):
        d = dict(name=name, cmd=cmd, expect=expect, threads=thr, peak_ram_gb=ram, needs=["verilator"])
        if expect == "pass":
            d.update(pass_regex=rx, pass_witness=wit)
        else:
            d.update(fail_regex=rx, fail_witness=wit)
        out.append(d)
    # combined lockstep (production PQ slot at the xg ring pins, x path +1); mutants inside are verdict lines
    b("xgtxo_bench", "bash tools/s81_slice/xgtxo_bench.sh {RUN}/xgtxo", "pass", f"{W}/xgtxo_bench.log", "^XGTXO_BENCH PASS", 32)
    for m in ("muttiercol", "mutbank", "mutoff", "mutwcopy", "mutexp"):
        b(f"xgtxo_{m}", f"bash tools/s81_slice/xgtxo_bench.sh {{RUN}}/xgtxo_{m} L0_{m}", "fail", f"{W}/xgtxo_bench.log",
          f"^XG_CASE L0_{m} FAIL expected=FAIL ok=1", 32)
    # head egress + slice-id rules on the safe ring stop (RG-HEAD bench, tb unchanged, master swapped)
    b("rstopt_xo", "bash tools/s81_slice/rstopt_xo_bench.sh {RUN}/rstopt_xo none", "pass", f"{W}/rstopt_xo_none.log",
      "^BENCH_PASS rstopt_xo", 8, 4)
    for m in ("xooff", "xoall", "xonoflag"):
        b(f"rstopt_xo_mut{m}", f"bash tools/s81_slice/rstopt_xo_bench.sh {{RUN}}/rstopt_xo {m}", "fail", f"{W}/rstopt_xo_{m}.log",
          f"^NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT={m}$", 8, 4)
    b("rstopt_xo_muttiercol", "bash tools/s81_slice/rstopt_xo_bench.sh {RUN}/rstopt_xo tiercol", "fail",
      f"{W}/rstopt_xo_tiercol.log", "^NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT=tiercol$", 8, 4)
    # x streamer equivalence (main xs + 1 edge) + its 6 mutants, re-run on this branch
    b("xs4_equiv", "bash tools/s81_slice/xs4_equiv.sh {RUN}/xs4_equiv", "pass", f"{W}/xs4_equiv_base.log", "^XS4_EQUIV_BENCH PASS$")
    for m in ("bank", "off", "qswap", "wcopy", "tpar", "exp"):
        b(f"xs4_equiv_mut{m}", f"bash tools/s81_slice/xs4_equiv.sh {{RUN}}/xs4_equiv_{m} {m}", "fail", f"{W}/xs4_equiv_{m}.log",
          "^XS4_CASE L0_near_s5 FAIL expected=FAIL ok=1")
    return out


PIN_REGS = {"enable": False, "reason": (
    "Source-registered leaf: every rstopt_xo input lands in an input flop (iw / ie / iv / xf_q / neo_q / nwo_q / ci_q / "
    "sid_c; pin-decided selects are decoded at the pin and registered as kept copies on the same edge) and every ring "
    "output leaves a flop (ro_* / vo / dl_* / nx_*); is_v / is_d land in the xs4 K=1 capture flops; xw_v / xw_d / fault "
    "leave flops.  A recipe pin_regs stage would add an unpriced ring-hop edge (~8 cycles per traversal).")}

STRUCT = (
    "S81-FIX2/XG (10-21): ONE combined end-slice u_xg master ot_s81sl_xgt_xo (same ports as ot_s81sl_xg / xg_xo / xgt) = "
    "ot_s81sl_rstopt_xo (RG-FFN rstopt: kept one-hot DKS selects, ot_rst_relay leaves on control/valid only, datapath "
    "unreset; + RG-HEAD head XB egress at s_0N -> ro_w as kept selects) + ot_s81sl_xs4 (xg5 lineage native-bounded x streamer, "
    "ab6b3f7b4 incl. XG5d rng/bad fix).  Replaces the failed s81sl_xgxo/_b gates (main ot_s81sl_xs ctl net 4,050 loads, "
    "rstop rst_n 2,517 loads vs census 32).  Cycle delta vs ot_s81sl_xg_xo: ring +0 (ro/vo/nx/dl/egress), slice x path "
    "+1 (xs4 capture, uniform for issuer and gather), fault +1.  Floorplan = the xg5 structural successor map "
    "(split macro stacks, full-width macro-free centre band) because xs4 has the same 37 macros / instance paths.  "
    "Census fixes in xs4 (xgt_xo mapped census max 72): BF arrival-line one-hot from 2 kept ot_s81sl_xs4_bdec predecode "
    "instances per group (was a shared AND3 decode, 72 loads x 4 groups); kept act_g copy of each calendar due act for the "
    "24-b age update (act mapped 39).  Value-preserving, 0 cycles.")


def make(base, name, tag, purpose):
    s = json.loads(Path(base).read_text())
    s["name"] = name
    s["top"] = "ot_s81sl_xgt_xo"
    s["sources"] = ["rtl/lib/ot_rst_relay.sv", "rtl/v41rom/ot_v41_kreg.sv", "rtl/common/ot_prefix.sv",
                    f"{SL}/ot_s81sl_rstopt_xo.sv", f"{SL}/ot_s81sl_xs4.sv", f"{SL}/ot_s81sl_xgt_xo.sv",
                    f"{SRAM}/ot_sram_1r1w_128x256_m1_r2c2_bb.v", f"{ROM}/ot_rom_4096x72_m8_bb.v",
                    f"{EXP}/ot_sram_1r1w2c_128x64_m1_bb.v"]
    s["pin_regs"] = PIN_REGS
    km = s["route"].setdefault("synth_keep_modules", [])
    if "ot_s81sl_xs4_bdec" not in km:
        km.append("ot_s81sl_xs4_bdec")
    s["structural_change"] = STRUCT + "\n\nBase floorplan (" + Path(base).parent.name + "):\n" + s.get("structural_change", "")
    j = s["job"]
    j["benches"] = benches()
    j["extra_paths"] = ["rtl/dsrom_sys", "rtl/lib", "rtl/v41rom", "rtl/common", "tools/s81_slice", "tools/s81_static_control",
                        "tools/s81/pq_static_calendar_abi.json", "physical/s81_pq_hier/pinned", SRAM, ROM, EXP,
                        "results/rtl/dsrom_recovery_20261004/immutable_fullcatalog/stage0",
                        "results/rtl/dsrom_recovery_20261004/immutable_fullcatalog/stage3", "results/rtl/s81_xgtxo_1021"]
    j.update(owner="Claude:S81-FIX2", branch="claude/s81-xgtxo-1021", tag=tag, purpose=purpose,
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}")
    d = Path(f"physical/ref_tile/{name}")
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print("wrote", d / "spec.json")


make(sys.argv[1], "s81sl_xgtxo", "xgtxo",
     "S81 end-slice u_xg combined master ot_s81sl_xgt_xo (head egress + safe rstopt + native xs4), MAIN: xg5fa map 734.4 x 777.6.")
make(sys.argv[2], "s81sl_xgtxo_b", "xgtxo_b",
     "S81 end-slice u_xg combined master ot_s81sl_xgt_xo (head egress + safe rstopt + native xs4), FALLBACK: xg5fb map 648 x 864.")
