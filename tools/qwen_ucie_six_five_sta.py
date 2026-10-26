#!/usr/bin/env python3
"""Ordinary-STA probe of the QCOLL UCIe gearbox (qfd_ucie_six_five), r10 2026-10-15.

Synthesises the ACTUAL gearbox RTL with Yosys to ASAP7 RVT cells and runs OpenROAD/OpenSTA with
ideal clocks generated from one 200 MHz PLL reference (core x6 = 1.2 GHz, FDI x5 = 1 GHz, block x1),
TT Liberty for setup and FF Liberty for hold, uncertainty setup 60 / hold 25 ps, IO 0.2 T.
NO false paths, clock groups, multicycles or disabled arcs. For every (launch, capture) clock
pair it records the worst setup slack and the setup relation (capture edge - launch edge) STA
applies, and the worst hold slack.

Scope: pre-placement, zero wire load, ideal clocks. It proves which clock relations ordinary STA
imposes on the real logic, not physical closure. --variant r9 probes the historical r9 gearbox
(direct core<->FDI crossings) from a git revision for comparison."""
import argparse, hashlib, json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "openroad/orfs:latest"
P = "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM"
YOSYS = "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys"
OR = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
LIBS = {c: [f"asap7sc7p5t_{k}_RVT_{c}_nldm_{v}" for k, v in
            (("AO", "211120.lib.gz"), ("INVBUF", "220122.lib.gz"), ("OA", "211120.lib.gz"),
             ("SIMPLE", "211120.lib.gz"), ("SEQ", "220123.lib"))] for c in ("TT", "FF")}

# clock name, port expression in the wrapper, multiply factor vs 200 MHz reference
CLOCKS = {
    "r10": [("blk0", "blk_tx_ck", 1), ("blk1", "blk_rx_ck", 1), ("core", "core_ck", 6),
            ("fdi", "fdi_ck", 5), ("fdirx", "fdi_rx_ck", 5)],
    "r9": [("core", "core_ck", 6), ("fdi", "fdi_ck", 5), ("rx0", "fdi_rx_ck[0]", 5),
           ("rx1", "fdi_rx_ck[1]", 5), ("rx2", "fdi_rx_ck[2]", 5)],
}


def wrapper(variant):
    ck = CLOCKS[variant]
    nets = "".join(f" wire g_{n};\n BUFx4_ASAP7_75t_R u_gen_{n}(.A(pll_ref),.Y(g_{n}));\n" for n, _, _ in ck)
    if variant == "r10":
        conn = ".core_ck(g_core),.fdi_ck(g_fdi),.fdi_rx_ck(g_fdirx),.blk_tx_ck(g_blk0),.blk_rx_ck(g_blk1),"
    else:
        conn = ".core_ck(g_core),.fdi_ck(g_fdi),.fdi_rx_ck({g_rx2,g_rx1,g_rx0}),"
    return ("module gearbox_sta(input wire pll_ref,rst_n,tx_valid,input wire[596:0]tx_frame,\n"
            " output wire phy_tx_valid,output wire[1042:0]phy_tx_frame,input wire phy_rx_valid,\n"
            " input wire[1042:0]phy_rx_frame,output wire rx_valid,output wire[596:0]rx_frame,\n"
            " output wire core_fault,fdi_fault);\n" + nets +
            f" qfd_ucie_six_five u_g({conn}.rst_n(rst_n),.tx_valid(tx_valid),.tx_frame(tx_frame),\n"
            "  .phy_tx_valid(phy_tx_valid),.phy_tx_frame(phy_tx_frame),.phy_rx_valid(phy_rx_valid),\n"
            "  .phy_rx_frame(phy_rx_frame),.rx_valid(rx_valid),.rx_frame(rx_frame),\n"
            "  .core_fault(core_fault),.fdi_fault(fdi_fault));\nendmodule\n")


