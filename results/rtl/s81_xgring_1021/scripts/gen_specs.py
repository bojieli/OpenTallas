#!/usr/bin/env python3
"""S81-ELEM2-XGRING (10-21): kit specs s81sl_xgr (MAIN, top ot_s81sl_xgr2, xg5fa map 734.4 x 777.6 with the 4 stream ROMs
grouped) and s81sl_xgr_b (FALLBACK, top ot_s81sl_xgr, xg5fb map 648 x 864) from the xgt_xo kits of f5f35855d.
usage: gen_specs.py   (cwd = repo root), then tools/ref_tile/ref_tile.py gen physical/ref_tile/<kit>/spec.json"""
import json
from pathlib import Path

W = "results/rtl/s81_xgring_1021/bench"
SL = "rtl/dsrom_sys/s81_dv/slice"
SRAM = "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2"
ROM = "physical/asap7_memory_macros_v2/ot_rom_4096x72_m8"
EXP = "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1"


def benches(top):
    out = []
    env = "env XGR_TOP=ot_s81sl_xgr2 " if top == "ot_s81sl_xgr2" else ""
    xb = "xgr2_main" if top == "ot_s81sl_xgr2" else "xgr_fb"

    def b(name, cmd, expect, wit, rx, ram=16, thr=8):
        d = dict(name=name, cmd=cmd, expect=expect, threads=thr, peak_ram_gb=ram, needs=["verilator"])
        if expect == "pass":
            d.update(pass_regex=rx, pass_witness=wit)
        else:
            d.update(fail_regex=rx, fail_witness=wit)
        out.append(d)
    # combined lockstep at the xg ring pins (production PQ slot, x path main xg + 3 edges); mutants are verdict lines
    b(f"{xb}_bench", f"{env}bash tools/s81_slice/xgr_bench.sh {{RUN}}/{xb}", "pass", f"{W}/{xb}_bench.log",
      f"^XGR_BENCH PASS top={top}$", 32)
    for m in ("muttiercol", "mutbank", "mutoff", "mutwcopy", "mutexp"):
        b(f"{xb}_{m}", f"{env}bash tools/s81_slice/xgr_bench.sh {{RUN}}/{xb}_{m} L0_{m}", "fail", f"{W}/{xb}_bench.log",
          f"^XG_CASE L0_{m} FAIL expected=FAIL ok=1", 32)
    # head egress + slice-id rules on the face-staged ring stop (RG-HEAD benches, tb unchanged, master swapped)
    b("rstopr", "bash tools/s81_slice/rstopr_bench.sh {RUN}/rstopr none", "pass", f"{W}/rstopr_none.log",
      "^BENCH_PASS rstopr", 8, 4)
    for m in ("xooff", "xoall", "xonoflag", "tiercol"):
        b(f"rstopr_mut{m}", f"bash tools/s81_slice/rstopr_bench.sh {{RUN}}/rstopr {m}", "fail", f"{W}/rstopr_{m}.log",
          f"^NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT={m}$", 8, 4)
    # x streamer equivalence (main xs + 2 edges) + the 6 mutants
    b("xs5_equiv", "bash tools/s81_slice/xs5_equiv.sh {RUN}/xs5_equiv", "pass", f"{W}/xs5_equiv_base.log", "^XS5_EQUIV_BENCH PASS$")
    for m in ("bank", "off", "qswap", "wcopy", "tpar", "exp"):
        b(f"xs5_equiv_mut{m}", f"bash tools/s81_slice/xs5_equiv.sh {{RUN}}/xs5_equiv_{m} {m}", "fail", f"{W}/xs5_equiv_{m}.log",
          "^XS4_CASE L0_near_s5 FAIL expected=FAIL ok=1")
    return out


PIN_REGS = {"enable": False, "reason": (
    "Source-registered leaf with explicit RTL face stages: every input pin lands in exactly one face flop (rstopr p_* stage, "
    "xgr is_vq / is_dq) and every output leaves a flop (MAIN xgr2 q_* output stage / FB rstopr ro_* / vo / dl_* / nx_*; "
    "xs5 xw_q; fault); io_flop_at_pins puts them at the pins.  The relay stages behind / before them are RTL edges priced in "
    "MU.S81.CAL (README); a recipe pin_regs stage would add a further unpriced edge.")}

