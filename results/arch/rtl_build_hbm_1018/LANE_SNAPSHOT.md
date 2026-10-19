# Lane RTL-BUILD-HBM (owner 0dv 10-18: build every missing RTL now) -- HBM die d4g -- 10-18 00:30
Branch claude/rtl-build-hbm-1018 (from origin/main 4f7440ccf). Worktree /home/ubuntu/wt/rtl-build-hbm-1018 (sparse).
Audit file: results/arch/rtl_build_hbm_1018/gen0_gap_audit.json. For every one of the 30 GEN0 gaps it lists each affected port and the master that drives or consumes it in the GEN0 contract (claude/hd4g-1017 da28e8d0f).
Sub-agent brief: /home/ubuntu/.claude/jobs/33555330/tmp/rbh_sub_brief.txt.

## Finding: the 30 GEN0 "gaps" are stale text, not 30 missing modules
GEN0 reports 0 exposed inputs. The gap descriptions are copied from the v16 specs (10-15/16). Since those specs were written, later layers bound almost all of the ports to real RTL: cxport, inj_copy, status_join_fa, col_idx/col_su/col_sfu collars, wb_kport, hc_eng_static, svc_sm_group_id, sfustore, cmd_target, and the fault tree. Residuals:
- open observability outputs: COLL done/stat_cycles/init_busy, inj_idx, argmax done. HBM-TIE classifies these as OBS.
- off-die pads: session_pad and the UCIe PMA. These are declared PHY/off-die pins, which the rules allow.
- G-HOST-PROGRAM-INSTALL: a verification item, not a missing RTL.
The missing RTL is in the d4g per-quadrant change: plan items 5, 9 and 10 plus the stack services that cross the centre line. None of these is in d4g.open_bindings, so no lane owned them.

## Gap -> owner -> state
gap / element | owner | state
--- | --- | ---
G-CIL-INJ (COLL inj_d) | bound: sucx (ot_hbm_su_static_cxport) + cij/cic; cxport = HBM-SU6 (su6-cx) | RESOLVED in GEN0; inj_idx open = OBS
G-CIL-RC (RED_CARRY rc/rr) | bound: sucx <-> hb_coll; HBM-SU6 / HBM-B-RTL3c | RESOLVED
G-CIL-DEL (del_flit consumer) | bound: sucx consumes; HBM-SU6 / HBM-B-RTL3c | RESOLVED
G-CIL-COLLSTAT | bound: ot_hbm_status_join_fa (faults); done/stat_cycles/init_busy open = OBS (HBM-TIE) | RESOLVED (OBS residual)
G-CIL-IDXCP (IDX programme/record issuer) | bound: col_idx collar (hdie_col_idx_r1 SUBMITTED); quad IDX = HBM-B-RTL2b | RESOLVED; RTL2b re-binds the quad client
G-CIL-AMCP (argmax issuer) | bound: col_idx collar; argmax r2 = HBM-SU6 (claude/hbm-su3-1017) | RESOLVED; done open = OBS
G-CIL-HOSTN (host packet bridge) | bound: ot_hbm_host_phy_adapt (closed view) | RESOLVED
G-DMA-WB / G-DMA (WB partner wb_ready/wa) | bound: ot_hbm_svc_wb_kport | RESOLVED for d4f; d4g per-quadrant split = RBH-STK (below)
G-HOST-SESSION (session_pad) | die pin (off-die sideband) | ACCEPTED (pad)
G-HOST-PADS (UCIe PMA) | die pins, behavioural PMA | ACCEPTED (PHY)
G-HC-ENG / G-HC | bound: ot_hbm_hc_eng_static + hc_q; d4g split = HBM-B-RTL2b | RESOLVED; split owned by RTL2b
G-HOST-PROGRAM-INSTALL (typed loader install coverage) | RTL-BUILD-HBM follow-up (bench, not RTL) | QUEUED (next RBH pass)
G-HOST-LOADER-CAL / G-SMVM-CALISS (VM calendar issuer) | bound: host_cp_ingress -> calendar_<q> (vm_calendar_f20 targets 56-59/96-99/132-135) | RESOLVED
G-HOST-LOADER-SVG | bound: ot_static_cmd_target cp_svg x16 (CLOSED hdie_cp_svg_r1) | RESOLVED
G-QUANT-SPLIT | split RTL on main (ot_hgi_qdq_lg_port_group / transport_split; 0dc+ decision); die binding = H-D4G (quant_NW0..3/_lg/_xp slots in grants); QBG = HBM-B-RTL3c | RTL EXISTS -> H-D4G bind
G-SMVM-XCMD (static x-load issuer) | bound: ot_hgi_sm_xload_cl2_ctlx (cfg/desc/launch from host_cp_ingress); d4g per-quadrant = RBH-XQL | RESOLVED d4f; d4g -> RBH-XQL
G-SMVM-STRAP | bound: banks flattened (vmb_<q><b> hfd_vms_bank_native_*) | RESOLVED
G-SMVM-KEYSTAGE (key_lines) | bound: svc_sm_group_id -> scorer; quad scorer = HBM-B-RTL2b | RESOLVED
G-SU-PROG-HOST | bound: col_su collar -> su_prog; pslice c5 = HBM-SU6 | RESOLVED
G-SFU-LOADER-SW/SE/NW/NE | bound: col_sfu_<q> collars (CLOSED hdie_col_sfu_r1) | RESOLVED
G-SFU-OPERAND-JOIN-SW/SE/NW/NE (vi_q/side_y) | bound: vi_q from sfus_<q> (ot_hbm_su_static_sfustore); side_y proved unused (HBM-TIE item 4) | RESOLVED; sfus hardening = RBH-SFUS

