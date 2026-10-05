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
                          drc=(ph.get("place_and_route") or {}).get("drc_errors"),
                          physical_summary={k: v for k, v in (ph.get("place_and_route") or {}).items()
                                            if not isinstance(v, (dict, list)) or k == "memory_macros"})
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
        command="python3 tools/dsrom_hop_closed.py " + " ".join(sys.argv[1:]))
    (REC / "levers/hop_closed.json").write_text(json.dumps(lever, indent=1, default=str) + "\n")
    print(json.dumps(dict(verdict=verdict, exact=exact, pre=(pre["ss_setup_wns_ps"], pre["ff_hold_wns_ps"]),
                          routed={nm: (r["ss_setup_wns_ps"], r["ff_hold_wns_ps"]) for nm, r in routes.items()}, hop=hop["us"], draft=draft["us"], ret=ret["us"]), indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("sim", "screen", "route", "record"))
    ap.add_argument("--work", required=True)
    ap.add_argument("--util", type=float, default=30)
    ap.add_argument("--density", type=float, default=0.55)
    ap.add_argument("--tag", default="r1")
    ap.add_argument("--halo", type=float, default=5, help="macro placement halo (um)")
    ap.add_argument("--config", default="hard", choices=sorted(ROUTES))
    a = ap.parse_args()
    {"sim": cmd_sim, "screen": cmd_screen, "route": cmd_route, "record": cmd_record}[a.cmd](a)


if __name__ == "__main__":
    main()
