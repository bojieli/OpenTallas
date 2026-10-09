#!/usr/bin/env python3
"""DS ROM pipelined verify on TWO consecutive stages with the CLOSED wavefront controller (mtp-exact, 2026-10-08).

The minimum vehicle that contains the wavefront's stage-to-stage mechanism: the reduced V4.1 vehicle split
[0..18][19][20][21..39]; packages 1 (layer 19) and 2 (layer 20: CSA producer + index scan), each an all-unit
ot_hdc_core_v41x with KV / index keys in modelled HBM and its package controller, joined by the real
ot_rom_pkg_link.  The controller is the CLOSED ot_rom_pkg_ctrl_wfc (sha d47c1759, the src r24 / stg r11 routes:
results/rtl/dsrom_wfc_split_20261006/closure.json) with the closed element's defines, compiled under the bench's
module name (a renamed copy made in the run directory; the pinned source is unchanged).

The bench (rtl/test/dsrom_wavefront/tb_dsrom_wavefront_array.sv STAGE_BENCH, generalised here to NODES = 2 by a
patched copy in the run directory: injector on package 0's inbound link, p2p link 0 -> 1, checking sink on package
1's outbound link) feeds the HIDDEN messages of positions 0, 1, 2, 3 (corrupted input token: a rejected draft),
3 (re-issue with the clean token: the squash rewinds BOTH stages), 4, back to back: the two stages work on
consecutive positions at the same time (the wavefront).  Checks, bit for bit: every outbound flit of the second
stage against the ISA pipeline, and the final KV / persistent vector memory of BOTH packages against the ISA after
the CLEAN sequence (dead rows of the squashed position rewritten before any read).  WAVE = 0 builds are the
negative control (a rewind latches proto_fault).

    python3 tools/mtp_exact_wavefront2.py prepare --scratch S --gold D/golden.json    # GPU host (ISA replay)
    python3 tools/mtp_exact_wavefront2.py run --scratch S [--wave 1] [--ctrl wfc|wf]    # EPYC (Verilator)
    python3 tools/mtp_exact_wavefront2.py record --scratch S --output R.json
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_wavefront_rtl_campaign as W  # noqa: E402  (array campaign flags, ISA pipeline, images)

A, P, I, V, G, AC, np = W.A, W.P, W.I, W.V, W.G, W.AC, W.np
SOURCE_LAYER = 19
BODY2 = lambda L: [list(range(SOURCE_LAYER)), [SOURCE_LAYER], [SOURCE_LAYER + 1],
                   list(range(SOURCE_LAYER + 2, L))]
KS = (1, 2)
BAD = 3
ORDER, CFG = "basic", "cfg_stage2"
WFC = ROOT / "rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv"
WFC_SHA = "d47c17591d61d42d300d928820ebd15d78079a44851b8f6d48ec6243ed92f7d8"
# the closed stg r11 element's knobs (results/rtl/dsrom_wfc_split_20261006/stage/stage_w1_r11.json)
WFC_DEFINES = ["OT_WFC_CONTROL_PIPE=1", "OT_WFC_UPOS_LWR=1", "OT_WFC_PRECOMP=1", "OT_WFC_CFG_Q=1", "OT_WFC_IN_DEC=1",
               "OT_WFC_TXQ_SLICE=1", "OT_WFC_RDY_LT=1", "OT_WFC_FANOUT_COPY=1", "OT_WFC_MARGIN=1",
               "OT_WFC_LINK_REG=1", "OT_WFC_VM_REG=1", "OT_WFC_SLEW_COPY=1", "OT_WFC_LINK_SEL=1"]


class _Stages:
    """config_svh view of consecutive packages KS of a plan as NODES = len(KS) (the last sends to the sink)."""
    def __init__(self, plan, ks):
        self.p, self.ks = plan, ks
        self.n, self.nb, self.hp, self.side, self.head_mcast = len(ks), len(ks), 0, {}, False
        self.vocab, self.pb = plan.vocab, plan.pb

    def role(self, i):
        r = dict(self.p.role(self.ks[i]))
        r["hid_dest"] = i + 1
        return r

    def ehash(self, i):
        return self.p.ehash(self.ks[i])

    def result_parts(self):
        return 1


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prepare(scratch: Path, gold_from: Path):
    t0 = time.time()
    scratch.mkdir(parents=True, exist_ok=True)
    model = V.Model()
    lay = P.Layout(model, rollback_ring=(ORDER == "deep"))
    A.place_head_parts(lay)
    roms = scratch / "roms"
    if not (roms / "hbm_q.hex").exists():
        A.write_roms(roms, lay)
        W.ximg.write_banked(roms / "hbank.hex", W.ximg.hbank_image(lay, 8), 32, 8)
        W.ximg.write(roms, lay, hhw=8, mg=8)
        sectors, _ = P.qe_hbm_image(lay)
        (roms / "hbm_q.hex").write_text(P.hexwords(sectors, P.QSEC))
    base = P.Machine(lay, np.zeros(I.KV_WORDS * I.W_LANES, dtype=np.float32), np.zeros(I.VM_ELEMS, dtype=np.float32))
    plan = A.Plan(lay, BODY2(model.L), 0, False, "relay")
    progs = [A.StageBuilder(plan.lay, qchunk=P.QCHUNK).stage(plan, k) for k in range(plan.n)]
    r0, r1 = plan.role(KS[0]), plan.role(KS[1])
    assert r0["txw"] == r1["rxw"], (r0["txw"], r1["rxw"])
    if gold_from:
        seq = json.loads(gold_from.read_text())["seq"]
    else:   # the clean greedy sequence of the wavefront campaign's prompt (its golden.json "seq")
        seq = [s["input"] for s in W.golden(model, A.prompts(W.PLEN)[0], W.STEPS, W.PLEN)]
        (scratch / "golden_seq.json").write_text(json.dumps(seq) + "\n")
    bad = (seq[BAD] + 1) % plan.vocab
    if ORDER == "deep":
        # MR-5 worst case: the rejected position's successors are already in the pipeline (issued on the corrupted
        # context) when the rejection lands; they are squashed and re-issued after the corrected position
        # gamma=5: all five successors may have executed before acceptance reaches the stage.
        jobs = [(seq[p], p) for p in range(BAD)] + [(bad, BAD)] + \
               [(seq[p], p) for p in range(BAD + 1, BAD + 6)] + \
               [(seq[p], p) for p in range(BAD, 12)]
        clean_n = 12
    else:
        jobs = [(seq[0], 0), (seq[1], 1), (seq[2], 2), (bad, BAD), (seq[3], 3), (seq[4], 4)]
        clean_n = 5

    def replay(order, capture):
        pipe = A.Pipeline(plan, progs, base)
        inj, exo = [], []
        for tok, pos in order:
            for mc in pipe.pk:
                mc.tokens = mc.tokens[:pos]
            pipe.pk[0].run(progs[0], tok, pos)
            pipe.hop(0, KS[0])
            if capture:
                inj.append([(0, W._hdr(pos, r0["rxw"], tok))] +
                           [(int(i == r0["rxw"] - 1), f) for i, f in
                            enumerate(W._flits(pipe.pk[KS[0]].vm, r0["rxb"], r0["rxw"]))])
            pipe.pk[KS[0]].run(progs[KS[0]], tok, pos)
            pipe.hop(KS[0], KS[1])
            pipe.pk[KS[1]].run(progs[KS[1]], tok, pos)
            if capture:
                exo.append([(0, W._hdr(pos, r1["txw"], tok))] +
                           [(int(i == r1["txw"] - 1), f) for i, f in
                            enumerate(W._flits(pipe.pk[KS[1]].vm, r1["txb"], r1["txw"]))])
        return inj, exo, [(pipe.pk[k].kv.copy(), pipe.pk[k].vm[plan.pb:plan.pb + A.PS].copy()) for k in KS]

    inj, exo, st = replay(jobs, True)
    _, _, st_clean = replay([(seq[p], p) for p in range(clean_n)], False)
    same = all(np.array_equal(G.bits(a[0]), G.bits(b[0])) and np.array_equal(G.bits(a[1]), G.bits(b[1]))
               for a, b in zip(st, st_clean))
    if not same:
        raise RuntimeError("2-stage ISA: squash + re-issue does not restore the clean state")
    img = scratch / CFG
    img.mkdir(parents=True, exist_ok=True)
    sectors, firsts = P.qe_hbm_image(lay)
    for i, k in enumerate(KS):
        words = [I.encode(**{a: v for a, v in f.items() if not a.startswith("_")}) for f in progs[k]]
        (img / f"prog_stage{i:02d}.hex").write_text(P.hexwords(words, I.INSTR_BITS))
        (img / f"qlist_stage{i:02d}.hex").write_text(P.hexwords(P.encode_list(P.qe_fetch_list(lay, progs[k], firsts)),
                                                                P.LIST_BITS))
        (img / f"expect_kv{i:02d}_0.hex").write_text(P.hexwords(G.bits(st[i][0]), 32))
        (img / f"expect_vm{i:02d}_0.hex").write_text(P.hexwords(G.bits(st[i][1]), 32))
    flat = lambda msgs: [(l << 512) | f for m in msgs for l, f in m]
    # bit 513: entry valid (an all-zero payload flit -- e.g. layer 19's empty relay words at position 0 -- is data,
    # not the pinned bench's zero end-of-list marker)
    (img / "inject.hex").write_text(P.hexwords([(1 << 513) | w for w in flat(inj)], 514))
    (img / "expect_out.hex").write_text(P.hexwords(flat(exo), 513))
    (img / "known.hex").write_text(P.hexwords([0] * (W.NBLK * W.KMAX), 17))
    (img / "expect_tokens.hex").write_text(P.hexwords([0] * W.SMAX, 16))
    (img / "expect_logits.hex").write_text(P.hexwords([0] * (2 * W.SMAX * plan.vocab), 32))
    svh = AC.config_svh(_Stages(plan, KS), lay, "p2p").replace("NPR = 2", "NPR = 1")
    (scratch / "stage2_cfg.svh").write_text(svh)
    prep_name = "prepare_stage2.json" if ORDER == "basic" else f"prepare_stage2_{ORDER}.json"
    prep = dict(schema="opentallas.rtl.mtp_exact_wavefront2_prepare.v1", layers=[plan.body[k] for k in KS],
                packages=list(KS), hop_words=r0["txw"], rxw=r0["rxw"], txw=r1["txw"],
                jobs=[(int(t), p) for t, p in jobs], corrupted_position=BAD, corrupted_token=bad,
                clean_token=seq[BAD], isa_squash_reissue_state_equals_clean_both_stages=same,
                program_instructions=[len(progs[k]) for k in KS], prepare_seconds=round(time.time() - t0, 1),
                input_sha256={str(p_.relative_to(ROOT)): sha(p_) for p_ in [*W.sources(), Path(__file__)]})
    prep["order"] = ORDER
    prep["compressor_ring_records"] = lay.ring
    prep["rollback_storage_delta_bytes_per_package"] = 4 * (lay.ring - 2) * 64 * 4
    prep["rollback_added_isa_instructions"] = 0
    (scratch / prep_name).write_text(json.dumps(prep, indent=1) + "\n")
    print(json.dumps({x: prep[x] for x in ("layers", "rxw", "txw", "jobs",
                                           "isa_squash_reissue_state_equals_clean_both_stages")}))
    return prep


def bench_copy(run: Path) -> Path:
    """tb_dsrom_wavefront_array.sv with STAGE_BENCH generalised to NODES >= 1 (inject at package 0, link n -> n+1,
    sink at package NODES-1).  NODES = 1 is the pinned bench's behaviour."""
    src = W.TB.read_text()
    old_inj = "            reg [FLIT:0] inj [0:INJ_MAX-1];           // {last, flit}; a zero entry ends the list\n"
    new_inj = "            reg [FLIT+1:0] inj [0:INJ_MAX-1];         // {valid, last, flit} (mtp-exact: explicit valid)\n"
    assert src.count(old_inj) == 1
    src = src.replace(old_inj, new_inj)
    old_ports = """            assign rx_v[0] = rst_n && inj[ip] != 0;
            assign rx_d[0 +: FLIT] = inj[ip][FLIT-1:0];
            assign rx_l[0] = inj[ip][FLIT];
            assign tx_r[0] = 1'b1;
"""
    new_ports = """            localparam integer SK = NODES - 1;     // mtp-exact: the sink is the LAST package
            assign rx_v[0] = rst_n && inj[ip][FLIT+1];
            assign rx_d[0 +: FLIT] = inj[ip][FLIT-1:0];
            assign rx_l[0] = inj[ip][FLIT];
            assign tx_r[SK] = 1'b1;
            for (n = 0; n < NODES - 1; n = n + 1) begin : g_slink
                ot_rom_pkg_link #(.FLIT_BYTES(FLIT / 8), .TX_STAGES(2), .CHANNEL_CYCLES(LINK_CH_MAX), .RX_STAGES(2),
                                  .CREDITS(32), .DYNAMIC_DELAY(FABRIC)) u_link (
                    .clk(clk), .rst_n(rst_n),
                    .channel_cycles(link_ch[15:0]),
                    .in_valid(tx_v[n]), .in_ready(tx_r[n]), .in_data(tx_d[n*FLIT +: FLIT]), .in_last(tx_l[n]),
                    .out_valid(rx_v[n + 1]), .out_ready(rx_r[n + 1]), .out_data(rx_d[(n + 1)*FLIT +: FLIT]),
                    .out_last(rx_l[n + 1]), .credit_stalls());
            end
"""
    old_sink = """                if (tx_v[0]) begin
                    // header flit: type and position; payload flits: every bit
                    if (exo[op][FLIT-1:0] !== tx_d[FLIT-1:0] &&
                        !(exo[op][FLIT] == 1'b0 && op_hdr &&
                          exo[op][16 +: 4] == tx_d[16 +: 4] && exo[op][40 +: 16] == tx_d[40 +: 16])) begin"""
    new_sink = """                if (tx_v[SK]) begin
                    // header flit: type and position; payload flits: every bit
                    if (exo[op][FLIT-1:0] !== tx_d[SK*FLIT +: FLIT] &&
                        !(exo[op][FLIT] == 1'b0 && op_hdr &&
                          exo[op][16 +: 4] == tx_d[SK*FLIT + 16 +: 4] && exo[op][40 +: 16] == tx_d[SK*FLIT + 40 +: 16])) begin"""
    old_last = """                    op_hdr <= tx_l[0];
                    if (tx_l[0]) begin"""
    new_last = """                    op_hdr <= tx_l[SK];
                    if (tx_l[SK]) begin"""
    for o, n_ in ((old_ports, new_ports), (old_sink, new_sink), (old_last, new_last)):
        assert src.count(o) == 1, "bench changed: re-anchor tools/mtp_exact_wavefront2.py"
        src = src.replace(o, n_)
    out = run / "tb_dsrom_wavefront_array_stage2.sv"
    out.write_text(src)
    return out


