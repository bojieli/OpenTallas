#!/usr/bin/env python3
"""DS-ROM recovery lever "hop": the S81 stage hop through the successor link endpoint ot_dsrom_link_ct.

The measured S81 hop (tools/dsrom_1m_links.py, results/rtl/dsrom_1m_allmeasured_20261004/links.json) pushes the whole
40,976-B residual through ONE 64-B/cycle ot_dsrom_link_rt endpoint (76.8 GB/s): 640 of its 909 cycles are endpoint
serialisation.  The committed lane split gives each die of a 2-die package 7 stage lanes each way
(results/arch/v41_rack.json lanes: stage_out 14 / stage_in 14 per package, R-L9; v41_rack_design.hop_link_bytes: "each
die needs the whole residual; half arrives on its 7 cable lanes and the rest crosses UCIe from its package peer").
The successor:
  * per-die halves: source die d sends half d of the residual on its own 7 lanes to destination die d, which forwards
    it cut-through over in-package UCIe to its peer (rtl/test/dsrom_sys/tb_dsrom_1m_hop_ct.sv);
  * ot_dsrom_link_ct (rtl/dsrom_sys/ot_dsrom_link_ct.sv): 96-B flits (115.2 GB/s endpoint) paced IN RTL to the
    lane rate, 7 x 13.176 GB/s = 92.24 GB/s = 3920/51 B per 1.2 GHz cycle, so the PHY lanes bind and the
    serialisation is simulated, not added; registered (SRAM-compatible) replay read; pipelined receive CRC check.
Unchanged: the light-FEC PHY vendor budget (130 ns = 156 cycles, delay line), the UCIe leg (10 - 1.5 ns = 11 cycles),
2 x 45 routed SerDes wire stages, the payload bytes (h [4,5120] BF16 + pre [4] FP32 = 40,976 B, replicated per rank:
every destination die needs all of it).

Subcommands (heavy ones run on the compute host):
  sim     Icarus runs of tb_dsrom_1m_hop_ct -> <work>/hop_ct.json
  screen  pre-layout SS/FF screen of ot_dsrom_link_ct (tools/dsrom_reindex_screen.py) -> <work>/screen_*/screen.json
  record  results/rtl/dsrom_recovery_20261004/hop/hop_ct.json + levers/hop.json (needs a composition run for the
          per-user gain; see --gate)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/rtl/dsrom_recovery_20261004"
LINKS = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004/links.json"
RACK = ROOT / "results/arch/v41_rack.json"

CLK = 1.2e9
LFEC_NS, KP4_NS, UCIE_NS = 130.0, 209.0, 10.0 - 1.5          # as tools/dsrom_1m_links.py
SERDES_STAGES = 45
RESIDUAL_B, RETURN_B, RETURN_TRAVERSALS = 40976, 8, 8
DRAFT_B = 5 * RESIDUAL_B          # DSpark draft: one 5-row stage hop into each of the 3 draft blocks
FB = 96


def cyc(ns):
    return math.ceil(ns * CLK * 1e-9 - 1e-9)


CH_LFEC, CH_KP4, CH_UCIE = cyc(LFEC_NS), cyc(KP4_NS), cyc(UCIE_NS)


def lanes():
    r = json.loads(RACK.read_text())["lanes"]
    per_die = r["per_package"]["stage_out"] // 2
    assert per_die * 2 == r["per_package"]["stage_in"]
    # 112G PAM4 lane, light FEC RS(272,257) + 256b/257b: 112e9 x 256/272 / 8 B/s (= results/arch/v41_rack.json value)
    lane = Fraction(112 * 10 ** 9 * 256, 272 * 8)
    assert abs(float(lane) - r["lane_net_Bps"]) < 1e-3, (float(lane), r["lane_net_Bps"])
    bpc = per_die * lane / Fraction(int(CLK))
    return dict(per_die=per_die, per_package=r["per_package"], total=r["total"], available=r["available"],
                lane_net_Bps=float(lane), die_Bps=float(per_die * lane), bytes_per_cycle=bpc)


RTL = ["rtl/test/dsrom_sys/tb_dsrom_1m_hop_ct.sv", "rtl/dsrom_sys/ot_dsrom_link_ct.sv",
       "rtl/dsrom_sys/ot_dsrom_link_chan.sv", "rtl/link/ot_link_crc32.sv"]


def cases():
    L = lanes()
    pn, pd = L["bytes_per_cycle"].numerator, L["bytes_per_cycle"].denominator
    base = dict(FB=FB, CH=CH_LFEC, CHU=CH_UCIE, CRED=256, SEQW=9, CREDU=64, SEQWU=8, PNUM=pn, PDEN=pd, MODE=1)
    return [
        ("hop_ct_halves", base, RESIDUAL_B,
         "HEADLINE stage hop: per-die halves on 7 paced lanes each + cut-through UCIe exchange"),
        ("hop_ct_halves_err", dict(base, ERRF=37, ERRR=29), RESIDUAL_B,
         "exactness under errors: forward bit flip every 37th frame, reverse every 29th (go-back-N replays through "
         "the registered replay read, paced)"),
        ("ret_ct_flit", dict(base, MODE=0), RETURN_B, "HEADLINE token return: one 8-B flit, one board traversal"),
        ("hop_ct_halves_kp4", dict(base, CH=CH_KP4), RESIDUAL_B, "sensitivity: 209 ns full-KP4 cable tier"),
        ("hop_ct_halves_draft5", dict(base, CRED=512, SEQW=10), DRAFT_B,
         "DSpark draft 5-row hop (204,880 B), receive buffer 512 flits so credits do not bind"),
        ("hop_ct_halves_fb64", dict(base, FB=64, PNUM=0, PDEN=1), RESIDUAL_B,
         "ablation: halves with the 64-B endpoint unpaced (76.8 GB/s, just under the 92.2 GB/s lanes)"),
    ]


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_case(work: Path, case):
    name, defs, nbytes, role = case
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
    return dict(case=name, role=role, defines=defs, bytes=nbytes, summary=m.group(0), fields=f,
                mismatch_lines=[l for l in r.stdout.splitlines() if l.startswith("MISMATCH")][:5],
                exact=f["result"] == "PASS")


def cmd_sim(a):
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    runs = {c[0]: run_case(work, c) for c in cases()}
    for r in runs.values():
        print(r["summary"], flush=True)
    out = dict(simulator=subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0],
               runs=runs, sources={p: sha(ROOT / p) for p in RTL + ["tools/dsrom_recovery_hop.py"]},
               generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    (work / "hop_ct.json").write_text(json.dumps(out, indent=1) + "\n")


SCREENS = {
    # the S81 board-leg endpoint at the screened storage depth (CREDITS 16): the replay buffer and the receive FIFO
    # are registered-read arrays, SRAM macros at the S81 depth (256 x 96 B); CHANNEL_CYCLES 1 (the delay line is the
    # PHY stand-in, not endpoint logic)
    "board": dict(FLIT_BYTES=FB, TX_STAGES=2, CHANNEL_CYCLES=1, RX_STAGES=2, CREDITS=16, SEQW=5, KEEPALIVE=16),
}


def cmd_screen(a):
    L = lanes()
    work = Path(a.work)
    for nm, p in SCREENS.items():
        p = dict(p, PHY_NUM=L["bytes_per_cycle"].numerator, PHY_DEN=L["bytes_per_cycle"].denominator)
        args = [sys.executable, str(ROOT / "tools/dsrom_reindex_screen.py"), "--top", "ot_dsrom_link_ct",
                "--period-ps", "833", "--work", str(work / f"screen_{nm}")]
        for s in RTL[1:]:
            args += ["--source", s]
        for k, v in p.items():
            args += ["--param", f"{k}={v}"]
        subprocess.run(args, check=True, cwd=ROOT)


def hop_row(r, ch, chu):
    f = r["fields"]
    wire = 2 * SERDES_STAGES
    total = f["last_flit"] + wire
    return dict(exact=r["exact"], payload_B=r["bytes"], half_B=[f["half_a"], f["half_b"]],
                flit_bytes=f["fb"], flits_per_half=[f["flits_a"], f["flits_b"]],
                link_ct_first_to_last_cycles=f["last_flit"], first_flit_cycles=f["first_flit"],
                own_half_last_flit_cycles=f["own_last_flit"], peer_half_last_flit_cycles=f["peer_last_flit"],
                vendor_channel_cycles=dict(board=ch, ucie_fanout=chu),
                measured_endpoint_cycles=f["last_flit"] - ch - chu,
                in_ready_stalls=f["credit_stalls"], wire_stage_cycles=wire, total_cycles=total,
                us=round(total / CLK * 1e6, 4))


def cmd_record(a):
    work = Path(a.work)
    sim = json.loads((work / "hop_ct.json").read_text())
    runs = sim["runs"]
    L = lanes()
    hop = hop_row(runs["hop_ct_halves"], CH_LFEC, CH_UCIE)
    kp4 = hop_row(runs["hop_ct_halves_kp4"], CH_KP4, CH_UCIE)
    fb64 = hop_row(runs["hop_ct_halves_fb64"], CH_LFEC, CH_UCIE)
    err = hop_row(runs["hop_ct_halves_err"], CH_LFEC, CH_UCIE)
    draft = hop_row(runs["hop_ct_halves_draft5"], CH_LFEC, CH_UCIE) if "hop_ct_halves_draft5" in runs else None
    rf = runs["ret_ct_flit"]["fields"]
    ret_cyc = RETURN_TRAVERSALS * rf["first_flit"] + 2 * SERDES_STAGES
    ret = dict(exact=runs["ret_ct_flit"]["exact"], per_traversal_cycles=rf["first_flit"],
               measured_endpoint_cycles_per_traversal=rf["first_flit"] - CH_LFEC, traversals=RETURN_TRAVERSALS,
               wire_stage_cycles=2 * SERDES_STAGES, total_cycles=ret_cyc, us=round(ret_cyc / CLK * 1e6, 4))
    old = json.loads(LINKS.read_text())["hop"]
    scr = {}
    for nm in SCREENS:
        p = work / f"screen_{nm}/screen.json"
        if p.is_file():
            scr[nm] = json.loads(p.read_text())
    bp = work / "screen_base_rt/screen.json"
    base_scr = json.loads(bp.read_text()) if bp.is_file() else None
    ss = min((s["ss_setup_wns_ps"] for s in scr.values() if s.get("ss_setup_wns_ps") is not None), default=None)
    ff = min((s["ff_hold_wns_ps"] for s in scr.values() if s.get("ff_hold_wns_ps") is not None), default=None)
    closes = ss is not None and ff is not None and ss >= 0 and ff >= 0
    exact = all(r["exact"] for r in runs.values())
    ser_ns = L["die_Bps"] and (math.ceil(RESIDUAL_B / 2) / L["die_Bps"] * 1e9)
    detail = dict(
        schema="opentallas.dsrom-recovery.hop.v1",
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        scope="DS-ROM S81 stage hop and token return through the successor endpoint ot_dsrom_link_ct (lever hop of "
              "the 2026-10-04 recovery), Icarus at 1.2 GHz, the 40,976-B residual at position 1,048,575 (shape-only: "
              "the hop is data-independent; payload words hashed, compared bit-exact per die)",
        lane_assumption=dict(
            lanes_per_die_each_way=L["per_die"], package_lanes=L["per_package"], package_lane_total=L["total"],
            package_lane_budget=L["available"], lane_net_Bps=L["lane_net_Bps"], die_stage_Bps=L["die_Bps"],
            pacer_bytes_per_cycle=f"{L['bytes_per_cycle'].numerator}/{L['bytes_per_cycle'].denominator}",
            pacer_bytes_per_cycle_float=float(L["bytes_per_cycle"]),
            half_serialisation_ns_at_lane_rate=round(ser_ns, 2),
            basis="results/arch/v41_rack.json lanes (R-L9 split of the 90-lane 2-die package edge, "
                  "technology.json rom_board_serdes sqrt(dies/4) x 128 lanes): stage_out 14 + stage_in 14 per "
                  "package = 7 per die each way; 112G PAM4 lanes, light-FEC RS(272,257) + 256b/257b = 13.176 GB/s net "
                  "(the lane_net_Bps of that record); per-die halves as v41_rack_design.hop_link_bytes.  No added "
                  "lanes: the lever moves the residual from one die's endpoint onto both dies' already-budgeted "
                  "stage lanes and matches the endpoint to their rate.",
            not_used="links.json phy_lane_rate 171.29 GB/s is the 13-lane TP budget per die pair, not stage lanes"),
        hop=hop, hop_kp4_sensitivity=kp4, hop_fb64_ablation=fb64, hop_error_injection=err, token_return=ret,
        draft_hop_5row=draft,
        old=dict(per_hop_us=old["per_hop_us"], total_cycles=old["total_cycles"],
                 measured_endpoint_cycles=old["measured_endpoint_cycles"],
                 token_return_us=old["token_return_us"], source=str(LINKS.relative_to(ROOT))),
        screen=dict(runs=scr, ss_setup_wns_ps=ss, ff_hold_wns_ps=ff, closes=closes,
                    baseline_link_rt_same_screen=base_scr,
                    baseline_note="context only: the pinned ot_dsrom_link_rt (FLIT_BYTES 64, CREDITS 16) through the "
                                  "same screen; the measured S81 hop (links.json) uses it unscreened",
                    configs={k: v for k, v in SCREENS.items()}),
        runs=runs, simulator=sim["simulator"], sources=sim["sources"],
        pinned_unchanged={p: sha(ROOT / p) for p in ("rtl/dsrom_sys/ot_dsrom_link_rt.sv",
                                                    "rtl/test/dsrom_sys/tb_dsrom_1m_hop.sv")})
    (REC / "hop").mkdir(parents=True, exist_ok=True)
    (REC / "hop/hop_ct.json").write_text(json.dumps(detail, indent=1, default=str) + "\n")
    gate = json.loads(Path(a.gate).read_text()) if a.gate else None
    verdict = "ADOPT" if exact and closes and (gate is None or gate["ar_gain"] >= 0.01) else "REJECT"
    reasons = ([] if exact else ["not exact"]) + ([] if closes else [
        f"SS/FF screen fails at 1.2 GHz: SS setup WNS {ss} ps (>= 0 required at 60 ps), FF hold WNS {ff} ps"]) + (
        [] if gate is None or gate["ar_gain"] >= 0.01 else [f"AR gain {gate['ar_gain']:.4f} < 1%"])
    lever = dict(
        schema="opentallas.dsrom-recovery.lever.v1", lever="hop", verdict=verdict, exact=exact,
        ss_ff=dict(ss_setup_wns_ps=ss, ff_hold_wns_ps=ff, period_ps=833, setup_uncertainty_ps=60,
                   hold_uncertainty_ps=25, closes=closes,
                   basis="pre-layout ORFS yosys/abc CORNER=WC (ADDER_MAP_FILE off), OpenSTA ASAP7 RVT SS setup / FF "
                         "hold, ideal clock, I/O false-pathed (tools/dsrom_reindex_screen.py); ot_dsrom_link_ct "
                         "FLIT_BYTES 96, paced, storage depth 16 (registered-read arrays; SRAM at the S81 depth 256)"),
        info=dict(hop_us=hop["us"],
                  hop_source=f"ot_dsrom_link_ct RTL {hop['measured_endpoint_cycles']} cyc (per-die halves of 40,976 B, "
                             f"96-B flits paced to 7 x 13.18 GB/s lanes, cut-through UCIe exchange) + light-FEC PHY "
                             f"VENDOR BUDGET 130 ns + UCIe 10 ns + 2x45 routed wire stages",
                  hop_cls="measured+vendor_phy",
                  **(dict(draft_hop_us=draft["us"],
                          draft_hop_source=f"ot_dsrom_link_ct RTL, 5-row 204,880 B per-die halves "
                                           f"({draft['total_cycles']} cyc incl. light-FEC 156 + UCIe 11 + 90 wire), "
                                           f"tb_dsrom_1m_hop_ct case hop_ct_halves_draft5; was 2.89 us on "
                                           f"ot_dsrom_link_rt") if draft else {})),
        nodes={"token.return": dict(us=ret["us"], cls="measured+vendor_phy",
                                    source=f"token return: {RETURN_TRAVERSALS} x (ot_dsrom_link_ct "
                                           f"{ret['measured_endpoint_cycles_per_traversal']} cyc + light-FEC VENDOR "
                                           f"BUDGET {CH_LFEC} cyc) + 90 wire")},
        reject_reasons=reasons,
        worst_paths_ss_ps={nm: s.get("worst_slack_by_stage_ps") for nm, s in scr.items()},
        old_hop_us=old["per_hop_us"], new_hop_us=hop["us"], old_hop_cycles=old["total_cycles"],
        new_hop_cycles=hop["total_cycles"], gate=gate, detail=str((REC / "hop/hop_ct.json").relative_to(ROOT)),
        rtl=dict(endpoint="rtl/dsrom_sys/ot_dsrom_link_ct.sv", bench="rtl/test/dsrom_sys/tb_dsrom_1m_hop_ct.sv",
                 pinned_byte_identical="rtl/dsrom_sys/ot_dsrom_link_rt.sv"),
        command="python3 tools/dsrom_recovery_hop.py " + " ".join(sys.argv[1:]))
    (REC / "levers").mkdir(parents=True, exist_ok=True)
    (REC / "levers/hop.json").write_text(json.dumps(lever, indent=1, default=str) + "\n")
    print(json.dumps(dict(verdict=verdict, exact=exact, ss=ss, ff=ff, old=old["per_hop_us"], new=hop["us"],
                          ret=ret["us"]), indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("sim", "screen", "record"))
    ap.add_argument("--work", required=True)
    ap.add_argument("--gate", default="", help="JSON with ar_gain (fraction) from the recovery composition")
    a = ap.parse_args()
    {"sim": cmd_sim, "screen": cmd_screen, "record": cmd_record}[a.cmd](a)


if __name__ == "__main__":
    main()
