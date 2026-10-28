# TOK-ALL-16 GB composition (XS4 -> col_h10_l4_lp_asb_x u_f_0L01 -> capc5r_e6), Tue Oct 27 05:13:27 PM PDT 2026

Outcome: POSITIVE PASS. intel1 unit oth-ubuntu-2788117-1793145276; raw data in /srv/opentallas-scratch2/claude/tok16-gb.

Root cause of the TOK-ALL-15 FAIL (CHECKED):
- The image generator and the calendar were correct.
- The physical kit strips #() from hard children. The functional copy of the image candidate (gb_image_bind_1450) restored only INSTANCE.
- So its 16 ot_s81_cfg7_seq and 6 ot_s81_cfg7_seq_bfp calls elaborated at their defaults: PQ 0, LAYOUT 0, PINREG 0.
- The hardened set (kit hard_params json and canonical vg col_h10_l4_lp.sv) is PQ 1, LAYOUT 1, PINREG 1.
- The il7 (LAYOUT 1) cfg image carries class-valid in word 8 (bank 1, row 1; decoded 0x401). The LAYOUT 0 sequencer reads macro 0 linearly and never sees it, so act stays 0 and go_e never rises.

Fix:
- tools/s81_dv/gb_hard_params.py restores exactly the kit-recorded hardened set on the functional copy.
- Each value must equal both the hard_params record and the canonical call. Ports and all other parameters are byte-identical; 0 cycles.
- 22 calls restored. Tests: 1 positive and 3 fail-closed controls.
- New candidate manifest asbuilt_b178_gb_image_candidate_tok16.json.
- Fresh extraction of all 4 masters PASS (h10_x 171/171, 38/38 plan). The schedules equal tok15's, as expected: the sequencers are black boxes in extraction.

Measured (CHECKED, run1/check.json and logs). Edges are core cycles at uniform clock phase:
- XS cfg at 390, XS go at 452 (Q advance 1).
- Sequencer go_e: r0 464/470, r1 479/482, r2 491. Element go +2 edges after its sequencer.
- 14/14 returns at 732..772. Return-plan shift 322 == pinned 322 (calibrated model 321 + measured XS4 edge).
- 4/4 CAP words == checkpoint, captured 823..855.
- GO -> last capture = 403 cycles. cfg -> last capture = 465 cycles.

Controls:
- Input corruption CAUGHT.
- Wrong loaded image CAUGHT.
- Parameter-stripped source (tok15 run2) CAUGHT: 0 returns.
- Old Q calendar NOT caught. It is an EQUIVALENT mutant at this scope: go at 453 instead of 452, but the returns and captures are bit- and edge-identical. The frame is paced by the stream, not by go.
- So Q advance 1 is not observable in a one-frame composition.

Scope:
- One frame (u_f_0L01) of L0 a_proj on slice u_s_0S.
- Not simulated: the 39-station return relay chain, the dsfd_dvland_70 landing, the other frames and regional clock phase.
- Bench admission OT_XS_GB_PROVIDER_UNDER_TEST=1; the default guard is unchanged and the native provider is NOT qualified.