def ctrl_copy(run: Path) -> Path:
    """The closed WFC under the bench's controller module name (ot_rom_pkg_ctrl_wf)."""
    assert sha(WFC) == WFC_SHA, "ot_rom_pkg_ctrl_wfc.sv is not the closed source"
    src = WFC.read_text()
    assert src.count("module ot_rom_pkg_ctrl_wfc #(") == 1
    out = run / "ot_rom_pkg_ctrl_wfc_as_wf.sv"
    out.write_text(src.replace("module ot_rom_pkg_ctrl_wfc #(", "module ot_rom_pkg_ctrl_wf #("))
    return out


def run(scratch: Path, wave: int, ctrl: str, jobs: int):
    tag = f"stage2_{ctrl}_w{wave}" + ("" if ORDER == "basic" else f"_{ORDER}")
    obj = scratch / f"obj_{tag}"
    obj.mkdir(parents=True, exist_ok=True)
    (obj / "v41_array_cfg.svh").write_text((scratch / "stage2_cfg.svh").read_text())
    tb = bench_copy(obj)
    cfile = ctrl_copy(obj) if ctrl == "wfc" else W.CTRL
    defs = WFC_DEFINES if ctrl == "wfc" else []
    core = W.core
    cmd = ["verilator", "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
           "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "-Wno-MULTIDRIVEN", "-Wno-TIMESCALEMOD",
           "-Wno-MODDUP", "-Wno-VARHIDDEN", "-Wno-UNOPTFLAT", "-Wno-PINMISSING",
           "--top-module", "tb_dsrom_wavefront_array", "-GUSERS=1", "-GSTALL=0", f"-GWAVE={wave}", f"-GWIN={W.WIN}",
           "-GSTAGE_BENCH=1", "-Mdir", str(obj), f"-I{obj}", f"-I{core.SVH.parent}", str(core.VLT),
           f"+define+HDC_SW={I.SU_LANES}",
           *[f"+define+HDC_X_{x}={2 if x == 'IDX' else 1}" for x in ("HE", "ME", "ATT", "IDX", "SEL", "EG", "SU")],
           "+define+HDC_W_HBM=1", "+define+HDC_KV_HBM=1", *[f"+define+{d}" for d in defs],
           *map(str, core.rtl_sources(True)), *map(str, AC.BENCH_AUX_RTL), *map(str, AC.KV_HBM_RTL),
           str(AC.LINK), str(AC.ROUTER), str(cfile), str(tb), str(W.HARNESS),
           "-CFLAGS", "-O1", "-MAKEFLAGS", "OPT_FAST=-O1 OPT_GLOBAL=-O1", "-j", str(jobs)]
    (obj / "build_cmd.json").write_text(json.dumps(cmd))
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    (obj / "build.log").write_text(r.stdout[-200000:] + r.stderr[-200000:])
    if r.returncode:
        raise SystemExit(f"build failed: {obj / 'build.log'}")
    bsec = time.time() - t0
    pn = "prepare_stage2.json" if ORDER == "basic" else f"prepare_stage2_{ORDER}.json"
    n_out = len(json.loads((scratch / pn).read_text())["jobs"])
    log = scratch / f"out_{tag}.txt"
    t0 = time.time()
    with open(log, "w") as fh:
        rc = subprocess.run(["stdbuf", "-oL", str(obj / "Vtb_dsrom_wavefront_array"), f"+DIR={scratch / CFG}",
                             f"+ROMS={scratch / 'roms'}", "+NUSERS=1", f"+NOUT={n_out}", "+HB=1000000"],
                            stdout=fh, stderr=subprocess.STDOUT).returncode
    (scratch / f"run_{tag}.json").write_text(json.dumps(dict(rc=rc, build_seconds=round(bsec, 1),
                                                             sim_seconds=round(time.time() - t0, 1), ctrl=ctrl,
                                                             wave=wave, defines=defs, tb_sha256=sha(tb),
                                                             ctrl_sha256=sha(cfile))) + "\n")
    return rc