STRUCT = {
 "ot_s81sl_xgr2": (
    "S81-ELEM2-XGRING (10-21): MAIN successor of s81sl_xgtxo (gate f5f35855d ep9 3256858: TT -765 ps, 6,805 failing reg "
    "endpoints = one-cycle 17-26-level hops over 800-1,370 um; clock pin-flop 95/89 > 80).  Master ot_s81sl_xgr2 (same ports "
    "as xgt_xo) = ot_s81sl_xgr + output relay stage: ring stop ot_s81sl_rstopr (face flop on every input, old input flops "
    "= mid-tile relays, kept selects decoded from face flops), is face stage, ot_s81sl_xs5 (per-bank registered read "
    "partials + S/N gather write copies), output stage on ro/vo/nx/dl.  Cycles vs xgt_xo: ring +2 per stop (line, V, NX, "
    "dl, egress), x path +2, fault +2 (MU.S81.CAL).  Floorplan: xg5fa map with the 4 stream ROMs grouped in the S ROM "
    "columns (stream ROM -> r1_w mux span ~170 um; was S/N split, u_stream0 -> r1_w -242 ps @ 576 um), cal/phase ROMs N.  "
    "Clock km split K 16 -> 24."),
 "ot_s81sl_xgr": (
    "S81-ELEM2-XGRING (10-21): FALLBACK successor of s81sl_xgtxo_b (gate f5f35855d ep9 3256860: TT -429 ps, clock "
    "84/86 > 80).  Master ot_s81sl_xgr (same ports as xgt_xo) = ring stop ot_s81sl_rstopr (face flop on every input, old "
    "input flops = mid-tile relays, kept selects decoded from face flops) + is face stage + ot_s81sl_xs5 (per-bank "
    "registered read partials + S/N gather write copies).  Cycles vs xgt_xo: ring +1 per stop, x path +2, fault +2 "
    "(MU.S81.CAL).  Floorplan: xg5fb map unchanged (648 x 864, stream ROMs already grouped N).  Clock km split K 16 -> 32."),
}


def make(base, name, tag, top, purpose, kk, roms=None):
    s = json.loads(Path(base).read_text())
    s["name"] = name
    s["top"] = top
    s["sources"] = ["rtl/lib/ot_rst_relay.sv", "rtl/v41rom/ot_v41_kreg.sv", "rtl/common/ot_prefix.sv",
                    f"{SL}/ot_s81sl_rstopr.sv", f"{SL}/ot_s81sl_xs4.sv", f"{SL}/ot_s81sl_xs5.sv", f"{SL}/ot_s81sl_xgr.sv",
                    f"{SRAM}/ot_sram_1r1w_128x256_m1_r2c2_bb.v", f"{ROM}/ot_rom_4096x72_m8_bb.v",
                    f"{EXP}/ot_sram_1r1w2c_128x64_m1_bb.v"]
    s["pin_regs"] = PIN_REGS
    km = s["route"].setdefault("synth_keep_modules", [])
    if "ot_s81sl_xs5_ln" not in km:
        km.append("ot_s81sl_xs5_ln")
    s.setdefault("orfs_vars", {})["OT_CKKM_K"] = str(kk)
    if roms:
        for m in s["macros"]:
            for inst, at in roms.items():
                if m["inst"] == f"*u_s.{inst}":
                    m["at"] = list(at)
        got = {m["inst"]: m["at"] for m in s["macros"] if "ot_rom" in m["view"]}
        assert all(got[f"*u_s.{i}"] == list(a) for i, a in roms.items()), got
    s["std_area_um2"] = 38000.0
    s["structural_change"] = STRUCT[top] + "\n\nBase (" + Path(base).parent.name + "):\n" + s.get("structural_change", "")
    j = s["job"]
    j["benches"] = benches(top)
    j["extra_paths"] = [p if p != "results/rtl/s81_xgtxo_1021" else "results/rtl/s81_xgring_1021" for p in j["extra_paths"]]
    j.update(owner="Claude:S81-ELEM2-XGRING", branch="claude/s81-xgring-1021", tag=tag, purpose=purpose,
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}")
    d = Path(f"physical/ref_tile/{name}")
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print("wrote", d / "spec.json")


# MAIN: 4 stream ROMs grouped in the S halves of both ROM columns; phase / calendar ROMs in the N halves
MAIN_ROMS = {"u_stream0": (367.2, 86.4), "u_stream1": (367.2, 149.376), "u_stream2": (475.2, 86.4),
             "u_stream3": (475.2, 149.376), "u_phase0": (367.2, 524.88), "u_cal_action": (367.2, 587.856),
             "u_cal_time": (475.2, 524.88)}
make("physical/ref_tile/s81sl_xgtxo/spec.json", "s81sl_xgr", "xgr", "ot_s81sl_xgr2",
     "S81 end-slice u_xg master ot_s81sl_xgr2 (ring stop face+relay+output stages, xs5 registered bank read partials), MAIN: xg5fa map 734.4 x 777.6, stream ROMs grouped, K24.",
     24, MAIN_ROMS)
make("physical/ref_tile/s81sl_xgtxo_b/spec.json", "s81sl_xgr_b", "xgr_b", "ot_s81sl_xgr",
     "S81 end-slice u_xg master ot_s81sl_xgr (ring stop face+relay stages, xs5 registered bank read partials), FALLBACK: xg5fb map 648 x 864, K32.",
     32)
