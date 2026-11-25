# QC-FWV1-F51 handoff (parent QC-ALLFIX)
Type: slw_fw_v1__clf51c11d8__cl592e3d37. Census posted 11-25 05:2x (hub d97d840e3f76).
Pick: --goal place probe on C1o v13 aa3a14fb7484 after BIND-PASS.
- Waiter: epyc12 /srv/opentallas-scratch2/claude/QC-FWV1-F51/wait.sh (pid 224121). Needs both a line starting "BIND-PASS C1o v13 aa3a14fb7484" in the QC-C1O-COMPOSE posts and bind_v13/latcheck.json with errors=[]. Then it runs kit.sh: kit_wave private-spec, epyc12, rt b7165c47a452, --ab OT_TAP_ESCAPE_CLEAR_UM=0.30.
- Read at place: the TT worst path (old kits: cland_origin->rstart_tx, rstart_in->fstart_flt_wo, -72..-136) and POSTCTS pinreg dev (C1j: 37.4 > 20).
- Residual cland/pinreg miss -> own C1p row. Leaf/channel/sink bins are not mine: FWLEAF-1 (QC-FWLEAF1-RE), FEFW-FAM (QC-FEFW-FAM), SINKBINS (QC-SINKBINS).