JOB = re.compile(r"JOB node=(\d+) user=(\d+) pos=(\d+) hdr=(\d+) pay=(\d+) cstart=(\d+) start=(\d+) done=(\d+)")
OUT = re.compile(r"OUT msg=(\d+) cycle=(\d+)")


def analyse(text):
    jobs = [dict(zip(("node", "user", "pos", "hdr", "pay", "cstart", "start", "done"), map(int, m.groups())))
            for m in JOB.finditer(text)]
    outs = [int(m.group(2)) for m in OUT.finditer(text)]
    st = re.search(r"STAGE_OUT msgs=(\d+) out_mismatch=(\d+)", text)
    arr = re.search(r"HDC41_ARRAY .* mismatches=(\d+) logit_mismatch=(\d+) .* state_mismatch=(\d+) total_cycles=(\d+)", text)
    rec = dict(passed="\nPASS" in text, jobs=jobs, out_cycles=outs,
               out_msgs=int(st.group(1)) if st else None, out_mismatch=int(st.group(2)) if st else None,
               mismatches=int(arr.group(1)) if arr else None, state_mismatch=int(arr.group(3)) if arr else None,
               total_cycles=int(arr.group(4)) if arr else None,
               proto_fault=("protocol=" in text and "protocol=00" not in text and "FAULT" in text))
    by = {0: [j for j in jobs if j["node"] == 0], 1: [j for j in jobs if j["node"] == 1]}
    rec["per_stage"] = {}
    for n, js in by.items():
        if not js:
            continue
        busy = [j["done"] - j["start"] for j in js]
        hand = [b["start"] - a["done"] for a, b in zip(js, js[1:])]
        rec["per_stage"][n] = dict(busy=busy, handoff_after_prev_done=hand, starts=[j["start"] for j in js])
    if by[0] and by[1]:
        # overlap: stage 1 runs position q while stage 0 runs q + 1
        ov = 0
        for a in by[1]:
            ov += sum(1 for b in by[0] if b["start"] < a["done"] and a["start"] < b["done"])
        rec["overlapping_job_pairs"] = ov
        rec["stage_hop_cycles"] = [b["start"] - a["done"] for a, b in zip(by[0], by[1])]
    return rec