## d4g open bindings (units the RTL lanes are changing)
unit | owner | state
--- | --- | ---
VM SE/NE hubs, quadrant writer, vmdel NPC2 | HBM-B-RTL1b (vm) | RTL+benches done; vmdel_lane2 SUBMITTED; wrq_t4 critical (coordinator)
SU stree / whole-SU RF_TREE bench | HBM-B-RTL1b (su) | leaf/root CLOSED; whole-SU bench running (scratch_hbmb_su_stree)
host_cfg_leaf per-quadrant NT/NF variants | HBM-B-RTL1b (host) | STARTED: hdie_host_cfg_leaf_{sw,se}_r1 gates running (seen 00:2x)
pgp_<q> pslice c5, sucore qcore r5, sucx cxport | HBM-SU6 (su6-ps / su6-qc / su6-cx) | running
subr_<q> ot_hbm_su_bridge_release (fold) | UNOWNED -> RBH-SFUS | building
HC quadrant engines + tree | HBM-B-RTL2b | split lockstep PASS (+28)
IDX scorer quarters + qctl + xq node | HBM-B-RTL2b | lockstep on fleet (lock1)
argmax r2 | HBM-SU6 (claude/hbm-su3-1017) | equiv mutants on fleet
COLL two rings + ring-AG ctl + QBG | HBM-B-RTL3c | bench running; QBG bench PASS
QDQ split binding | H-D4G | RTL on main
SFU store sfup_<q> cluster r10 | coordinator (CRITICAL hbm_sfu_programme_store) | r10n2 leaf awaiting review
sfus_<q> ot_hbm_su_static_sfustore hard wrapper (+ plan item 5 SFU/LG chain quadrant check) | UNOWNED -> RBH-SFUS | building
XQL per quadrant (plan item 9: xl_<q>_ctl + aq13 lo/hi + xq pair blocks rebound per quadrant) | UNOWNED -> RBH-XQL | building
DMA-back / WB per quadrant (plan item 10: hb_dbk_<q>, wbk_<q>, wbc) + stack services crossing the centre line (sfault_<S>, refcfg_<S>) | UNOWNED -> RBH-STK | building

## Sub-agent results (appended by the sub-agents)
