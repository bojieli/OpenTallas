#!/usr/bin/env python3
"""qwen-coll-io r5 2026-10-14 (OWNER 0ah static cycle schedule; OWNER 19:12 all on-chip execution real hardware):
COMPOSED bench of the static TP8 collective on the REAL static link RTL, rtl/test/tb_coll_tp8_static_links.sv.

8 dies, each: ot_coll_cmd_issue (compiler commands over the program-write face, issued by ot_qwen_fixed_issue) ->
ot_coll_tp8_static (or the die-name master) -> ot_coll_static_linkcal (IO calendar) -> qfd_io_xfifo_static (static
CDC) -> qfd_io_ucie_static / qfd_io_serdes_static x3 (static codecs, CRC32) -> fixed-latency PHY models (the only
modelled part).  The scheduler is tools/qwen_coll_tp8_static_bench.schedule (same compiler model) at the COMPOSED
latencies LU / LS; this script also writes the stage program (pw.hex) the issuer executes.

Composed latency (link roots mesochronous with the core root, PHI 0 same edge / PHI 1 link edge after the core edge):
  L_min = KC + KW + 17 + PHY   (UCIe: LU = 4 + 2 + 17 + 14 = 37;  SerDes: LS = 4 + 2 + 17 + 339 = 362)
the --tight case runs L_min - 1 and must FAIL (publication fault), proving the priced value is the minimum.
Exit 0 iff every case meets its expectation."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import os
import shutil

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from qwen_coll_tp8_static_bench import schedule, vectors, ND, GC  # noqa: E402

KC, KW, PU, PS = 4, 2, 14, 339
# TOKEN-XDIE-QTP8 10-18: die-lane / face-form options (all default 0 = the r5..s4 benches unchanged)
XD = dict(lanes=(0, 0, 0, 0, 0, 0), ev2=0, tok_reg=0, lx=(0, 0, 0))
# Q-COLLCAL 10-18 --real-lanes coll_lane_latency.json: the REAL forwarded lanes (+define+OT_TP8S_REAL_LANES), N / K per
# SerDes port and direction (tx, txv, rx, rxv) from the die GEN; RL = {param: value} (empty = fixed-delay lanes as before)
RL = dict(params={}, src=None)
D50 = dict(on=False)
# QC-TOK 10-25 --wavefront bind_reset.json (owner decision 13): per-partition release plusargs (tb OT_TP8S_WAVEFRONT);
# empty = the single-edge reset of every earlier bench (unchanged)
WF = dict(on=False, plus={}, start_rel=None, pw0=20, src=None, sha=None, map=None)
WF_D0 = 15            # the tb rst_n (rcnt == F) deasserts at cycle 15
# tb reset group -> plan partitions (bind_names.json of the r3 wavefront bind); a group releases at the LATEST member
WF_MAP = dict(WF_ISS=["sl_W5_fw"], WF_CORE=["coll_core"], WF_N=["coll_n"], WF_S=["coll_s"], WF_UCIE=["coll_ucie"],
              WF_FT=["coll_f0", "coll_f1", "coll_f2", "coll_f3", "coll_f4", "coll_f5"], WF_SER0=["io_serdes"],
              WF_SER1=["io_serdes_1"], WF_SER2=["io_serdes_2"])   # --duty50: six_five harness with 50 %-duty clocks (half-tick resolution)
VERILATOR = os.environ.get("OT_VERILATOR") or next((v for v in (os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"),) if os.path.exists(v)), None) or shutil.which("verilator")
DEPTH, START = 8, 40
SRC = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
    "rtl/rom/ot_coll_fold_slice.sv", "rtl/rom/ot_coll_rst_leaf.sv", "rtl/lib/ot_reset_sync.sv",
    "physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v",
    "physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v",
    "physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v",
    "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v",
    "rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv", "rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv",
    "rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv",
    "rtl/physical/ot_qfd_static_transport.sv", "rtl/physical/ot_qfd_io_xfifo_static.sv",
    "rtl/physical/ot_qfd_io_links_static.sv", "rtl/physical/ot_qfd_coll_static_face.sv", "rtl/physical/ot_qfd_ucie_static_share.sv", "rtl/physical/ot_qfd_ucie_six_five.sv", "rtl/physical/ot_qfd_collective_static_io.sv", "rtl/physical/ot_qfd_collective_static_io_production.sv",
    "rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue.sv",
    "rtl/rom/ot_coll_tp8_static.sv", "rtl/physical/ot_qfd_io_collective_static.sv",
    "rtl/rom/ot_coll_static_linkcal.sv", "rtl/rom/ot_coll_cmd_issue.sv",
    "rtl/qwen_split/qfd_seq_su_collective_calendar.sv",
    "rtl/hdc/ot_hdc_cg.sv", "rtl/qwen_split/qfd_fwd_lane.sv",
    "rtl/test/tb_coll_tp8_static_links.sv")]
RES = re.compile(r"TP8SL dies=8 .* mismatches=(\d+) extra=(\d+) out_err=(\d+) cmd_bad=(\d+) coll_fault=([01]+) "
                 r"issuer_fault=([01]+) die_fault=([01]+) words_out=(\d+) meas_lu=(-?\d+) meas_ls=(-?\d+) "
                 r"pr_overlap=(\d+) issuer_done=([01]+)")

# name, msgs, words, modes, expectation, plusargs
UNIT = [
    ("reduce_8w_x7", 7, 8, "r", "pos", {}),
    ("reduce_1w_x7_odd", 7, 1, "r", "pos", {}),
    ("gather_4w_x4", 4, 4, "g", "pos", {}),
    ("mixed_8w_x7", 7, 8, "m", "pos", {}),
    ("fault_drop_word", 4, 8, "r", "drop", {"DROP": 1}),
    ("fault_serdes_crc", 4, 8, "m", "corrupt", {"CORRUPT": 3}),
]
PRODUCTION = [
    ("qwen_ar_256w", 1, 256, "r", "pos", {}),
    ("qwen_layer_2x256w", 2, 256, "r", "pos", {}),
    ("qwen_argmax_1w", 1, 1, "g", "pos", {}),
    ("qwen_layer_2x256w_argmax", 3, 256, "rrg1", "pos", {}),
]


MU = dict(cases=None)   # MU-QWEN 10-18: --mu-cal cases (compiled multi-user command lists)


def mu_prog(cmds, nwords, lu, ls, shared_ucie, unchecked=False):
    """MU-QWEN: messages at the COMPILED command cycles of tools/qwen_static_schedule/mu_calendar (no greedy move);
    refuses if two messages book one engine resource cycle (the compiler's assertion, re-checked here)"""
    from qwen_coll_tp8_static_bench import word_events
    seen = {}
    prog = []
    for m, (c, mode) in enumerate(cmds):
        n = nwords[m]
        slots, b, wr, out, hold = word_events(mode, c, n, lu, ls)
        sets = dict(issue=slots, B=b, W=wr, O=out, hold=hold)
        if shared_ucie:
            sets["ucie"] = [x + 2 for x in slots] + ([x - lu - 2 for x in out] if mode == 0 else [])
        for r, xs in sets.items():
            for x in xs:
                if (r, x) in seen and not unchecked:
                    raise SystemExit(f"mu-cal collision: msg {m} and msg {seen[(r, x)]} on {r} at {x}")
                seen[(r, x)] = m
        prog.append(dict(msg=m, mode=mode, words=n, cmd_cycle=c, first_slot=slots[0], first_out=out[0], last_out=out[-1]))
    return prog


def program_words(prog, nwords, cmd_pin_stages=0, start=None):
    start = START if start is None else start
    """Stage program for ot_coll_cmd_issue: rows {cycle, words, mode}, tags, END row, seal (see its header)."""
    pw, rows = [], []
    for k, p in enumerate(prog):
        x = p["cmd_cycle"] - start - 1 - cmd_pin_stages
        assert x >= 4, "first command too close to the stage start"
        rows.append((x, nwords[k], p["mode"], 0, k))
    last = prog[-1]
    last_slot = last["cmd_cycle"] + 1 + (GC if last["mode"] else 1) * (nwords[-1] - 1)
    xe = last_slot + 2 - start - 1
    rows.append((xe, 0, 0, 1, 0))
    assert len(rows) <= DEPTH, f"{len(rows)} rows > issuer DEPTH {DEPTH}"
    for k, (x, w, m, e, tag) in enumerate(rows):
        pw.append((2 * k, (e << 49) | (m << 48) | (w << 32) | x))
        pw.append((2 * k + 1, tag))
    pw.append((2 * DEPTH, (0x434C << 48) | (len(rows) << 32) | xe))
    return pw


def build(out: Path, lu, ls, xu, xs, phi, define=None, qfd=False, parent=False, relays=(0,0,0,0), shared=False, six_five=False, seqsu=False):
    xdtag = ("_wf" if WF["on"] else "") + ("_d50" if D50["on"] else "") + ("_rl" + hashlib.sha256(json.dumps(RL["params"], sort_keys=True).encode()).hexdigest()[:8] if RL["params"] else "") + ("" if XD == dict(lanes=(0, 0, 0, 0, 0, 0), ev2=0, tok_reg=0, lx=(0, 0, 0)) else \
        "_e" + "-".join(map(str, XD["lanes"])) + f"_v{XD['ev2']}_t{XD['tok_reg']}_x" + "-".join(map(str, XD["lx"])))
    obj = out / f"obj_d{DEPTH}_u{lu}_s{ls}_xu{xu}_xs{xs}_phi{phi}{'_qfd' if qfd else ''}{'_seqsu' if seqsu else ''}{('_' + define) if define else ''}{xdtag}"
    h = out / f"harness_phi{phi}{'_d50' if D50['on'] else ''}.cpp"
    step = ("t->clk = 1; t->lck = 1; t->eval(); t->clk = 0; t->lck = 0; t->eval();" if phi == 0 else
            "t->clk = 1; t->eval(); t->lck = 1; t->eval(); t->clk = 0; t->eval(); t->lck = 0; t->eval();")
    if six_five and D50["on"]:
        # TOKEN-XDIE-QTP8 10-18: the r11..r15 gearbox (ot_qfd_ucie_six_five) has NEGEDGE half-cycle registers; the 1-tick
        # pulse harness below puts every negedge in the same tick as its posedge, which is not a clock.  Here every root
        # is a 50 %-duty clock at half-tick resolution: core 10, FDI 12 (rising edge offset 2*FDIPHI), block 60 half-ticks.
        step="bool ce=(tick%10)<5,fe=((tick+120-2*fphi)%12)<6,be=(tick%60)<30;t->clk=ce;t->lck=ce;t->fdi_ck=fe;t->blk_ck=be;t->eval();tick++;"
    elif six_five:
        step="bool ce=(tick%5==0),fe=(tick%6==fphi),be=(tick%30==0);t->clk=ce;t->lck=ce;t->fdi_ck=fe;t->blk_ck=be;t->eval();t->clk=0;t->lck=0;t->fdi_ck=0;t->blk_ck=0;t->eval();tick++;"
    old_h = h.read_text() if h.exists() else None
    h.write_text('#include "Vtb_coll_tp8_static_links.h"\n#include "verilated.h"\n'
                 "#include <cstring>\n#include <cstdlib>\nint main(int argc, char** argv) { Verilated::commandArgs(argc, argv);\n"
                 "  unsigned tick=0;int fphi=0;for(int i=1;i<argc;i++)if(!strncmp(argv[i],\"+FDIPHI=\",8))fphi=atoi(argv[i]+8);\n"
                 "  auto* t = new Vtb_coll_tp8_static_links; t->clk = 0; t->lck = 0; t->fdi_ck=0; t->blk_ck=0; t->eval();\n"
                 f"  while (!Verilated::gotFinish()) {{ {step} }}\n"
                 "  t->final(); delete t; return 0; }\n")
    cmd = [VERILATOR, "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
           "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "-Wno-UNOPTFLAT", "--top-module", "tb_coll_tp8_static_links",
           f"-GLATU={lu}", f"-GLATS={ls}", f"-GPU={PU}", f"-GPS={PS}", f"-GKC={KC}", f"-GKW={KW}", f"-GXU={xu}",
           f"-GXS={xs}", "-Mdir", str(obj)] + ([f"+define+{define}"] if define else []) + [str(s) for s in SRC] + \
          [str(h), "-CFLAGS", "-O1", "-j", "16"]
    if six_five:cmd += ["+define+OT_TP8S_PRODUCTION_WRAPPER"]
    cmd += [f"-G{k}={v}" for k, v in zip(("ET0", "ET1", "ET2", "ER0", "ER1", "ER2"), XD["lanes"])] + \
           [f"-GEV2={XD['ev2']}", f"-GTOKREG={XD['tok_reg']}"] + [f"-GLX{j}={v}" for j, v in enumerate(XD["lx"])]
    if RL["params"]:
        cmd += ["+define+OT_TP8S_REAL_LANES"] + [f"-G{k}={v}" for k, v in sorted(RL["params"].items())]
    if seqsu:cmd += ["+define+OT_TP8S_SEQSU"]
    if WF["on"]:cmd += ["+define+OT_TP8S_WAVEFRONT"]
    if DEPTH != 8:
        cmd += [f"-GISSUE_DEPTH={DEPTH}"]
    if parent:
        cmd += [f"-GSHARED={int(shared)}",f"-GSIXFIVE={int(six_five)}", "+define+OT_TP8S_PARENT"] + [f"-G{p}={v}" for p,v in zip(("RU","RS0","RS1","RS2"),relays)]
    if qfd:
        cmd += ["+define+OT_TP8S_QFD", f"+define+OT_QFDS_LU={lu}", f"+define+OT_QFDS_LS={ls}"]
    # Reuse only the exact source/executable/driver/profile previously recorded
    # in this output directory. FDIphase is a runtime argument, not a build.
    receipt=out/"record.json"
    exe=obj/"Vtb_coll_tp8_static_links"
    if receipt.exists() and exe.exists() and old_h==h.read_text():
        prior=json.loads(receipt.read_text())
        exact_sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC}
        if (prior.get("source_sha256")==exact_sources and
            prior.get("executable_sha256")==hashlib.sha256(exe.read_bytes()).hexdigest() and
            all(prior.get(k)==v for k,v in dict(latu=lu,lats=ls,xu=xu,xs=xs,phi=phi,
              phy_ucie=PU,phy_serdes=PS,die_name_master=qfd,production_parent=parent,
              relays=list(relays),shared_ucie=shared,six_five=six_five,mutant=define,sequencer_face=seqsu,
              die_lanes=list(XD['lanes']),valid_skew_port2=XD['ev2'],tok_reg=XD['tok_reg'],calendar_lane_cycles=list(XD['lx']),duty50=D50['on'],real_lanes=RL['params'],wavefront_build=WF['on']).items())):
            return exe
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"build failed:\n{r.stdout[-4000:]}{r.stderr[-4000:]}")
    return obj / "Vtb_coll_tp8_static_links"


