#!/usr/bin/env python3
"""DS-ROM recovery lever "hop_closed" (MANDATORY): a stage-hop link endpoint that closes at 1.2 GHz.

Both the as-built S81 endpoint ot_dsrom_link_rt (the measured 0.7575 us hop) and the rejected successor
ot_dsrom_link_ct fail the pre-layout SS screen (-417.3 / -500.4 ps, results/rtl/dsrom_recovery_20261004/hop/
hop_ct.json).  ot_dsrom_link_cl (rtl/dsrom_sys/ot_dsrom_link_cl.sv) keeps link_ct's per-die-halves hop and lane
pacer and cuts every failing path (power-of-two replay indices, registered reverse-frame check, CRC in its own TX
and RX stages, registered-read SRAM-macro storage, split status counters); the module header lists each added
cycle.

Subcommands (heavy ones on the compute host):
  sim     Icarus runs of rtl/test/dsrom_sys/tb_dsrom_1m_hop_cl.sv (board legs on the SRAM macro model) -> hop_cl.json
  screen  pre-layout SS/FF screen, flop storage at depth 16 (tools/dsrom_reindex_screen.py) -> screen_pre/
  route   ORFS synth+P&R of the hardened board-leg endpoint (CREDITS 256 on 6 ot_sram_1r1w_256x256 macros), then
          tools/w18/corner_sta.py (SS setup / FF hold, 60/25 ps) -> route/
  record  results/rtl/dsrom_recovery_20261004/hop_closed/hop_cl.json + levers/hop_closed.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_recovery_hop as H  # noqa: E402

REC = ROOT / "results/rtl/dsrom_recovery_20261004"
MACRO = "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2"
RTL = ["rtl/test/dsrom_sys/tb_dsrom_1m_hop_cl.sv", "rtl/dsrom_sys/ot_dsrom_link_cl.sv",
       "rtl/dsrom_sys/ot_dsrom_link_chan.sv", "rtl/link/ot_link_crc32.sv", f"{MACRO}/ot_sram_1r1w_256x256_m2_r2c2.v"]
ENDPOINT = ["rtl/dsrom_sys/ot_dsrom_link_cl.sv", "rtl/dsrom_sys/ot_dsrom_link_chan.sv", "rtl/link/ot_link_crc32.sv"]
FB = 96


def cases():
    L = H.lanes()
    pn, pd = L["bytes_per_cycle"].numerator, L["bytes_per_cycle"].denominator
    base = dict(FB=FB, CH=H.CH_LFEC, CHU=H.CH_UCIE, CRED=256, SEQW=9, CREDU=64, SEQWU=8, PNUM=pn, PDEN=pd, MODE=1,
                BMEM=1)
    return [
        ("hop_cl_halves", base, H.RESIDUAL_B, "HEADLINE stage hop (board legs on the SRAM macro model)", "PASS"),
        ("hop_cl_halves_err", dict(base, ERRF=37, ERRR=29), H.RESIDUAL_B,
         "exactness under errors: forward flip every 37th frame, reverse every 29th (go-back-N replay)", "PASS"),
        ("ret_cl_flit", dict(base, MODE=0), H.RETURN_B, "HEADLINE token return: one 8-B flit, one traversal", "PASS"),
        ("hop_cl_halves_draft5", base, H.DRAFT_B, "DSpark draft 5-row hop (204,880 B) at the hardened depth 256",
         "PASS"),
        ("hop_cl_halves_kp4", dict(base, CH=H.CH_KP4), H.RESIDUAL_B, "sensitivity: 209 ns full-KP4 tier", "PASS"),
        ("hop_cl_halves_flop", dict(base, BMEM=0), H.RESIDUAL_B, "storage-form equivalence: flop arrays", "PASS"),
        ("neg_nocrc_err", dict(base, ERRF=37, ERRR=29, OT_DSROM_LINK_MUT_NOCRC=1), H.RESIDUAL_B,
         "negative control: receiver ignores the CRC under injected errors -> must FAIL", "FAIL"),
    ]


def run_case(work: Path, case):
    name, defs, nbytes, role, expect = case
    vvp = work / f"{name}.vvp"
    cmd = ["iverilog", "-g2012", "-o", str(vvp)] + [f"-D{k}={v}" for k, v in sorted(defs.items())] + \
        [str(ROOT / s) for s in RTL]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"compile {name}: {r.stderr[-2000:]}")
    r = subprocess.run(["vvp", "-n", str(vvp), f"+bytes={nbytes}", "+seed=81", f"+case={name}"],
                       capture_output=True, text=True)
    m = re.search(r"HOPCT_SUMMARY (.*)", r.stdout)
    if not m:
        raise SystemExit(f"{name}: no summary\n{r.stdout[-2000:]}{r.stderr[-2000:]}")
    f = {}
    for kv in m.group(1).split():
        k, v = kv.split("=", 1)
        f[k] = int(v) if re.fullmatch(r"-?\d+", v) else v
    return dict(case=name, role=role, defines=defs, bytes=nbytes, summary=m.group(0), fields=f, expect=expect,
                mismatch_lines=[l for l in r.stdout.splitlines() if l.startswith("MISMATCH")][:5],
                exact=f["result"] == "PASS", as_expected=f["result"] == expect)


def cmd_sim(a):
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    runs = {c[0]: run_case(work, c) for c in cases()}
    for r in runs.values():
        print(r["summary"][:300], flush=True)
    out = dict(simulator=subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0],
               runs=runs, sources={p: H.sha(ROOT / p) for p in RTL + ["tools/dsrom_hop_closed.py"]},
               generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    (work / "hop_cl.json").write_text(json.dumps(out, indent=1) + "\n")


def params(credits, seqw, mem):
    L = H.lanes()
    return dict(FLIT_BYTES=FB, CHANNEL_CYCLES=1, CREDITS=credits, SEQW=seqw, KEEPALIVE=16, MEM=mem,
                PHY_NUM=L["bytes_per_cycle"].numerator, PHY_DEN=L["bytes_per_cycle"].denominator)


def cmd_screen(a):
    work = Path(a.work)
    args = [sys.executable, str(ROOT / "tools/dsrom_reindex_screen.py"), "--top", "ot_dsrom_link_cl",
            "--period-ps", "833", "--work", str(work / "screen_pre")]
    for s in ENDPOINT:
        args += ["--source", s]
    for k, v in params(16, 5, 0).items():
        args += ["--param", f"{k}={v}"]
    subprocess.run(args, check=True, cwd=ROOT)


CONTEXT_SDC = "physical/dsrom_link/context_io.sdc"
# routed configurations, both under the in-context I/O constraints of the baseline link-clock record
ROUTES = {
    # the hardened S81 board-leg endpoint at its real storage: CREDITS 256 on 6 ot_sram_1r1w_256x256 macros
    "hard": dict(credits=256, seqw=9, mem=1),
    # like-for-like with results/rtl/dsrom_baseline_link_clock_20261004/context_r1_FAIL (flop storage, 16 credits)
    "ctx16": dict(credits=16, seqw=5, mem=0),
}


def cmd_route(a):
    rc = ROUTES[a.config]
    work = Path(a.work) / f"route_{a.config}"
    work.mkdir(parents=True, exist_ok=True)
    args = [sys.executable, "tools/run_abi3_physical.py", "--view", "asap7", "--top", "ot_dsrom_link_cl"]
    for s in ENDPOINT:
        args += ["--source", s]
    for k, v in params(rc["credits"], rc["seqw"], rc["mem"]).items():
        args += ["--param", f"{k}={v}"]
    if rc["mem"]:
        args += ["--macro-view", f"ot_sram_1r1w_256x256_m2_r2c2={MACRO}", "--macro-place-halo", str(a.halo), str(a.halo)]
    args += ["--orfs-var", f"SDC_FILE=/src/{CONTEXT_SDC}",
             "--clock-period-ns", "0.833333", "--clock-uncertainty-ns", "0.06", "--clock-uncertainty-hold-ns", "0.025",
             "--orfs-corner", "WC", "--hold-corners", "WC,BC", "--io-delay-fraction", "0.2",
             "--stages", "pnr", "--core-utilization", str(a.util), "--place-density", str(a.density),
             "--hold-margin-ns", "0.01", "--orfs-var", "ADDER_MAP_FILE=", "--orfs-var", "NUM_CORES=20",
             "--slew-margin-percent", "30", "--purpose", "signoff_target",
             "--nickname-tag", f"claude_hopcl_{a.config}_{a.tag}", "--keep-workdir", str(work / "work"), "--force",
             "--output", str(work / "physical.json")]
    subprocess.run(args, cwd=ROOT)
    subprocess.run([sys.executable, "tools/w18/corner_sta.py", "--orfs-dir", str(work / "work/orfs"),
                    *(["--macro", MACRO] if rc["mem"] else []), "--output", str(work / "corner_sta.json")], cwd=ROOT)


WINDOW_TCL = r"""
read_db {odb}
set_global_routing_layer_adjustment M2-M7 0.5
set_routing_layers -clock M2-M7
set_routing_layers -signal M2-M7
global_route -allow_congestion -congestion_iterations 30
set tech [ord::get_db_tech]
set grid [[ord::get_db_block] getGCellGrid]
set nx [llength [$grid getGridX]]; set ny [llength [$grid getGridY]]
set worst 0.0; set wl ""; set over 0; set n 0
foreach ln {{M2 M3 M4 M5 M6 M7}} {{
  set layer [$tech findLayer $ln]
  for {{set j 0}} {{$j + 4 <= $ny}} {{incr j 4}} {{
    for {{set i 0}} {{$i + 4 <= $nx}} {{incr i 4}} {{
      set c 0; set u 0
      for {{set dj 0}} {{$dj < 4}} {{incr dj}} {{ for {{set di 0}} {{$di < 4}} {{incr di}} {{
        set c [expr {{$c + [$grid getCapacity $layer [expr {{$i+$di}}] [expr {{$j+$dj}}]]}}]
        set u [expr {{$u + [$grid getUsage $layer [expr {{$i+$di}}] [expr {{$j+$dj}}]]}}] }} }}
      if {{$c > 0}} {{ incr n; set r [expr {{double($u) / $c}}]; if {{$r > 1.0}} {{ incr over }}
        if {{$r > $worst}} {{ set worst $r; set wl "$ln $i $j" }} }}
    }}
  }}
}}
puts "OTW worst_window_use_cap $worst at $wl windows $n over $over"
"""


def cmd_congestion(a):
    """4x4-gcell window use/capacity of the routed endpoint (global route re-run on the routed design, as
    tools/qwen_rom_fulldie_b3r2.summarize), plus the flow's own final GRT congestion report."""
    import glob
    d = Path(a.work) / f"route_{a.config}"
    base = Path(glob.glob(str(d / "work/orfs/results/asap7/*/base"))[0])
    odb = next(p for p in (base / "6_final.odb", base / "5_3_route.odb", base / "5_1_grt.odb") if p.is_file())
    rel = odb.relative_to(d / "work/orfs")
    (d / "work/orfs/ot_window.tcl").write_text(WINDOW_TCL.format(odb=f"/work/{rel}"))
    r = subprocess.run(["docker", "run", "--rm", "-v", f"{d / 'work/orfs'}:/work", os.environ.get(
        "OPENTALLAS_ORFS_IMAGE", "openroad/orfs:latest"), "bash", "-lc",
        "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit -threads 8 /work/ot_window.tcl"],
        capture_output=True, text=True)
    m = re.search(r"OTW worst_window_use_cap (\S+) at (\S+ \S+ \S+) windows (\d+) over (\d+)", r.stdout)
    log = next(iter(glob.glob(str(d / "work/orfs/logs/asap7/*/base/5_1_grt.log"))), None)
    grt = {}
    if log:
        t = Path(log).read_text(errors="replace")
        i = t.rfind("Final congestion report")
        for ln in t[i:].splitlines()[3:12] if i >= 0 else []:
            f = ln.split()
            if len(f) >= 9 and (f[0].startswith("M") or f[0] == "Total"):
                grt[f[0]] = dict(usage_pct=float(f[3].rstrip("%")), max_h=int(f[4]), max_v=int(f[6]), overflow=int(f[8]))
    out = dict(odb=str(rel), worst_window_use_cap=float(m.group(1)) if m else None, worst_window_at=m and m.group(2),
               windows=m and int(m.group(3)), windows_over_1=m and int(m.group(4)),
               grt_final=grt, grt_overflow=grt.get("Total", {}).get("overflow"),
               basis="4x4-gcell windows, layers M2-M7, use/cap after global_route (layer adjustment 0.5) on the routed "
                     "design; grt_overflow = the ORFS 5_1_grt final congestion report Total overflow",
               stderr_tail=r.stderr[-800:] if not m else "")
    (d / "congestion.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("worst_window_use_cap", "windows_over_1", "grt_overflow")}))


MACRO_UM2 = 7091.712            # ot_sram_1r1w_256x256_m2_r2c2.json area.macro_area_um2
S81_DIES = 324 + 12             # 81 stages x TP4 rank dies (dsrom_s81_component_word_service resource) + 12 head dies
DRAFT_PRIMARY, DRAFT_REPLICA, DRAFT_LINKS_PER_PRIMARY = 4, 60, 15   # results/rtl/dsrom_recovery_20261004/draft/placement.json
RT_A16_UM2 = 13622.28354        # results/rtl/dsrom_recovery_20261004/hop/hop_ct.json screen.baseline_link_rt_same_screen


def physical_cost(work, routes, pre):
    """Area (vs the pinned ot_dsrom_link_rt at its as-built S81 depths), per die and in total, slacks, congestion."""
    sc = lambda n: json.loads((work / n / "screen.json").read_text())["cell_area_um2"]
    hard = routes["hard"]
    std_hard = hard["physical_summary"].get("standard_cell_area_um2")
    cl_board = dict(stdcell_um2=std_hard, macros=6, macro_um2=6 * MACRO_UM2,
                    total_um2=round((std_hard or 0) + 6 * MACRO_UM2, 1),
                    basis="routed hard endpoint (FLIT 96, CREDITS 256): std-cell area of the routed run (incl. CTS and "
                          "hold buffers) + 6 x ot_sram_1r1w_256x256_m2_r2c2 macro outlines")
    cl_ucie = dict(total_um2=sc("area_ucie64_cl"), basis="ORFS synthesis cell area, ot_dsrom_link_cl FLIT 96 CREDITS 64 "
                   "flop storage, unpaced (the in-package UCIe leg); pre-CTS, no hold buffers")
    a64 = sc("area_rt64")
    slope = (a64 - RT_A16_UM2) / 48.0
    rt_board = dict(total_um2=round(RT_A16_UM2 + slope * (512 - 16), 1), basis=f"pinned ot_dsrom_link_rt FLIT 64 at the "
                    f"as-built board depth CREDITS 512 (tb_dsrom_1m_hop), linear in depth from ORFS synthesis cell area "
                    f"at CREDITS 16 ({RT_A16_UM2}) and 64 ({a64}) um2 (flop storage, as the pinned RTL builds it)")
    rt_ucie = dict(total_um2=a64, basis="pinned ot_dsrom_link_rt FLIT 64 CREDITS 64 (the as-built UCIe leg), synthesis "
                   "cell area")
    per_die_new = cl_board["total_um2"] + cl_ucie["total_um2"]
    per_die_old = rt_board["total_um2"] + rt_ucie["total_um2"]
    d_stage = per_die_new - per_die_old
    d_board = cl_board["total_um2"] - rt_board["total_um2"]
    draft_d = DRAFT_PRIMARY * DRAFT_LINKS_PER_PRIMARY * d_board + DRAFT_REPLICA * d_board
    total_mm2 = (S81_DIES * d_stage + draft_d) / 1e6
    cg = {nm: json.loads((work / f"route_{nm}/congestion.json").read_text())
          if (work / f"route_{nm}/congestion.json").is_file() else {} for nm in ROUTES}
    ss = min(r["ss_setup_wns_ps"] for r in routes.values())
    ff = min(r["ff_hold_wns_ps"] for r in routes.values())
    return dict(
        area_um2_per_element=dict(new_board_endpoint=cl_board, new_ucie_endpoint=cl_ucie,
                                  old_board_endpoint=rt_board, old_ucie_endpoint=rt_ucie,
                                  delta_board_um2=round(d_board, 1),
                                  delta_stage_die_um2=round(d_stage, 1),
                                  unit="one link module = its sender half on one die + its receiver half on the next; "
                                       "a die hosts one board link's worth (stage hop in + out) and one UCIe link's "
                                       "worth (peer exchange)"),
        area_mm2_per_die=dict(s81_stage_or_head_die=round(d_stage / 1e6, 5),
                              draft_primary_die=round(DRAFT_LINKS_PER_PRIMARY * d_board / 1e6, 5),
                              draft_replica_die=round(d_board / 1e6, 5),
                              new_per_s81_die_mm2=round(per_die_new / 1e6, 5),
                              old_per_s81_die_mm2=round(per_die_old / 1e6, 5),
                              basis="delta vs the pinned link_rt at its as-built depths; draft: 15 replica board links "
                                    "per primary die and 1 per replica die (DP1-EP5), each a hardened board endpoint"),
        area_mm2_total=round(total_mm2, 4),
        area_total_basis=f"{S81_DIES} S81 stage+head dies x per-die delta + DP1-EP5 draft links "
                         f"({DRAFT_PRIMARY} x {DRAFT_LINKS_PER_PRIMARY} + {DRAFT_REPLICA}) x board delta",
        dies_added=0,
        ss_wns_ps=ss, ff_hold_wns_ps=ff,
        slack_basis="routed in context at 1.2 GHz (worst over the hard 256-deep SRAM endpoint and the like-for-like "
                    "16-deep flop endpoint): run_abi3_physical pnr under " + CONTEXT_SDC + " (the baseline in-context "
                    "record's I/O 100/30 in, 60/25 out, 0.6 fF), tools/w18/corner_sta.py SS setup 60 ps / FF hold "
                    "25 ps on the routed 6_final + SPEF, propagated clock; pre-layout SS " + str(pre["ss_setup_wns_ps"])
                    + " / FF " + str(pre["ff_hold_wns_ps"]),
        grt_overflow={nm: c.get("grt_overflow") for nm, c in cg.items()},
        worst_window_use_cap={nm: c.get("worst_window_use_cap") for nm, c in cg.items()},
        congestion_basis="ORFS 5_1_grt final congestion report Total overflow; 4x4-gcell windows M2-M7 use/cap after "
                         "global_route on the routed endpoint (tools/dsrom_hop_closed.py congestion)",
        die_edge=dict(changes=False, stage_lanes_per_die_each_way=7, ucie_links=1,
                      basis="per-die halves ride each die's already-budgeted 7 stage lanes each way "
                            "(results/arch/v41_rack.json stage_out/stage_in 14 per 2-die package) and the existing "
                            "UCIe peer link; the endpoint's port is the same flit interface to the same SerDes / UCIe "
                            "PHY, so the S81 die's SerDes and UCIe shoreline and pin count are unchanged; draft replica "
                            "links are the DP1-EP5 placement's own 15-per-primary star (already in placement.json)"),
        s81_rerun_needed=False,
        s81_rerun_why=("no S81 die re-floorplan: dies and shoreline are unchanged and the new endpoints are "
                       + ("smaller" if d_stage <= 0 else "larger") + f" than the as-built ones by "
                       f"{abs(d_stage) / 1e6:.4f} mm2 per die, against the S81 floorplan's 4.238 mm2 'link' "
                       "allotment (results/rtl/dsrom_s81_fulldie_20261004/floorplan.json area_mm2_by_kind.link); only "
                       "the per-token composition reruns (tools/dsrom_1m_allmeasured.py, done here)"))


def cmd_record(a):
    work = Path(a.work)
    sim = json.loads((work / "hop_cl.json").read_text())
    runs = sim["runs"]
    hop = H.hop_row(runs["hop_cl_halves"], H.CH_LFEC, H.CH_UCIE)
    draft = H.hop_row(runs["hop_cl_halves_draft5"], H.CH_LFEC, H.CH_UCIE)
    kp4 = H.hop_row(runs["hop_cl_halves_kp4"], H.CH_KP4, H.CH_UCIE)
    flop = H.hop_row(runs["hop_cl_halves_flop"], H.CH_LFEC, H.CH_UCIE)
    err = H.hop_row(runs["hop_cl_halves_err"], H.CH_LFEC, H.CH_UCIE)
    rf = runs["ret_cl_flit"]["fields"]
    wire = 2 * H.SERDES_STAGES
    ret_cyc = H.RETURN_TRAVERSALS * rf["first_flit"] + wire
    ret = dict(exact=runs["ret_cl_flit"]["exact"], per_traversal_cycles=rf["first_flit"],
               measured_endpoint_cycles_per_traversal=rf["first_flit"] - H.CH_LFEC, traversals=H.RETURN_TRAVERSALS,
               wire_stage_cycles=wire, total_cycles=ret_cyc, us=round(ret_cyc / H.CLK * 1e6, 4))
    exact = all(r["as_expected"] for r in runs.values())
    pre = json.loads((work / "screen_pre/screen.json").read_text())
    routes = {}
    for nm in ROUTES:
        d = work / f"route_{nm}"
        cs = json.loads((d / "corner_sta.json").read_text())
        ph = json.loads((d / "physical.json").read_text()) if (d / "physical.json").is_file() else {}
        routes[nm] = dict(config=dict(ROUTES[nm], **params(ROUTES[nm]["credits"], ROUTES[nm]["seqw"], ROUTES[nm]["mem"])),
                          ss_setup_wns_ps=cs["setup_ss"]["worst_slack_ps"], ss_tns_ps=cs["setup_ss"].get("tns_ps"),
                          ff_hold_wns_ps=cs["hold_ff"]["worst_slack_ps"],
                          ff_violating=cs["hold_ff"].get("violating_d_pins"), corner_sta=cs,
                          flow_completed=ph.get("flow_completed"),
                          drc=((ph.get("place_and_route") or {}).get("metrics") or {}).get("drc_errors"),
                          physical_summary={k: v for k, v in ((ph.get("place_and_route") or {}).get("metrics") or {}).items()
                                            if k in ("die_area_um2", "core_area_um2", "standard_cell_area_um2",
                                                     "macro_area_um2", "macro_count", "drc_errors", "instance_count",
                                                     "sequential_cell_count", "antenna_violating_nets",
                                                     "max_slew_violations", "max_cap_violations",
                                                     "utilization_fraction", "routed_wirelength_um")})
    ok = lambda r: (r["ss_setup_wns_ps"] is not None and r["ff_hold_wns_ps"] is not None
                    and r["ss_setup_wns_ps"] >= 0 and r["ff_hold_wns_ps"] >= 0)
    closes = pre["ss_setup_wns_ps"] >= 0 and pre["ff_hold_wns_ps"] >= 0 and all(ok(r) for r in routes.values())
    ct = json.loads((REC / "hop/hop_ct.json").read_text())
    old = json.loads(H.LINKS.read_text())["hop"]
    detail = dict(
        schema="opentallas.dsrom-recovery.hop-closed.v1",
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        scope="DS-ROM S81 stage hop, DSpark draft 5-row hop and token return through the closed endpoint "
              "ot_dsrom_link_cl, Icarus at 1.2 GHz, board legs on the ASAP7 ot_sram_1r1w_256x256 macro model; "
              "per-die halves on 7 paced stage lanes per die (lane basis as hop_ct.json lane_assumption)",
        lane_assumption=ct["lane_assumption"],
        added_cycles_vs_link_ct=dict(
            per_leg_forward=4, per_hop=2 * 4,
            items=["RX CRC compare in its own stage (+1)", "receive write register (+1)",
                   "registered-read SRAM + output register (+1)", "4-entry output skid (+1)",
                   "TX CRC moved into existing TX stage 1 (0)", "reverse-frame CRC registered: ACK/credit return +1 "
                   "(off the forward path while credits cover the round trip; binds 1068-flit draft halves slightly)",
                   "replays: one read outstanding, <= 1 replay launch per 3 cycles (error recovery only)",
                   "status counters split 16+16 with registered carry; fault causes registered (+1 to the latch)"]),
        hop=hop, draft_hop_5row=draft, token_return=ret, hop_kp4_sensitivity=kp4, hop_flop_storage=flop,
        hop_error_injection=err,
        compare=dict(link_rt_as_built=dict(hop_us=old["per_hop_us"], total_cycles=old["total_cycles"],
                                           screen_ss_ps=ct["screen"]["baseline_link_rt_same_screen"]["ss_setup_wns_ps"],
                                           closes=False),
                     link_ct_rejected=dict(hop_us=ct["hop"]["us"], total_cycles=ct["hop"]["total_cycles"],
                                           draft_hop_us=ct["draft_hop_5row"]["us"],
                                           screen_ss_ps=ct["screen"]["ss_setup_wns_ps"], closes=False)),
        screen_prelayout=pre,
        routes=routes, context_sdc=CONTEXT_SDC, macro=MACRO,
        runs=runs, simulator=sim["simulator"], sources=sim["sources"],
        pinned_unchanged={p: H.sha(ROOT / p) for p in ("rtl/dsrom_sys/ot_dsrom_link_rt.sv",
                                                      "rtl/dsrom_sys/ot_dsrom_link_ct.sv",
                                                      "rtl/test/dsrom_sys/tb_dsrom_1m_hop.sv",
                                                      "rtl/test/dsrom_sys/tb_dsrom_1m_hop_ct.sv")})
    (REC / "hop_closed").mkdir(parents=True, exist_ok=True)
    (REC / "hop_closed/hop_cl.json").write_text(json.dumps(detail, indent=1, default=str) + "\n")
    verdict = "ADOPT" if exact and closes else "FAIL_NOT_CLOSED"
    lever = dict(
        schema="opentallas.dsrom-recovery.lever.v1", lever="hop_closed", verdict=verdict, exact=exact,
        class_="MANDATORY baseline block: the stage-hop endpoint must close; replaces the unclosed as-built hop",
        as_built_not_closed=("AS-BUILT HOP NOT CLOSED: the pinned ot_dsrom_link_rt behind the measured 0.7575 us hop "
                             "(links.json) fails the 1.2 GHz pre-layout SS screen at -417.3 ps "
                             "(results/rtl/dsrom_recovery_20261004/hop/hop_ct.json screen.baseline_link_rt_same_screen) "
                             "and, routed in context, SS -176.6 ps / FF hold -44.7 ps "
                             "(results/rtl/dsrom_baseline_link_clock_20261004/context_r1_FAIL/verdict.json)"),
        ss_ff=dict(prelayout=dict(ss_setup_wns_ps=pre["ss_setup_wns_ps"], ff_hold_wns_ps=pre["ff_hold_wns_ps"],
                                  basis="ORFS yosys/abc CORNER=WC (ADDER_MAP_FILE off), OpenSTA SS/FF, ideal clock, "
                                        "I/O false-pathed; flop storage depth 16"),
                   routed_in_context={nm: dict(ss_setup_wns_ps=r["ss_setup_wns_ps"], ff_hold_wns_ps=r["ff_hold_wns_ps"],
                                               ss_tns_ps=r["ss_tns_ps"], ff_violating=r["ff_violating"],
                                               flow_completed=r["flow_completed"], drc=r["drc"])
                                      for nm, r in routes.items()},
                   basis="run_abi3_physical pnr (WC, hold WC/BC) under the in-context I/O SDC of "
                         "results/rtl/dsrom_baseline_link_clock_20261004/context_r1_FAIL (input 100/30 ps, output "
                         "60/25 ps, load 0.6 fF; " + CONTEXT_SDC + "); routed 6_final + SPEF timed by "
                         "tools/w18/corner_sta.py at SS (setup, 60 ps) and FF (hold, 25 ps), propagated clock; "
                         "hard = CREDITS 256 on 6 ot_sram_1r1w_256x256 macros (own SS/FF liberty), ctx16 = the "
                         "baseline record's like-for-like flop configuration",
                   period_ps=833.333, closes=closes),
        info=dict(hop_us=hop["us"],
                  hop_source=f"ot_dsrom_link_cl RTL {hop['measured_endpoint_cycles']} cyc (closed endpoint; per-die "
                             f"halves of 40,976 B, 96-B flits paced to 7 x 13.18 GB/s lanes, cut-through UCIe) + "
                             f"light-FEC PHY VENDOR BUDGET 130 ns + UCIe 10 ns + 2x45 routed wire stages",
                  hop_cls="measured+vendor_phy",
                  draft_hop_us=draft["us"],
                  draft_hop_source=f"ot_dsrom_link_cl RTL, 5-row 204,880 B per-die halves ({draft['total_cycles']} cyc "
                                   f"incl. light-FEC 156 + UCIe 11 + 90 wire), case hop_cl_halves_draft5"),
        nodes={"token.return": dict(us=ret["us"], cls="measured+vendor_phy",
                                    source=f"token return: {H.RETURN_TRAVERSALS} x (ot_dsrom_link_cl "
                                           f"{ret['measured_endpoint_cycles_per_traversal']} cyc + light-FEC VENDOR "
                                           f"BUDGET {H.CH_LFEC} cyc) + 90 wire")},
        old_hop_us=old["per_hop_us"], new_hop_us=hop["us"], old_hop_cycles=old["total_cycles"],
        new_hop_cycles=hop["total_cycles"], detail=str((REC / "hop_closed/hop_cl.json").relative_to(ROOT)),
        rtl=dict(endpoint="rtl/dsrom_sys/ot_dsrom_link_cl.sv", bench="rtl/test/dsrom_sys/tb_dsrom_1m_hop_cl.sv"),
        physical_cost=physical_cost(work, routes, pre),
        command="python3 tools/dsrom_hop_closed.py " + " ".join(sys.argv[1:]))
    if lever["physical_cost"]["area_mm2_per_die"]["s81_stage_or_head_die"] > 4.238 / 8:
        lever["physical_cost"]["s81_rerun_needed"] = True
        lever["physical_cost"]["s81_rerun_why"] = "per-die endpoint delta exceeds one S81 floorplan link slot"
    (REC / "levers/hop_closed.json").write_text(json.dumps(lever, indent=1, default=str) + "\n")
    print(json.dumps(dict(verdict=verdict, exact=exact, pre=(pre["ss_setup_wns_ps"], pre["ff_hold_wns_ps"]),
                          routed={nm: (r["ss_setup_wns_ps"], r["ff_hold_wns_ps"]) for nm, r in routes.items()}, hop=hop["us"], draft=draft["us"], ret=ret["us"]), indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("sim", "screen", "route", "congestion", "record"))
    ap.add_argument("--work", required=True)
    ap.add_argument("--util", type=float, default=30)
    ap.add_argument("--density", type=float, default=0.55)
    ap.add_argument("--tag", default="r1")
    ap.add_argument("--halo", type=float, default=5, help="macro placement halo (um)")
    ap.add_argument("--config", default="hard", choices=sorted(ROUTES))
    a = ap.parse_args()
    {"sim": cmd_sim, "screen": cmd_screen, "route": cmd_route, "congestion": cmd_congestion,
     "record": cmd_record}[a.cmd](a)


if __name__ == "__main__":
    main()
