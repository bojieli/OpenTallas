#!/usr/bin/env python3
"""Gate-level power of the power-gated S81 ROM element (ROM stage power gating, 2026-10-04).

Three measured states of one element domain (ot_v41_rom_elem_q_pg_w10, PG = 1, routed in the q-frame C):
  ACTIVE   one token's work (bench window go_A .. end_A)
  PG_IDLE  domain switched off between tokens (pg_en = 1): what is left is the always-on side's power plus the
           header switches' off-state leakage
  CG_IDLE  pg_en = 0: domain powered, element idle behind its own clock gate (today's baseline)

Activity: Icarus gate-level simulation of the routed netlist inside rtl/test/tb_signoff_rom_elem_pg.sv (the RTL
element paces the x beats and checks every output cycle by cycle), one VCD streamed through tools/signoff/vcd2saif
into one SAIF per window.  Power: OpenSTA report_power at the routed SPEF, TT, through
tools/signoff_analysis.analyze().  The always-on side is routed alone (ot_v41_rom_pg_ao, launch_ao.sh) for its
leakage, so domain leakage = element-route leakage - AO-route leakage.

    python3 tools/rom_stage_pg_power.py activity --routed <R1 workdir> --work <dir>
    python3 tools/rom_stage_pg_power.py power --routed <R1 workdir> --ao-routed <A1 workdir> --work <dir> --out <json>
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import signoff_analysis as so  # noqa: E402

BENCH = ROOT / "rtl/test/tb_signoff_rom_elem_pg.sv"
BENCH_TOP = "tb_signoff_rom_elem_pg"
DUT = "ot_v41_rom_elem_q_pg_w10"
RTL = ["rtl/v41rom/ot_v41_rom_elem_q_w10.sv", "rtl/v41rom/ot_v41_rom_elem_w10.sv", "rtl/v41rom/ot_v41_bterm.sv",
       "rtl/v41rom/ot_v41_chain.sv", "rtl/v41rom/ot_v41_segtree.sv", "rtl/v41rom/ot_v41_bf16_lanes.sv",
       "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_cg.sv",
       "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/v41rom/ot_v41_fadd.sv", "rtl/common/ot_prefix.sv",
       "rtl/v41rom/ot_v41_bmul2.sv", "rtl/v41rom/ot_v41_bterm2_w10.sv", "rtl/v41rom/ot_v41_chain2.sv",
       "rtl/v41rom/ot_v41_segtree2.sv", "rtl/v41rom/ot_v41_bf16_lanes2.sv"]
LIBERTY = [Path.home() / f".local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_{n}_RVT_TT_{d}.lib" for n, d in
           (("AO", "nldm_211120"), ("INVBUF", "nldm_220122"), ("OA", "nldm_211120"), ("SEQ", "nldm_220123"),
            ("SIMPLE", "nldm_211120"))]
HALF_PS = 417                       # 0.834 ns cycle, the q-element's 0.833 ns SS clock
# windows in bench cycles (one count per falling edge from time 0), from the bench's MARK lines (RTL run, identical
# timeline at gate level; the gate-level run re-checks them)
WINDOWS = dict(active=(3000, 3855), pg_idle=(4255, 16255), cg_idle=(20256, 32256))


def build(work: Path, netlist: Path) -> tuple[Path, dict]:
    work.mkdir(parents=True, exist_ok=True)
    text, removed = so.gate_level_bench(BENCH.read_text(), DUT)
    gl_bench = work / "bench_gl.sv"
    gl_bench.write_text(text)
    gl = work / f"{DUT}_gl.v"
    so.netlist_accepting_params(netlist, gl, so.rtl_param_overrides([BENCH], DUT))
    cells = work / "cells.v"
    cm = so.write_cell_models(LIBERTY, cells, so.netlist_cell_types(gl) | {"ICGx1_ASAP7_75t_R"})
    top = work / "so_icarus_top.sv"
    top.write_text((ROOT / "tools/signoff/icarus_top.sv.in").read_text().replace("@BENCH@", BENCH_TOP)
                   .replace("@HALF_PS@", str(HALF_PS)).replace("@SCOPES@", "bench.dut"))
    exe = work / "sim.vvp"
    # -DSYNTHESIS: the RTL pacing element instantiates its macros without the simulation-only INSTANCE strings and
    # its clock gates as the platform ICG cell (modelled from the Liberty like the netlist's)
    cmd = ["iverilog", "-g2012", "-DSYNTHESIS", "-o", str(exe), "-s", "so_icarus_top", str(top), str(gl_bench),
           str(gl), str(cells), *[str(ROOT / f) for f in RTL]]
    t0 = time.time()
    b = subprocess.run(cmd, capture_output=True, text=True)
    (work / "build.log").write_text(b.stdout[-200000:] + b.stderr[-200000:])
    if b.returncode:
        raise RuntimeError(f"iverilog failed: {work / 'build.log'}")
    return exe, dict(netlist=str(netlist), netlist_sha256=so.sha256_file(netlist), bench_removed=removed,
                     cell_models=cm, build_s=round(time.time() - t0, 1))


def activity(a) -> int:
    work = a.work.resolve()
    netlist = so.find_results_dir(a.routed) / "6_final.v"
    exe, meta = build(work, netlist)
    conv = so.build_vcd2saif(work)
    fifo = work / "trace.fifo"
    tees = []
    for p in [fifo] + [work / f"t_{n}.fifo" for n in WINDOWS]:
        p.unlink(missing_ok=True)
        os.mkfifo(p)
    readers = {}
    for n, (b, e) in WINDOWS.items():
        f = work / f"t_{n}.fifo"
        tees.append(f)
        readers[n] = subprocess.Popen([str(conv), str(f), str(work / f"{n}.nets.saif"), "so_icarus_top.bench.dut",
                                       str(b * 2 * HALF_PS), str(e * 2 * HALF_PS)], stderr=subprocess.PIPE, text=True)
    # each converter stops reading at its window's end: tee must keep feeding the others (--output-error=
    # warn-nopipe), or the first window's end SIGPIPEs the whole chain and the simulator with it
    tee = subprocess.Popen(f"cat {fifo} | tee --output-error=warn-nopipe /dev/null {' '.join(str(f) for f in tees[1:])} "
                           f"> {tees[0]}", shell=True)
    t0 = time.time()
    sim = subprocess.run(["vvp", "-n", str(exe), f"+VCD={fifo}"], capture_output=True, text=True, cwd=work)
    meta["sim_returncode"] = sim.returncode
    try:
        os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
    except OSError:
        pass
    tee.wait()
    meta["sim_s"] = round(time.time() - t0, 1)
    out = sim.stdout + sim.stderr
    (work / "sim.log").write_text(out)
    meta["marks"] = [ln for ln in out.splitlines() if ln.startswith(("MARK", "PASS", "FATAL"))]
    meta["pass"] = any(ln.startswith("PASS") for ln in out.splitlines()) and "FATAL" not in out
    meta["windows_cycles"] = WINDOWS
    meta["saif"] = {}
    for n, p in readers.items():
        _, err = p.communicate()
        pins = work / f"{n}.saif"
        exp = so.expand_saif_to_pins(work / f"{n}.nets.saif", work / f"{DUT}_gl.v", pins, top="dut")
        meta["saif"][n] = dict(path=str(pins), converter=err.strip()[-300:], expansion=exp)
    for p in [fifo, *tees]:
        p.unlink(missing_ok=True)
    (work / "activity.json").write_text(json.dumps(meta, indent=1, default=str))
    print(json.dumps({k: meta[k] for k in ("marks", "pass", "sim_s")}, indent=1))
    return 0 if meta["pass"] else 1


def power(a) -> int:
    work = a.work.resolve()
    act = json.loads((work / "activity.json").read_text())
    res = dict(schema="opentallas.rtl.rom_stage_pg_power.v1", activity={k: v for k, v in act.items() if k != "saif"},
               states={})
    for n in WINDOWS:
        r = so.analyze(Path(a.routed), work / f"an_{n}", label=f"rom_elem_pg_{n}", record=None,
                       saif=Path(act["saif"][n]["path"]), saif_scope="dut", groups=[], corners=["TT"], derate=0.0,
                       ir_sources=[], bump_pitch_um=140.0, cycles_per_token=None, activity_meta=None,
                       tt_stages=["power"])
        c = r["corners"]["TT"]
        res["states"][n] = dict(power_w=c["power_w"], annotation=c["activity_annotation"], routed=r["routed"])
    r = so.analyze(Path(a.ao_routed), work / "an_ao", label="rom_pg_ao_vectorless", record=None, saif=None,
                   saif_scope="", groups=[], corners=["TT"], derate=0.0, ir_sources=[], bump_pitch_um=140.0,
                   cycles_per_token=None, activity_meta=None, tt_stages=["power"])
    res["ao_route"] = dict(power_w=r["corners"]["TT"]["power_w"], routed=r["routed"],
                           note="vectorless (leakage is activity-independent; dynamic not used)")
    a.out.write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(json.dumps({n: s["power_w"]["total"] for n, s in res["states"].items()} |
                     {"ao_leak": res["ao_route"]["power_w"]["total"]["leakage"]}, indent=1))
    return 0


CLASSES = (("domain", ("u_pg.u_elem.", "u_pg.e_clk", "u_pg.u_elem")),
           ("ao_sched_ctrl", ("u_pg.g_pg.u_ao.u_sched.",)),
           ("ao_element", ("u_pg.g_pg.u_ao.",)))


def classify(name: str) -> str:
    """Instance class in the flat routed netlist: by RTL path for named cells (flops, ICGs, CTS buffers carry
    their clock net's name), else root clock tree (buffers of the port clock) or unnamed logic."""
    for cls, keys in CLASSES:
        if any(k in name for k in keys):
            return cls
    if name.startswith(("clkbuf", "delaybuf", "clkload")) and ("_clk" in name):
        return "root_clock"
    return "unnamed"


def inst(a) -> int:
    """Per-instance TT power of each state, totalled by class (so_inst_power of tools/signoff_analysis)."""
    work = a.work.resolve()
    act = json.loads((work / "activity.json").read_text())
    orig = so.session_script
    out = {}
    for n in WINDOWS:
        so.session_script = lambda *x, **k: orig(*x, **dict(k, inst_power="/so_out/inst.txt"))
        try:
            so.analyze(Path(a.routed), work / f"inst_{n}", label=f"inst_{n}", record=None,
                       saif=Path(act["saif"][n]["path"]), saif_scope="dut", groups=[], corners=["TT"], derate=0.0,
                       ir_sources=[], bump_pitch_um=140.0, cycles_per_token=None, activity_meta=None,
                       tt_stages=["power"])
        finally:
            so.session_script = orig
        tot: dict[str, list] = {}
        for ln in (work / f"inst_{n}" / "inst.txt").read_text().splitlines():
            name, w = ln.rsplit(" ", 1)
            c = tot.setdefault(classify(name), [0.0, 0])
            c[0] += float(w)
            c[1] += 1
        out[n] = {k: dict(total_w=v[0], instances=v[1]) for k, v in sorted(tot.items())}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("activity")
    p.add_argument("--routed", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    q = sub.add_parser("power")
    q.add_argument("--routed", type=Path, required=True)
    q.add_argument("--ao-routed", type=Path, required=True)
    q.add_argument("--work", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True)
    i = sub.add_parser("inst")
    i.add_argument("--routed", type=Path, required=True)
    i.add_argument("--work", type=Path, required=True)
    i.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    return dict(activity=activity, power=power, inst=inst)[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