def main():
    global PU
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--latu", type=int, default=KC + KW + 17 + PU)
    ap.add_argument("--lats", default=str(KC + KW + 17 + PS),
                    help="SerDes calendar LS: an integer, or 'cal' / 'cal-N' = the COMPILED calendar (Q-COLLCAL3: "
                         "tools/qwen_split/lane_groups.collective_calendar of the --real-lanes LX (else --lx) and --relays)")
    ap.add_argument("--xu", type=int, default=0)
    ap.add_argument("--xs", type=int, default=0)
    ap.add_argument("--phi", type=int, default=0, choices=(0, 1))
    ap.add_argument("--production", action="store_true")
    ap.add_argument("--expect-fail", action="store_true", help="negative control: some positive case must FAIL")
    ap.add_argument("--mutant-define", default=None)
    ap.add_argument("--only", default=None)
    ap.add_argument("--qfd", action="store_true")
    ap.add_argument("--relays",type=int,nargs=4,default=[0,0,0,0],metavar=("U","S0","S1","S2"))
    ap.add_argument("--parent",action="store_true",help="actualproduction collective+fiveface parent")
    ap.add_argument("--shared-ucie",action="store_true")
    ap.add_argument("--six-five",action="store_true")
    ap.add_argument("--fdi-phase",type=int,choices=range(6),default=0)
    ap.add_argument("--unsafe-shared-calendar",action="store_true")
    ap.add_argument("--seqsu",action="store_true",help="commands from the actual qfd_seq_su_collective_calendar face (PW944, {token,pos,tag6} tags)")
    ap.add_argument("--lanes", type=int, nargs=6, default=[0] * 6, metavar=("ET0", "ET1", "ET2", "ER0", "ER1", "ER2"),
                    help="die-level lane cycles io_collective<->io_serdes_j (TX ETj, RX ERj), from the die GEN fwd_lanes.json")
    ap.add_argument("--valid-skew", type=int, default=0, help="extra cycles of port 2 TX valid lane vs its data lane")
    ap.add_argument("--tok-reg", type=int, default=0, choices=(0, 1), help="hardened face form (TOK_REG pin registers)")
    ap.add_argument("--lx", type=int, nargs=3, default=None, help="lane cycles the SerDes face calendars absorb (parent LX0..2); "
                    "default 0 0 0, or the GEN's LX with --real-lanes")
    ap.add_argument("--real-lanes", type=Path, help="die GEN case/coll_lane_latency.json: real forwarded lanes (N, K per port) "
                    "in place of the fixed lane delays; LX defaults to its LX (the calendar the GEN emits)")
    ap.add_argument("--real-lanes-override", nargs="*", default=[], metavar="PARAM=V",
                    help="negative controls: override single lane parameters (e.g. KTV2=6: the as-built valid K)")
    ap.add_argument("--duty50", action="store_true", help="six_five harness with 50%%-duty clocks (needed by the negedge gearbox)")
    ap.add_argument("--plusarg",action="append",default=[],help="extra +K=V for every case (negative controls TAGBAD=1 / TOKMUT=1)")
    ap.add_argument("--mu-cal", type=Path, help="MU-QWEN: JSON {cases: [{name, kind, cmds: [[cycle, mode, words], ...]}]} "
                    "from tools/qwen_static_schedule/mu_calendar (cycles relative; rebased to the stage start)")
    ap.add_argument("--wavefront", type=Path, help="bind_reset.json / reset_offsets JSON {parts: {name: {release}}}: per-partition "
                    "wavefront reset (+define+OT_TP8S_WAVEFRONT) with the stage START broadcast after the latest release")
    ap.add_argument("--wf-start", type=int, default=130, help="START broadcast, clocks after the LATEST die rst_n (r3 carve: 130 "
                    "= max_release 128 + 2); negative controls set it earlier")
    ap.add_argument("--wf-skew", type=int, default=0, help="die g rst_n deasserts ((5g+3) mod 8) * SKEW clocks late (independent die resets)")
    ap.add_argument("--wf-override", nargs="*", default=[], metavar="WF_X=V", help="negative controls: override one group's release")
    a = ap.parse_args()
    if a.wavefront:
        global START
        rj = json.loads(a.wavefront.read_text())
        parts = rj["parts"]
        WF.update(on=True, src=str(a.wavefront), sha=hashlib.sha256(a.wavefront.read_bytes()).hexdigest(), map=WF_MAP,
                  max_release=rj.get("max_release"), root=rj.get("root"))
        WF["plus"] = {k: max(int(parts[p]["release"]) for p in ps) for k, ps in WF_MAP.items()}
        for kv in a.wf_override:
            k_, v_ = kv.split("=")
            assert k_ in WF["plus"], k_
            WF["plus"][k_] = int(v_)
        WF["plus"]["WF_SKEW"] = a.wf_skew
        last_rst = WF_D0 + 7 * a.wf_skew                       # latest die rst_n deassert
        START = last_rst + a.wf_start                          # the START broadcast (one cycle on every die)
        WF["pw0"] = START - 20                                 # program write window: same distance to start as before
        WF["start_rel"] = a.wf_start
        latest = max(v for k, v in WF["plus"].items() if k != "WF_SKEW")
        print(f"WAVEFRONT {a.wavefront} sha256 {WF['sha'][:12]} releases {WF['plus']} latest {latest} -> START {START} "
              f"(= latest die rst_n {last_rst} + {a.wf_start}), PW0 {WF['pw0']}", flush=True)
    if a.mu_cal:
        global DEPTH
        MU["cases"] = json.loads(a.mu_cal.read_text())["cases"]
        DEPTH = max(8, max(len(c["cmds"]) + 1 for c in MU["cases"]))
        assert DEPTH <= 31, "ot_coll_cmd_issue DEPTH <= 31"
    if a.real_lanes:
        cll = json.loads(a.real_lanes.read_text())
        for j in range(3):
            pj = cll["ports"][str(j)] if str(j) in cll["ports"] else cll["ports"][j]
            for d, pn in (("tx", "T"), ("txv", "TV"), ("rx", "R"), ("rxv", "RV")):
                RL["params"][f"N{pn}{j}"] = int(pj[d]["n"] or 0)
                RL["params"][f"K{pn}{j}"] = int(pj[d]["K"] or 0)
        for kv in a.real_lanes_override:
            k_, v_ = kv.split("=")
            RL["params"][k_] = int(v_)
        RL["src"] = str(a.real_lanes)
        if a.lx is None:
            a.lx = list(cll["LX"])
    if a.lx is None:
        a.lx = [0, 0, 0]
    CAL = None
    if str(a.lats).startswith("cal"):
        sys.path.insert(0, str(ROOT / "tools" / "qwen_split"))
        import lane_groups as LGC
        lx_c = list(cll["LX"]) if a.real_lanes else list(a.lx)   # the lanes AS BUILT (a --lx mutant is a wrong calendar LX)
        CAL = LGC.collective_calendar(lx_c, dict(PS=PS, KC=KC, KW=KW, RU=a.relays[0], RS0=a.relays[1], RS1=a.relays[2],
                                                 RS2=a.relays[3]))
        off = int(a.lats[3:] or 0)
        a.lats = CAL["LS"] + off
        print(f"COLL_CALENDAR compiled LS={CAL['LS']} (binding port {CAL['binding_port']}, LX {lx_c}, RS {CAL['RS']}) "
              f"-> lats {a.lats}", flush=True)
    a.lats = int(a.lats)
    XD.update(lanes=tuple(a.lanes), ev2=a.valid_skew, tok_reg=a.tok_reg, lx=tuple(a.lx))
    D50["on"] = a.duty50
    if a.six_five:
        a.parent=True;a.shared_ucie=True
        PU=20  # r10 200 MHz block-stage gearbox: 19 core edges + registered codec pin
    if a.parent:a.qfd=True
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    cases = PRODUCTION if a.production else UNIT
    if MU["cases"]:
        cases = [(c["name"], len(c["cmds"]), None, "mu", c.get("kind", "pos"), c.get("plusargs", {})) for c in MU["cases"]]
    if a.only:
        cases = [c for c in cases if re.search(a.only, c[0])]
    if a.xu or a.xs:
        cases = [("phy_longer_than_compiled", 4, 8, "m", "link", {})]
    if a.expect_fail:
        cases = [c for c in cases if c[4] == "pos"]
    if a.seqsu:
        assert a.production, "the sequencer face admits tags 0..2: production programs (<= 3 messages) only"
    exe = build(a.out, a.latu, a.lats, a.xu, a.xs, a.phi, a.mutant_define, a.qfd, a.parent, a.relays, a.shared_ucie, a.six_five, a.seqsu)
    bad, records, lane_meas = [], [], {}
    for i, (name, nmsg, words, mk, kind, extra) in enumerate(cases):
        rng = np.random.default_rng(100 + i)
        if mk == "mu":
            mc = next(c for c in MU["cases"] if c["name"] == name)
            st_ = max(START, WF["pw0"] + 2 * DEPTH + 1 + 8)   # the issuer is sealed before its start
            base = st_ + 8 - min(x[0] for x in mc["cmds"])
            modes = [int(x[1]) for x in mc["cmds"]]
            nw = [int(x[2]) for x in mc["cmds"]]
            prog = mu_prog([(int(x[0]) + base, m_) for x, m_ in zip(mc["cmds"], modes)], nw, a.latu, a.lats,
                           a.shared_ucie and not a.unsafe_shared_calendar, unchecked=bool(mc.get("unchecked")))
        elif mk == "rrg1":
            modes, nw = [0, 0, 1], [words, words, 1]
        else:
            modes = {"r": [0] * nmsg, "g": [1] * nmsg, "m": [int(x) for x in rng.integers(0, 2, nmsg)]}[mk]
            nw = [words] * nmsg
        if mk != "mu":
            prog = schedule(modes, nw, a.latu, a.lats, start=START + 6, shared_ucie=a.shared_ucie and not a.unsafe_shared_calendar)
        vec = a.out / f"vec_{name}"
        vectors(vec, nw, prog, 1000 + i)
        pw = program_words(prog, nw, cmd_pin_stages=int(a.qfd), start=(st_ if mk == "mu" else START))
        (vec / "pw.hex").write_text("".join(f"{ad:03x}{d:016x}\n" for ad, d in pw))
        st_run = st_ if mk == "mu" else START
        args = [str(exe), f"+VEC={vec}", f"+NMSG={nmsg}", f"+NPW={len(pw)}", f"+START={st_run}", f"+FDIPHI={a.fdi_phase}"] + \
               ([f"+PW0={WF['pw0']}"] + [f"+{k}={v}" for k, v in WF["plus"].items()] if WF["on"] else []) + \
               [f"+{k}={v}" for k, v in extra.items()] + [f"+{x}" for x in a.plusarg]
        run = subprocess.run(args, capture_output=True, text=True)
        txt = run.stdout
        (a.out / f"{name}.log").write_text(txt + run.stderr)
        m = RES.search(txt)
        lane_meas[name] = re.findall(r"^TP8SL_LANE .*$", txt, re.M)
        passed = run.returncode == 0 and bool(m) and any(l.strip() == "PASS" for l in txt.splitlines()) and "WF_BAD" not in txt
        ok = (not passed) if a.expect_fail else passed
        g = m.groups() if m else None
        span = max(p["last_out"] for p in prog) - prog[0]["first_slot"] + 1
        print(f"case {name} kind={kind} latu={a.latu} lats={a.lats} phi={a.phi} xu={a.xu} xs={a.xs} "
              f"mutant={a.mutant_define or '-'} {'PASS' if passed else 'FAIL'}"
              f"{' (expected FAIL)' if a.expect_fail else ''} " +
              (f"mismatches={g[0]} extra={g[1]} out_err={g[2]} cmd_bad={g[3]} coll_fault={g[4]} issuer_fault={g[5]} "
               f"die_fault={g[6]} words_out={g[7]} meas_lu={g[8]} meas_ls={g[9]} pr_overlap={g[10]} "
               f"compiled_span={span}" if g else "no result: " + txt.strip()[-400:]), flush=True)
        records.append(dict(name=name, kind=kind, passed=passed, messages=nmsg, words_per_message=nw, modes=modes,
                            program=prog, program_words=[[ad, f"{d:016x}"] for ad, d in pw],
                            compiled_span_cycles=span, result=dict(zip(
                                ["mismatches", "extra", "out_err", "cmd_bad", "coll_fault", "issuer_fault",
                                 "die_fault", "words_out", "meas_lu", "meas_ls", "pr_overlap", "issuer_done"], g))
                            if g else None))
        if not ok:
            bad.append(name)
    (a.out / "record.json").write_text(json.dumps(dict(
        schema="opentallas.qwen.tp8.collective.static_links.v1", ranks=ND, latu=a.latu, lats=a.lats, kc=KC, kw=KW,
        phy_ucie=PU, phy_serdes=PS, xu=a.xu, xs=a.xs, phi=a.phi, die_name_master=a.qfd, production_parent=a.parent, relays=a.relays, shared_ucie=a.shared_ucie, six_five=a.six_five, FDI_phase_ticks=a.fdi_phase, unsafe_shared_calendar=a.unsafe_shared_calendar, mutant=a.mutant_define, sequencer_face=a.seqsu, plusargs=a.plusarg,
        real_lanes=RL['params'], real_lanes_source=RL['src'], lane_meas=lane_meas, compiled_calendar=CAL,
        die_lanes=list(XD['lanes']), valid_skew_port2=XD['ev2'], tok_reg=XD['tok_reg'], calendar_lane_cycles=list(XD['lx']), duty50=D50['on'],
        verilator=VERILATOR, verilator_version=subprocess.run([VERILATOR, '--version'], capture_output=True, text=True).stdout.strip(),
        expect_fail=a.expect_fail, production=a.production, issuer_depth=DEPTH, stage_start=START, cmd_pin_stages=int(a.qfd),
        wavefront=(dict(source=WF["src"], sha256=WF["sha"], root=WF.get("root"), max_release=WF.get("max_release"),
                        group_map=WF["map"], releases=WF["plus"], die_rst_n_cycle=WF_D0, start_after_latest_die_rst=WF["start_rel"],
                        pw0=WF["pw0"], start_broadcast=START) if WF["on"] else None),
        modelled="PHY frame pipes only (fixed latency); all on-chip blocks are the real RTL masters",
        mechanism="compiler program -> fixed-issue core -> collective tokens -> IO calendar slots; no credits/ready/"
                  "backpressure; observed validity, CRC and publication are fault-only checks",
        cases=records, source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC},
        helper_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in
          ("tools/qwen_coll_tp8_static_links_bench.py","tools/qwen_coll_tp8_static_bench.py","tools/qwen_coll_tp8_bench.py","tools/hdc_golden.py","tools/qwen_split/lane_groups.py")},
        executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(), native_layer_qualified=False,
        physical_qualified=False), indent=2) + "\n")
    if bad:
        print(f"COLL_TP8SL FAIL failed={','.join(bad)}")
        sys.exit(1)
    print(f"COLL_TP8SL {'NEGATIVE-CONTROL ' if a.expect_fail else ''}PASS cases={len(cases)} latu={a.latu} lats={a.lats}")


if __name__ == "__main__":
    main()