def sdc(variant):
    s = ["create_clock -name pll_ref -period 5000 [get_ports pll_ref]"]
    for n, _, m in CLOCKS[variant]:
        s.append(f"create_generated_clock -name {n} -master_clock pll_ref -source [get_ports pll_ref] "
                 f"-multiply_by {m} [get_pins u_gen_{n}/Y]")
    s += ["set_clock_uncertainty -setup 60 [all_clocks]", "set_clock_uncertainty -hold 25 [all_clocks]"]
    rx = ["fdi", "fdirx"] if variant == "r10" else ["fdi", "rx0", "rx1", "rx2"]
    io = [("core", "input", "tx_valid tx_frame*"), ("core", "output", "rx_valid rx_frame* core_fault"),
          ("fdi", "output", "phy_tx_valid phy_tx_frame* fdi_fault")]
    io += [(c, "input", "phy_rx_valid phy_rx_frame*") for c in rx]
    # die reset: released by a register of the named root; IO budget 0.2 T of the FASTEST capturing root
    io.append(("blk0" if variant == "r10" else "core", "input", "rst_n"))
    for c, d, ports in io:
        per = 5000 / (6 if ports == "rst_n" else dict((n, m) for n, _, m in CLOCKS[variant])[c])
        s.append(f"set_{d}_delay {0.2 * per:.3f} -clock {c} -add_delay [get_ports {{{ports}}}]")
    return "\n".join(s) + "\n"


def sta_tcl(variant, corner, kind):
    libs = " ".join(f"/w/lib/{Path(l).name.replace('.gz', '')}" for l in LIBS[corner])
    names = [n for n, _, _ in CLOCKS[variant]]
    lef = "/OpenROAD-flow-scripts/flow/platforms/asap7/lef"
    body = [f"read_lef {lef}/asap7_tech_1x_201209.lef", f"read_lef {lef}/asap7sc7p5t_28_R_1x_220121a.lef",
            f"foreach l {{{libs}}} {{read_liberty $l}}", "read_verilog /w/net.v", "link_design gearbox_sta",
            "read_sdc /w/clocks.sdc", "report_clock_properties"]
    for a in names:
        for b in names:
            body.append(f'puts "PAIR {a} {b}"')
            body.append(f"report_checks -from [get_clocks {a}] -to [get_clocks {b}] -path_delay {kind} "
                        "-format full_clock_expanded -digits 3 -group_path_count 1")
    body.append(f'puts "PAIR all all"\nreport_checks -path_delay {kind} -digits 3 -group_path_count 1')
    body.append('puts "STA_DONE"')
    return "\n".join(body) + "\n"


