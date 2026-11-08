# QC-TYPES-10/CTLM 11-08: tt_ctlm CALREG[0] FQREG netlist rebuild

## Failure and cause

The kit-wave row tt_ctlm failed TIMING. kw24 a9 post-CTS G2 setup_tt was -278.65 ps.
QC-TYPES-9/DEPTH diagnosed the worst path (results/rtl/qc_types_9_depth_1108/README.md):

    u_gi.u_cal.g_fifo[2].u_fifo rd_out (SRAM access 380 ps) -> 4:1 rs select -> fq_word source select
    -> FIREDQ dq = tcount + 1 - ht -> dq FF

That path has 25 levels at a 773 ps period.

The tt_ctlm master is the HP13 generated netlist qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1. Its u_cal
(qfd_dv_cmd_cal_mu, frozen sha 7617d35a) is the SRAM-FIFO form, which predates CALREG.

## Fix

The fix is the existing CALREG[0] FQREG form from rtl/qwen_dv/headprep37/qfd_dv_cmd_cal_mu_head37.sv:

- Each playhead has an 8-entry ring of 2 x 512 flops, plus a registered next head nx_q.
- A pop loads the head from nx_q.
- The 4 FIFO SRAMs and the pending/bypass source selects are gone from the FIREDQ cone.

How it is applied:

- The input is head37 with the module renamed back to qfd_dv_cmd_cal_mu and CALREG defaulting to 1
  (qfd_dv_cmd_cal_mu_fqreg.sv, sha 3f3481f2).
- HEAD_STAGE37 = 0, so the stage range is unchanged.
- STARTREG and ISSUEFLAT are off, so 0 edges are added.
- Every other head37 hunk is gated by CALREG or HEAD_STAGE37 (diff checked).

Cost: PIN CYCLES 0, EDGES 0, no image change.

Estimate: the new worst path in this cone is nx_q FF -> 3:2 + 14-bit KS (ot_ks_add) -> candidate select -> dq FF. That is
about 11 levels, roughly 300-350 ps of the 773 ps period. The SRAM's 380 ps and about 4 select levels leave the cone, so this
cone is expected at about +300 ps. The type's next-worst path is unknown until the kit runs.

## Reproduction (heavy steps via ot-run)

### 1. Frozen HP13 frontend tree

build_tree.py rebuilds the frozen tree from git:

- Inputs come from 4b215c0b3 and 8349f4a1, using frontend_input_commits.json (each blob is matched to the
  input_source_inventory sha256).
- The native_frontend files come from c303af45e5b.
- Modes are base, fqreg (the ys reads the FQREG cal file instead of rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv) and fqreg_mut2.

regen_native.sh is the QDIE5 recipe: yosys 0.68 full_generic_hp13.ys, then construct_hp13_2.py.

| tree | native32 sha256 | notes |
|---|---|---|
| base | 22b50590 | bit-exact to main (positive control) |
| fqreg | 81f18c88 | 73866 generic cells, was 74215; macros 13 -> 9 (the 4 g_fifo 64x512 SRAMs are gone); dff_p +2054 |
| fqreg_mut2 | 8229cc27 | mutant |

The helpers are unchanged at 8a1c0d01. See logs/construct_*.log.

### 2. Core publisher

mk_alias.py runs on the FQREG parent.json. Then regen_corepub_ctlm.py runs; it is a copy of the QDIE5 driver.

| output | sha256 |
|---|---|
| cpub39_1 | c09b67b7 |
| cpub39_2 | 01c85b5a |

Fanout audit PASS: 768 dead-cone keep removals and 3 protected, the same as before. The bank qfd_hp13_corepub39 is unchanged.
tools/qwen_split/headprep_source.py and headprep_corepub_source.py are re-pinned.

## Proof

### realcalendar_native lockstep

This compares the regenerated native netlist with the frozen SRAM-form HP13 RTL on every edge (V5.050). The fixture is
fixture_overlay.sh with results/arch/qdie5_hp13_1022/run_native_compare.sh. Input shas for every tree are in
logs/ncmp_inputs_*.sha256; the base inputs match QDIE5's ncmp_inputs.sha.

| run | CALR1 | CALR2 |
|---|---|---|
| base 22b50590 (control) | PASS, 1,198,920 compares | PASS, 4,744,920 + TLOAD_PRODUCER PASS |
| FQREG 81f18c88 | PASS, 1,198,920 compares | PASS, 4,744,920 + TLOAD_PRODUCER PASS |
| MUTANT fqreg_mut2 (nx_q refill at c0 == 1 from the wrong ring half) | FAIL, 3,566 mismatches | FAIL, 20,907 mismatches |

The mutant is caught.

### HP13 die-form head bench

This is the TOKc-SEGCAL die runs: hb/run_hb.sh, the tt_ctlm_prog_bench checker from c0f8097f3, and the die form
materialized by hb/materialize_4b215.py, with u_cal swapped. It uses the landed lp in lockstep.

| run | result |
|---|---|
| base imgh | PASS 131/131, LANDED_LOCKSTEP PASS |
| FQREG imgh | PASS 131/131, LANDED_LOCKSTEP 27,946 / 0 mismatches |
| FQREG img0 | PASS 123/123, LANDED_LOCKSTEP 24,811 / 0 mismatches |
| FQREG bmut3 | FAIL 129/131 (caught) |
| RTL mutant fqreg_mut2 imgh | PASS 131/131 |

The head bench does not catch the RTL mutant fqreg_mut2: this image never takes the c0 == 1 refill with differing ring
halves. The realcalendar lockstep above is the witness that catches it.

## Plan event plan_qc53v4w_ctlmfq

- Base: v4w e5dc7eacb745.
- Script: mk_plan_ctlmfq.py.
- sha256: 9c4334378129cefb1c478f25d59b0ae783593fd9999daa3bc7c4e107ee04cd51.
- Only partition_types.tt_ctlm.hard_cores changes (19 -> 15: the 4 u_bound.u_core.u_gi.u_cal.g_fifo[*].u_fifo SRAMs
  are removed), plus that type's note.
- Every other key is identical: asserted in the script, and the text diff is 97 lines.
- Schema validate PASS (logs/validate.txt).
- Staged with cores/ at /srv/opentallas-scratch2/claude/qct10/ctlm/plan/ on epyc4, epyc2, epyc5, epyc6 and intel1.
- Strict bind: bind_report.txt.

Scope: no physical, closure or sign-off claim. The kit has to show the new timing.
