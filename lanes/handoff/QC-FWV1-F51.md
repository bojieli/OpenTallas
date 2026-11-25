# QC-FWV1-F51 handoff (parent QC-ALLFIX)
Type: slw_fw_v1__clf51c11d8__cl592e3d37. Census posted 11-25 05:2x (hub d97d840e3f76).
Pick: --goal place probe on C1o v13 aa3a14fb7484 after BIND-PASS.
- Waiter: epyc12 /srv/opentallas-scratch2/claude/QC-FWV1-F51/wait.sh (pid 224121). Needs both a line starting "BIND-PASS C1o v13 aa3a14fb7484" in the QC-C1O-COMPOSE posts and bind_v13/latcheck.json with errors=[]. Then it runs kit.sh: kit_wave private-spec, epyc12, rt b7165c47a452, --ab OT_TAP_ESCAPE_CLEAR_UM=0.30.
- Read at place: the TT worst path (old kits: cland_origin->rstart_tx, rstart_in->fstart_flt_wo, -72..-136) and POSTCTS pinreg dev (C1j: 37.4 > 20).
- Residual cland/pinreg miss -> own C1p row. Leaf/channel/sink bins are not mine: FWLEAF-1 (QC-FWLEAF1-RE), FEFW-FAM (QC-FEFW-FAM), SINKBINS (QC-SINKBINS).

## 07:5x update (COORD 07:4x via QC-ALLFIX: write the row now, do not wait for the probe)
- Cause: role-strap type. Relay copies sl_W0_fw/sl_W4_fw had cland_start_d = the raw cland_rstart_in pin (E face 621,916), so one combinational hop of up to 1.1 mm reached every writer-start stage 0 and the fstart_flt_wo copy (-116..-142). The same pin had 2 loads (face_guard shared).
- Tool: main e74667e963ad (clock_landings ROLESTRAP-RX-STAGES + tests). Worktree: epyc12 QC-FWV1-F51/wt.
- Row FWV1-RXSTG 6a2552d4395e (epyc12+epyc11 QC-FWV1-F51/row_fwv1_rxstg.json): rx_stages 4, rx_pin_plain, sites p0 (613.44,915.84), p1 (613.44,640), p2 (420,492.48), p3 (200,492.48); sidecar parts sl_W0/W4_fw stages 4->8. Gives plan 97f39816ffca and sidecar 05d2401f8810 (epyc11 QC-FWV1-F51/c1p).
- PRE by path: epyc11 pre.sh on launch_fwv1 (C1n-r3 tree on epyc11 + SUL1 overlay, rt b7165), log pre_fwv1.log.
- Next: the scoped strict bind after BIND-PASS v13 (needs an rt that has e74667e), then a place probe.
- Row 19 (sle_fw_v1 sc_eo -216) is covered by FWLEAF-1 (QC-FWLEAF1-RE). No second row.
