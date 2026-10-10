#!/usr/bin/env python3
"""MTP block cycles charged on the token path (mtp-lead, 2026-10-09).

    python3 tools/mtp_step_charges.py            # writes results/arch/mtp_step_20261009/{ds_rom,hbm_ds}_step.json

Until today the MTP views (tools/token_path_export.py ds_rom_mtp / hbm_mtp) charged MTP as a composed rule only
(draft + verify AR pass + 5 wavefront intervals + seed/commit); the cycles the MTP hardware itself adds were NOT
charged.  This tool lists every such charge per MTP step, each from its RTL bench / closure record, and classifies it:

  critical    on the step's serial dependency chain: added to the step (the exporter inserts it as a node)
  overlapped  off the chain, with the schedule fact that proves the overlap (the exporter adds it as a parallel node
              with its slack); a charge is overlapped ONLY when that proof is stated, otherwise it is critical

Variant-dependent charges name the variant charged (the conservative / currently selected one) and the alternative.
The exporter (token_path_export.apply_mtp_charges) reads these files; the MTP tok/s of the token-path views is the
composed step + the critical charges.  Nothing here changes the AR views (the WFC kit's AR-pass charge is listed as
`ar_effect` for the reprice: it applies to AR once the WFC kit is default-on on the S81 dies).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/arch/mtp_step_20261009"
CLK = 1.2e9
TP = ROOT / "results/arch/token_path_20261009"
MTP_ROM_BENCH = "results/rtl/dsrom_mtp_rom_20261008/bench_summary.json"
WFC_CLOSURE = "results/rtl/dsrom_wfc_split_20261006/closure.json"
DRAFT_REC = "results/rtl/dsrom_recovery_20261004/draft/draft_blocks_recovery.json"
MARKOV_Q = "results/rtl/dsrom_markov_pinreg_20261008/qualification.json"
P2_SRC = "physical/mtp_p2_transport/route.sh"
P2_MODEL = "physical/mtp_p2_transport/model.json"
COMMIT_RTL = "rtl/mtp/rollback/ot_mtp_commit.sv"
HBM_BENCH = "results/rtl/hbm_mtp_20261008/bench/round1.json"
SPEC_SWEEP = "results/rtl/mtp_exact_20261008/spec_state/sweep.json"
OLD_STEP = "results/uarch/dsrom_mtp_rom_step_20261008/step.json"
REPRICE = "results/arch/reprice_20261008/reprice.json"


def J(p):
    return json.loads((ROOT / p).read_text())


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:16]


def bench_line(summary, case, tag):
    c = next(x for x in summary["cases"] if x["case"] == case)
    assert c["verdict"] == "OK", (case, c["verdict"])
    line = next(l for l in c["log_lines"] if l.startswith(tag))
    return {k: float(v) for k, v in re.findall(r"(\w+)=([0-9.]+)", line)}


def charge(cid, element, cycles, *, anchor, phase, critical=True, formula, source, grade="measured", variant=None,
           proof=None, note=None, lower=None):
    assert critical or proof, f"{cid}: an overlapped charge needs its proof"
    d = dict(id=cid, element=element, cycles=round(float(cycles), 1), critical=critical, phase=phase, anchor=anchor,
             formula=formula, source=source, grade=grade)
    if lower is not None:
        d["cycles_lower"] = round(float(lower), 1)
    if variant:
        d["variant"] = variant
    if proof:
        d["overlap_proof"] = proof
    if note:
        d["note"] = note
    return d


# ============================================================================================= DS ROM (S81, HALF_PHL)
def ds_rom():
    ar = json.loads((TP / "ds_rom.json").read_text())
    mtp = json.loads((TP / "ds_rom_mtp.json").read_text())
    hv = mtp["mtp_variants"]["half_phl"]
    bs = J(MTP_ROM_BENCH)
    assert bs["all_ok"] is True
    s0 = bench_line(bs, "s0_tr_forced", "MTP_S0_CYC")
    s0f = bench_line(bs, "s0_hash_u1_fast", "MTP_S0_CYC")
    stg = bench_line(bs, "stg_vmnat", "MTP_STG_CYC")
    wfc = J(WFC_CLOSURE)["charge"]
    # ---- stage hops on the AR pass (verify position 1): the AR view's critical stage-hop nodes
    hops = 0
    for n in ar["nodes"]:
        if n["id"] not in ar["critical_path"] or n["cls"] != "hop":
            continue
        if n["op"] in ("token.return", "eng.lead_flit"):
            continue
        m = re.match(r"(\d+) more stage hops", n["label"])
        hops += int(m.group(1)) if m else 1
    assert hops == hv.get("stages", 120) or hops == 120, hops
    lnk = 3 + 3                                    # dsfd_wfc_lnk +3 in / +3 out (mtp-rom benches)
    vmx = stg["start_mean"] + stg["done_mean"]     # dsfd_wfc_vmx start crossing + done path incl. the 46-word prefetch
    per_hop = wfc["hop_delta_cycles"] + lnk + vmx
    busy_cyc = hv["worst_stage"]["busy_us"] * CLK / 1e6
    handoff = busy_cyc * (wfc["measured_interval_overhead"] - 46 / 11271)
    ch = []
    ch.append(charge(
        "wfc_kit.ar_pass", "WFC kit (ot_rom_pkg_ctrl_wfc SOURCE/STG + dsfd_wfc_lnk + dsfd_wfc_vmx) on every stage hop",
        hops * per_hop, anchor="wave.last", phase="verify",
        formula=f"{hops} stage hops (AR view critical path: substage/head hops + the unplaced stage hops) x {per_hop:g} "
                f"(WFC done->out + entry delta {wfc['hop_delta_cycles']} + lnk {lnk} + vmx start {stg['start_mean']:g} + "
                f"vmx done/prefetch {stg['done_mean']:g})",
        source=[WFC_CLOSURE + " charge.hop_delta_cycles", MTP_ROM_BENCH + " stg_vmnat MTP_STG_CYC",
                "~/claude-takeover-20261007/mtp-rom.log (lnk +3/+3 a hop)"],
        note="the composition charges the reference ot_rom_pkg_ctrl_wf (46/11,271 handoff, no shims) whose route was rejected; "
             "the real controller kit adds these on the verify AR pass. Same cycles on every AR token once the kit is "
             "default-on (ar_effect).",
        variant="WFC HARD kit (STG CLOSED, HARD wfc_tok CLOSED, SOURCE partner routing); --wfc-hard is default-off on the die"))
    ii_once = per_hop + handoff
    ch.append(charge(
        "wfc_kit.intervals", "WFC kit on the 5 wavefront intervals (positions 2-6)", 5 * (ii_once + vmx), lower=5 * ii_once,
        anchor="wave.last", phase="verify",
        formula=f"5 x (hop {per_hop:g} + handoff 49 vs 46 on the busiest stage {handoff:.1f} + stage occupancy {vmx:g})",
        source=[WFC_CLOSURE + " charge.measured_interval_overhead", MTP_ROM_BENCH + " stg_vmnat"],
        note="upper bound charged: the vmx start/done cycles are counted both in the hop latency and as stage occupancy "
             "(no bench measures the handoff with vmx in place, so the overlap of the outbound prefetch with the next "
             f"position's start is NOT proven); cycles_lower counts them once ({5 * ii_once:.0f})"))
    # ---- sequencer (dsfd_mtp_seq, head die)
    ch.append(charge(
        "mtp_seq.draft_chain", "dsfd_mtp_seq draft chain (seed rows -> first draft head, head result -> next head)",
        s0["rows_to_dh1"] + 5 * s0["dh_result_to_next"], anchor="draft.last", phase="draft",
        formula=f"rows_to_dh1 {s0['rows_to_dh1']:g} + 5 x dh_result_to_next {s0['dh_result_to_next']:g}",
        source=[MTP_ROM_BENCH + " s0_tr_forced MTP_S0_CYC"],
        note="bench means include the bench adapters (+2 in / +1 out): upper bound; each draft head step waits for the "
             "previous head's argmax (serial chain)"))
    ch.append(charge(
        "mtp_seq.seed_release", "dsfd_mtp_seq seed after the closing result + DRAFT flit / release",
        s0["seed_after_close"] + s0f["last_dh_to_draft_flit"], anchor="accept.commit", phase="accept",
        formula=f"seed_after_close {s0['seed_after_close']:g} + last_dh_to_draft_flit {s0f['last_dh_to_draft_flit']:g} "
                "(s0_hash_u1_fast: no squashed results to wait for)",
        source=[MTP_ROM_BENCH + " s0_tr_forced / s0_hash_u1_fast MTP_S0_CYC"],
        note="the other traces' release (51.6-231 cycles) includes waiting for squashed verify results the bench models "
             "serially; those positions are already charged as verify intervals"))
    ch.append(charge(
        "wfc_tok.edges", "dsfd_wfc_tok HARD (S0 token/draft store, one-edge read)", 3, anchor="accept.commit", phase="accept",
        formula="+3 edges (draft store write -> verify-start read)",
        source=["results/arch/mtp_status_20261009/STATUS.md (dsfd_wfc_tok HARD row: +3 edges recorded)",
                "results/rtl/dsrom_wfc_token_hard_20261009"]))
    ch.append(charge(
        "mtp_commit", "ot_mtp_commit (n = q + 2 + a, registered)", 1, anchor="accept.commit", phase="accept",
        formula="commit outputs registered 1 cycle after acc_done", source=[COMMIT_RTL + " header (Latency)"]))
    # ---- P2 selected draft transport (MD-2): replaces the recovery path's expert return hop per draft block
    dr = J(DRAFT_REC)
    p2_gate = 5467
    p2 = []
    for st, s in dr["stages"].items():
        ret = next(p["us"] for p in s["critical_path"] if p["node"] == "ffn.ret_hop.r0") * CLK / 1e6
        p2.append((st, ret))
    ch.append(charge(
        "p2.selected_path", "MD-2 P2 selected path (PRIMARY_SHARED1 9-SRAM transport + 3-SRAM A-prefix + publisher)",
        sum(p2_gate - r for _, r in p2), anchor="draft.blocks", phase="draft", grade="measured (bench log)",
        formula=" + ".join(f"({p2_gate} - {st} ret_hop {r:.0f})" for st, r in p2),
        source=[P2_SRC + " header (codex/mtp-die-continuation 0091c7ad5 gate PASS 5,467 cycles; reproduced by mtp-lead "
                "for mtp-p2-path-{a,b}-91473d972-tc)", "~/claude-takeover-20261007/REVIEW_20261009.md V22 (5,467 cycles per "
                "rank prefix, <= 6,240 model)", DRAFT_REC + " stages[*].critical_path ffn.ret_hop.r0"],
        variant="selected P2 path (routes queued, not closed); the composition's draft is the DP1-EP5 recovery placement",
        note="per draft block the rank prefix replaces only the expert return hop; the block's combine all-reduce stays "
             "(no record replaces it): upper bound. Blocks are serial (block k+1 consumes block k's hc_post), so critical."))
    # ---- Markov head (MD-6): the composition's transfer ratio vs the measured row-pipeline latency
    mq = J(MARKOV_Q)
    mk_model = next(n["cycles"] for n in mtp["nodes"] if n["id"] == "draft.markov0")
    mk = mq["first_result_cycles_no_bubbles"]
    ch.append(charge(
        "markov.floor", "Markov head PINREG1 (ot_dsrom_markov_row, K 256)", 5 * max(0.0, mk - mk_model),
        anchor="draft.last", phase="draft",
        formula=f"5 draft steps x (first result {mk} cycles - modelled {mk_model:g})",
        source=[MARKOV_Q + " first_result_cycles_no_bubbles", "results/arch/token_path_20261009/ds_rom_mtp.json draft.markov*"],
        note="lower bound: the measured single-row pipeline latency is a floor the transfer-ratio model is under; the "
             "whole-vocab sweep throughput needs the head full340_A production wrapper (not built)"))
    # ---- sensitivity: the RTL-sequenced step (draft from the closing result), NOT credited
    old = J(OLD_STEP)["step_model"]["blend_harmonic"]
    sens = dict(rtl_sequenced_over_model=old["rtl_over_model"], source=OLD_STEP + " step_model.blend_harmonic",
                why_not_credited="dsfd_mtp_seq starts the draft at the closing result while positions a+1..5 are still in "
                                 "verify; the draft head steps then share the head die's lm_head bundle with the verify "
                                 "positions' head passes. The bench proves the sequencing, not a conflict-free head "
                                 "schedule: overlap NOT proven, so not credited")
    return finish("ds_rom", ch, mtp, sens=sens, ar_effect=dict(
        cycles=hops * per_hop, rule="the WFC kit's per-hop cycles on the AR pass; apply to the AR views when --wfc-hard is "
        "default-on", AR_tok_s_before=hv["AR_tok_s"],
        AR_tok_s_after=round(CLK / (hv["AR_us"] * CLK / 1e6 + hops * per_hop), 1)),
        inputs=[MTP_ROM_BENCH, WFC_CLOSURE, DRAFT_REC, MARKOV_Q, P2_SRC, P2_MODEL, COMMIT_RTL, OLD_STEP])


# ============================================================================================= HBM accelerator (TP-96)
def hbm_ds():
    mtp = json.loads((TP / "hbm_ds_mtp.json").read_text())
    nodes = mtp["nodes"]
    moe = sum(1 for n in nodes if n["label"] == "du:router_top6" and n["critical"])
    assert moe == 40, moe
    hb = J(HBM_BENCH)
    assert hb["verdict"].startswith("PASS")
    ch = []
    ch.append(charge(
        "ctl_stop.nreg", "adopted NREG controller transition between successive MTP passes", 1,
        anchor="draft.last", phase="draft",
        formula="+1 per steady-state MTP pass after the first; single-pass/EOS/prefill cases add 0",
        source=["results/rtl/mtp_hfdpipe_20261009/gates.json cycles_added and multistep_differential",
                "results/rtl/mtp_lead_20261009/routes/hfd-mtp-x-stop-nreg-hm10-7bebe74b7-tc"],
        variant="adopted NREG=1; step throughput conservatively charges the recurring transition"))
    ch.append(charge(
        "hfd_mtp.round_trips", "hfd_mtp die master pin flops (command -> engine done round trips)", 7 * 2,
        anchor="draft.last", phase="draft",
        formula="7 dependent round trips a step (5 draft-head commands, verify, accept/emit) x 2 (+1 per pin crossing)",
        source=[HBM_BENCH + " cycle_note (+1 per pin crossing, +2 per round trip)"],
        variant="x-stop (die-router selections) live; hfd_mtp_x_lvt would be +4 a round trip (PRL 2)"))
    ch.append(charge(
        "hfd_mtp.logit_pins", "hfd_mtp logit-row input pin flop + am output (6 argmax streams)", 6 * 2,
        anchor="draft.last", phase="draft",
        formula="(5 draft heads + 1 verify) x (lg_* in +1, am_* out +1)", source=[HBM_BENCH + " cycle_note"]))
    ch.append(charge(
        "argmax_f1", "ot_dshbm_argmax FAST (argmax_f1)", 6, anchor="draft.last", phase="draft",
        formula="+1 per argmax stream x 6 (rows stream; the register adds latency once a stream)",
        source=["~/claude-takeover-20261007/mtp-hbm.log (argmax FAST is +1 cyc/row)",
                "results/rtl/hbm_mtp_20261008/routes/mtp_argmax_f1-d30fa5f39-tc"]))
    ch.append(charge(
        "topk_f384", "router topK (topk_f384) on every MoE layer of the verify walk", moe * 1, anchor="verify.last",
        phase="verify", formula=f"{moe} MoE layers (du:router_top6 on the verify path) x +1 a select",
        source=["~/claude-takeover-20261007/mtp-hbm.log (+1 cyc/select vs topk original)",
                "results/rtl/hbm_mtp_20261008/routes/mtp_topk_f384-d30fa5f39-tc"]))
    ch.append(charge(
        "union_f3", "ot_dshbm_expert_union FAST (union_f3) per MoE layer", moe * 1, anchor="verify.last", phase="verify",
        formula=f"{moe} MoE layers x +1", source=["results/arch/mtp_status_20261009/STATUS.md (union_f3 +1)",
                                                   "results/rtl/hbm_mtp_20261008/routes/mtp_union_f3-d30fa5f39-tc"]))
    ch.append(charge(
        "spec_state.gathers", "spec-state window gathers through hfd_mtp (sr/sa valid-ready streams)", 3 * 3,
        anchor="accept.commit", phase="accept",
        formula="3 DSpark stages' window-row gather streams x +3 (once a stream: valid/ready ports behind skid slices "
                "accept one request a cycle)", source=[HBM_BENCH + " cycle_note (+3 per spec-state gather)"],
        note="the bench issues gathers serially (+3 each, upper bound); on the die each stream pays the latency once"))
    ch.append(charge(
        "spec_state.answer", "spec_state_f answer latency on the accept path", 5, anchor="accept.commit", phase="accept",
        formula="LAT 5 (token-ring write through 5 registered stages)", source=[SPEC_SWEEP + " bench (a_* LAT=5)"]))
    ch.append(charge(
        "scratch_c2", "draft scratch (scratch_c2)", 1, anchor="accept.commit", phase="accept", formula="+1 a step",
        source=["results/arch/mtp_status_20261009/STATUS.md (scratch_c2 +1)"]))
    ch.append(charge(
        "fence", "RF visibility fence", 2, anchor="accept.commit", phase="accept",
        formula="+2 capture -> write (fence_p), once a step before the next step's reads",
        source=["~/claude-takeover-20261007/mtp-hbm.log (fence_p +2 cyc capture->write)"],
        variant="fence_p charged (+2); the banked -cx (mtp_fence_b64-*-75cb677e4, 0 cycles) is routing: 0 if it closes"))
    ch.append(charge(
        "mtp_commit", "ot_mtp_commit (n = q + 2 + a, registered)", 1, anchor="accept.commit", phase="accept",
        formula="commit outputs registered 1 cycle after acc_done", source=[COMMIT_RTL + " header (Latency)"]))
    draft_cyc = sum(n["cycles"] for n in nodes if n.get("phase") == "draft" and n["critical"] and not n["id"].startswith("mc."))
    rows = moe * 6
    ch.append(charge(
        "dskv_wb_spec.rows", "adopted ot_hbm_accel_dskv_wb_spec PIPE=2 (+3 a row)", rows * 3, anchor="step.start",
        phase="draft", critical=False,
        formula=f"{moe} layers x up to 6 accepted positions = {rows} KV rows x +3",
        source=["results/rtl/mtp_lead_20261009/dskv_wb_spec_p2/README.md (+3 a row vs PIPE 0)"],
        variant="adopted mtprb-dskvwb_spec_p2a-5ce6c3c62-tc; wrapper pin FIFO costs retained",
        proof=f"the accepted rows of step s are written while step s+1 drafts: the draft phase ({draft_cyc:,.0f} cycles) runs "
              "on the DSpark stages' own state (main_x + their wkv window rows), and the first read of a main-model KV row is "
              "verify layer 0 after the draft; the +3/row adds <= "
              f"{rows * 3} cycles to a write stream that must fit in {draft_cyc:,.0f} cycles"))
    hbm_sim = dict(note="The HBM native and approved gather paths are distinct; systems.json uses "
                        "ds_sw_seq_pricing.json approved_path_c2_g22 and adds its delta relative to native S2 once "
                        "per verify pass. These component charges carry over to either basis unchanged.")
    return finish("hbm_ds", ch, mtp, basis_note=hbm_sim, inputs=[HBM_BENCH, SPEC_SWEEP, COMMIT_RTL, "results/rtl/mtp_hfdpipe_20261009/gates.json",
                "results/rtl/mtp_lead_20261009/dskv_wb_spec_p2/README.md"])


def finish(key, ch, mtp, sens=None, ar_effect=None, basis_note=None, inputs=()):
    tau = mtp["totals"]["tau"]
    base = mtp["totals"]["cycles"] - sum(n["cycles"] for n in mtp["nodes"] if n["id"].startswith("mc.") and n["critical"])
    crit = sum(c["cycles"] for c in ch if c["critical"])
    crit_lo = sum(c.get("cycles_lower", c["cycles"]) for c in ch if c["critical"])
    rec = dict(
        schema="opentallas.mtp_step_charges.v1", design=key, tool="tools/mtp_step_charges.py", published=True, clock_hz=CLK,
        rule="MTP step = the composed step (token_path_export) + every critical charge; overlapped charges carry their proof",
        charges=ch,
        totals=dict(critical_cycles=round(crit, 1), critical_cycles_lower=round(crit_lo, 1),
                    overlapped_cycles=round(sum(c["cycles"] for c in ch if not c["critical"]), 1),
                    composed_step_cycles=round(base, 1), charged_step_cycles=round(base + crit, 1), tau=tau,
                    MTP_tok_s_composed=round(tau * CLK / base, 1), MTP_tok_s_charged=round(tau * CLK / (base + crit), 1),
                    MTP_tok_s_charged_lower_charges=round(tau * CLK / (base + crit_lo), 1)),
        inputs={p: sha(p) for p in inputs})
    if sens:
        rec["sensitivity_not_credited"] = sens
    if ar_effect:
        rec["ar_effect"] = ar_effect
    if basis_note:
        rec["basis_note"] = basis_note
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{key}_step.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def main():
    for f in (ds_rom, hbm_ds):
        r = f()
        t = r["totals"]
        print(f"{r['design']}: +{t['critical_cycles']:,.1f} critical (lower {t['critical_cycles_lower']:,.1f}), "
              f"{t['overlapped_cycles']:,.1f} overlapped; MTP {t['MTP_tok_s_composed']:,.1f} -> {t['MTP_tok_s_charged']:,.1f} tok/s")
        for c in r["charges"]:
            print(f"   {c['id']:24s} {c['cycles']:>9,.1f} {'critical' if c['critical'] else 'overlapped'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
