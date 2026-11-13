# HARD-QC-FORMS-1 handoff (Fable; QC hard repeat-failing type forms; COORD coordinates)

Started 2026-11-13 06:05 PST. Scope: the unowned DIEVIEW-QC-1113 findings: (a) su_l1 / su_c macro walls behind pin faces, (b) coll_core, (c) CB window-to-tile binding and tap windows, (d) stm ROM row + ROM-read pipeline, (e) setup negative at CTS (st_a). Deliver: plan deltas to DIE-QC-100 for s29, RTL / tool READY branches off origin main, rules in RULEBOOK-1113.md. Then stop.

## Where
- Work dir: epyc7 /srv/opentallas-scratch2/claude/hard-qc-forms-1 (ev2/ = file copy of DIE-QC-100's epyc9 wt/qc-s28-event2 @0bac129af3 without .git; bind_ev2st_g1 copy; tools/tr.py = my type plan render; png/; out/street_head.json = street_rule check of the head with the 59858adeb6 tool).
- Plan base: s28 head zz_gates_ev2st.json 736058c458ee; bound plan zz_bind_ev2st_g1.json 9f3ed3486d81 (bind not clean: 92 errors R8_STALE / LANE_ASBUILT / PARAM_REGEN, DIE-QC-100's item).
- Build pipeline: sub-agent HQF-PIPE (Opus) builds epyc9 /srv/opentallas-scratch2/claude/hard-qc-forms-1/pipe (chain_qc.sh, rebind_qc.sh, README.md); private kits via component-proof + kit-rtl + gen phys; builds through ot-run on epyc7 / epyc4. Baseline: sle_stm_v2__cl7b3062fa.
- Local scratch: localhost scratchpad hq/ (scripts p1-p3.py, tr.py, png/).

## State
- 06:40 read DIEVIEW, RULEBOOK, DIE-QC-100 / CTLCAP / RESID handoffs, METHODOLOGY 12. Base renders of su_c, su_l1 (sle, slw), coll_core, stm, cbn_q00 drawn and viewed.
- stm: DIE-QC-97 (11-10 23:10) measured the class: ROM clk->Q 598 ps, then OR4/AOI + 13 buffers to tw_data registers 350-663 um away. qfd_dv_table_rom_loader already has an opt-in CAPTURE_STAGE (+1 write edge). Form = CAPTURE_STAGE on + ROM block under the N window.

## Next
Design forms per family (guarded delta scripts), proof builds, RULEBOOK rows, READYs.
