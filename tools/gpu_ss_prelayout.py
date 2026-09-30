#!/usr/bin/env python3
"""Pre-layout SS-corner timing of an RTL block (ORFS synthesis at CORNER=WC, OpenSTA with the SS RVT libs).

    python3 tools/gpu_ss_prelayout.py --top ot_fp32_add_rne_pipe --source rtl/proto/ot_fp32_add_rne_pipe.sv \
        --period-ps 833 --work /tmp/.../ss_fadd [--param K=V ...]

Reports the worst register-to-register setup slack at SS (60 ps uncertainty, ideal clock, no wires) and the
worst path's start/end: the stage that must be split to close 1.2 GHz at SS (AGENTS.md sign-off corners).
Pre-layout is optimistic (no wire, no placement), so a stage needs margin here.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chip_assembly import case as cs, harden as H, orfs  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", required=True)
    ap.add_argument("--source", action="append", required=True)
    ap.add_argument("--param", action="append", default=[])
    ap.add_argument("--period-ps", type=float, default=833.0)
    ap.add_argument("--work", required=True, type=Path)
    a = ap.parse_args(argv)
    params = dict(p.split("=", 1) for p in a.param)
    work = a.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    sdc = f"create_clock -name clk -period {a.period_ps:g} [get_ports clk]\nset_false_path -from [all_inputs]\nset_false_path -to [all_outputs]\n"
    spec = cs.CaseSpec(nickname=f"ss_{a.top}", top=a.top, sources=a.source, die_um=(400.0, 400.0), sdc=sdc,
                       params=params, extra={"CORNER": "WC", "ABC_AREA": 0, "ADDER_MAP_FILE": ""})
    cs.write_case(work, spec)
    net = orfs.results_dir(work, spec.nickname) / "1_2_yosys.v"
    if not net.is_file():
        p = orfs.docker_make(work, f"/work/results/asap7/{spec.nickname}/base/1_2_yosys.v", "synth.log", 7200)
        if p.returncode != 0:
            sys.exit(f"synthesis failed: {work}/synth.log")
    orfs.normalise_netlist(net)
    libdir = "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM"
    tcl = "\n".join([f"read_liberty {libdir}/{f}" for f in H.CORNER_LIBS["SS"]] + [
        "read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef",
        "read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef",
        f"read_verilog /work/results/asap7/{spec.nickname}/base/1_2_yosys.v", f"link_design {a.top}",
        f"create_clock -name clk -period {a.period_ps:g} [get_ports clk]", "set_clock_uncertainty 60 [all_clocks]",
        "set_false_path -from [all_inputs]", "set_false_path -to [all_outputs]",
        'puts "OTC wns [sta::worst_slack_cmd max]"',
        "report_checks -path_delay max -group_path_count 100000 -endpoint_path_count 1 -unique_paths_to_endpoint -format end > /work/ss_ends.rpt",
        "report_checks -path_delay max -digits 1 > /work/ss_worst.rpt"]) + "\n"
    (work / "ss.tcl").write_text(tcl)
    orfs.docker_openroad(work, "/work/ss.tcl", "ss.log")
    wns = None
    for line in (work / "ss.log").read_text(errors="replace").splitlines():
        if line.startswith("OTC wns"):
            wns = float(line.split()[2]) * 1e12
    rpt = (work / "ss_worst.rpt").read_text(errors="replace") if (work / "ss_worst.rpt").is_file() else ""
    sp = re.search(r"Startpoint: (\S+)", rpt)
    ep = re.search(r"Endpoint: (\S+)", rpt)
    stages = {}
    ends = (work / "ss_ends.rpt").read_text(errors="replace") if (work / "ss_ends.rpt").is_file() else ""
    for m in re.finditer(r"^(\S+)/D \(\S+\)\s+[-0-9.]+\s+[-0-9.]+\s+([-0-9.]+)", ends, re.M):
        name = re.sub(r"\[\d+\]", "", m.group(1)).split("$")[0]
        key = re.sub(r"_[a-z0-9]+$", "", name) if re.match(r"(s|p)\d+_", name.split(".")[-1]) else name
        stages[key] = min(stages.get(key, 1e9), float(m.group(2)))
    out = dict(top=a.top, params=params, period_ps=a.period_ps, ss_setup_wns_ps=None if wns is None else round(wns, 1),
               ss_fmax_prelayout_hz=None if wns is None else round(1e12 / (a.period_ps - wns)),
               worst_start=sp and sp.group(1), worst_end=ep and ep.group(1),
               worst_slack_by_stage_ps=dict(sorted(stages.items(), key=lambda kv: kv[1])[:30]),
               basis="pre-layout: ORFS yosys/abc at CORNER=WC, OpenSTA SS RVT libs, ideal clock, 60 ps uncertainty")
    (work / "ss.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out))


if __name__ == "__main__":
    main()