def parse(log):
    out = {}
    for blk in log.split("PAIR ")[1:]:
        head, _, rest = blk.partition("\n")
        a, b = head.split()[:2]
        if "No paths found" in rest or "slack" not in rest:
            out[f"{a}->{b}"] = None
            continue
        slack = float(re.search(r"(-?[\d.]+)\s+slack", rest).group(1))
        edges = re.findall(r"([-\d.]+)\s+[-\d.]+\s+clock (\S+) \((rise|fall) edge\)", rest)
        rel = None
        if len(edges) >= 2:
            rel = round(float(edges[-1][0]) - float(edges[0][0]), 3)
        sp = re.search(r"Startpoint: (\S+)", rest).group(1)
        ep = re.search(r"Endpoint: (\S+)", rest).group(1)
        out[f"{a}->{b}"] = dict(slack_ps=slack, relation_ps=rel, startpoint=sp, endpoint=ep)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--variant", choices=("r10", "r9"), default="r10")
    ap.add_argument("--rev", default=None, help="git revision for the gearbox source (default: working tree)")
    ap.add_argument("--src", type=Path, default=None, help="explicit gearbox source file (overrides --rev)")
    a = ap.parse_args()
    w = a.out.resolve(); w.mkdir(parents=True, exist_ok=True)
    rel = "rtl/physical/ot_qfd_ucie_six_five.sv"
    src = a.src.read_text() if a.src else subprocess.run(["git", "-C", str(ROOT), "show", f"{a.rev}:{rel}"], capture_output=True, text=True,
                         check=True).stdout if a.rev else (ROOT / rel).read_text()
    (w / "gearbox.sv").write_text(src); (w / "wrapper.v").write_text(wrapper(a.variant))
    (w / "clocks.sdc").write_text(sdc(a.variant))
    libs_tt = " ".join(f"-liberty /w/lib/{Path(l).name.replace('.gz', '')}" for l in LIBS["TT"])
    seq = f"/w/lib/{LIBS['TT'][-1]}"
    (w / "synth.ys").write_text(
        "".join(f"read_liberty -lib /w/lib/{Path(l).name.replace('.gz', '')}\n" for l in LIBS["TT"]) +
        "read_verilog -sv /w/gearbox.sv /w/wrapper.v\nsynth -top gearbox_sta -flatten\n"
        f"dfflibmap -liberty {seq}\nabc -D 833 {libs_tt}\nopt_clean -purge\n"
        "hilomap -singleton -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L\n"
        "stat\nwrite_verilog -noattr /w/net.v\n")
    (w / "sta_setup_tt.tcl").write_text(sta_tcl(a.variant, "TT", "max"))
    (w / "sta_hold_ff.tcl").write_text(sta_tcl(a.variant, "FF", "min"))
    prep = "mkdir -p /w/lib && " + " && ".join(
        (f"zcat {P}/{l} > /w/lib/{l[:-3]}" if l.endswith(".gz") else f"cp {P}/{l} /w/lib/{l}")
        for c in ("TT", "FF") for l in LIBS[c])
    cmd = (f"{prep} && {YOSYS} -q -l /w/synth.log /w/synth.ys && "
           f"{OR} -no_init -exit /w/sta_setup_tt.tcl > /w/sta_setup_tt.log 2>&1 && "
           f"{OR} -no_init -exit /w/sta_hold_ff.tcl > /w/sta_hold_ff.log 2>&1; rc=$?; rm -rf /w/lib; exit $rc")
    r = subprocess.run(["docker", "run", "--rm", "-u", f"{__import__('os').getuid()}", "-v", f"{w}:/w", IMAGE,
                        "bash", "-c", cmd], capture_output=True, text=True)
    (w / "docker.log").write_text(r.stdout + r.stderr)
    if r.returncode or "STA_DONE" not in (w / "sta_hold_ff.log").read_text():
        raise SystemExit(f"probe failed rc={r.returncode}: {(r.stdout + r.stderr)[-3000:]}")
    stat = (w / "synth.log").read_text()
    cells = re.findall(r"Number of cells:\s+(\d+)", stat) or re.findall(r"\n\s+(\d+)\s+cells\n", stat)
    setup = parse((w / "sta_setup_tt.log").read_text()); hold = parse((w / "sta_hold_ff.log").read_text())
    cross = {k: v for k, v in setup.items() if v and k.split("->")[0] != k.split("->")[1] and k != "all->all"}
    rec = dict(schema="opentallas.qwen.qcoll.gearbox_ordinary_sta.v1", variant=a.variant, rev=a.rev or (str(a.src) if a.src else "worktree"),
               gearbox_sha256=hashlib.sha256(src.encode()).hexdigest(),
               tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), image=IMAGE,
               cells=int(cells[-1]) if cells else None, exceptions="none", clocks="ideal, generated from 200 MHz",
               setup_tt=setup, hold_ff=hold,
               min_cross_clock_setup_relation_ps=min((v["relation_ps"] for v in cross.values()
                                                      if v["relation_ps"] is not None), default=None),
               worst_setup_slack_ps=min(v["slack_ps"] for v in setup.values() if v),
               worst_hold_slack_ps=min(v["slack_ps"] for v in hold.values() if v),
               worst_cross_clock_setup_slack_ps=min((v["slack_ps"] for v in cross.values()), default=None),
               scope="pre-placement zero-wire ideal-clock ordinary STA; not physical closure")
    (w / "record.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("variant", "cells", "min_cross_clock_setup_relation_ps",
                                          "worst_setup_slack_ps", "worst_cross_clock_setup_slack_ps", "worst_hold_slack_ps")}))
    for k, v in setup.items():
        if v: print("setup", k, v["relation_ps"], v["slack_ps"])


if __name__ == "__main__":
    main()