def record(scratch: Path, output: Path):
    pn = "prepare_stage2.json" if ORDER == "basic" else f"prepare_stage2_{ORDER}.json"
    prep = json.loads((scratch / pn).read_text())
    res = dict(schema="opentallas.rtl.mtp_exact_wavefront2.v1", prepare=prep, runs={})
    for f in sorted(scratch.glob("run_stage2_*.json")):
        tag = f.stem[len("run_"):]
        meta = json.loads(f.read_text())
        a = analyse((scratch / f"out_{tag}.txt").read_text(errors="replace"))
        res["runs"][tag] = dict(meta=meta, **a)
    suffix = "" if ORDER == "basic" else f"_{ORDER}"
    w1 = res["runs"].get(f"stage2_wfc_w1{suffix}", {})
    w0 = res["runs"].get(f"stage2_wfc_w0{suffix}") or res["runs"].get(f"stage2_wf_w0{suffix}", {})
    res["pass"] = bool(w1.get("passed") and w1.get("out_mismatch") == 0 and w1.get("mismatches") == 0
                       and w1.get("state_mismatch") == 0 and w1.get("overlapping_job_pairs", 0) > 0
                       and (not w0 or not w0.get("passed")))
    res["negative_control_wave0_detected"] = (not w0.get("passed")) if w0 else None
    deep = res["runs"].get("stage2_wfc_w1_deep")
    if deep is not None:      # MR-5: squashed successors already in flight, re-issued after the corrected position
        res["mr5_deep_order_exact"] = bool(deep.get("passed") and deep.get("out_mismatch") == 0
                                            and deep.get("state_mismatch") == 0)
        res["pass"] = res["pass"] and res["mr5_deep_order_exact"]
    output.write_text(json.dumps(res, indent=1) + "\n")
    print("pass" if res["pass"] else "FAIL", {k: (v.get("passed"), v.get("total_cycles")) for k, v in res["runs"].items()})
    return 0 if res["pass"] else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=("prepare", "run", "record"))
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--gold", type=Path)
    ap.add_argument("--wave", type=int, default=1)
    ap.add_argument("--ctrl", default="wfc", choices=("wfc", "wf"))
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--order", default="basic", choices=("basic", "deep"))
    ap.add_argument("--source-layer", type=int, default=19, choices=(8, 14, 19),
                    help="First measured stage; 14 exercises ratio2 compressor rollback plus Engram, 19 is original WFC vehicle")
    a, rest = ap.parse_known_args()
    assert set(rest) <= {"--all-unit", "--kv-hbm"}, rest   # appended by the array campaign import
    global ORDER, CFG, SOURCE_LAYER
    SOURCE_LAYER = a.source_layer
    ORDER, CFG = a.order, ("cfg_stage2" if a.order == "basic" else f"cfg_stage2_{a.order}")
    if a.action == "prepare":
        prepare(a.scratch, a.gold)
        return 0
    if a.action == "run":
        return run(a.scratch, a.wave, a.ctrl, a.jobs)
    return record(a.scratch, a.output)


if __name__ == "__main__":
    raise SystemExit(main())
