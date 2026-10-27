# HEAD-RTL lane (s81_head missing content RTL)

## [HEAD-RTL 2026-10-26 19:30 PDT] hd_mesh RTL written, hd_lep0N covered by the existing provider; hd_ctl and hd_host ASK. No job running.

Branch claude/head-rtl-1026@fa6598bd6 (base origin/main d398138f3). Evidence: results/arch/head_rtl_1026/.

Port-bind / module check (tools/s81_head/head_module_check.py), CHECKED:
- canonical plan: 4 missing.
- candidate plan (head_rtl_plan_delta.py, a copy, no adoption): 2 missing (ot_s81hd_ctl, ot_s81hd_host_ep), 0 unresolved instances.
- gen.py rtl --rtl-root leaf bind for hd_mesh and hd_lep0N: rc 0.
The "0 missing" target is NOT met.

- hd_lep0N: covered by Codex's ot_s81hd_lep0N_core and its source closure; I wrote no new RTL. The plan names "dsdv_slice_lepw_mu.LP", which is not a module. Codex's head_lep_plan_delta.py fixes this: u_core = lep0N_core, plus a 1-bit lep0N.fault_o0 -> ctl.lep_fault_i return. Adopting it is a plan event (plan frozen).
- hd_mesh: NEW ot_s81hd_mesh_ep_core.
  - Contents: 2 x stacked MAIN head lane (dsfd_coll_lane_w_safe8_ntf + closed s81hd_lsc_t9x3/t8/r0m/r1m, the sc6 composition renamed) + best64 decode on TX (the own BEST goes on both lanes) + copy-A/B slots on RX.
  - Output to ctl: 110-b words {ep_fault12, copy, HSF0 hdr+BEST97}, 2 beats each, A first. The ctl side is ot_s81hd_mesh64_rx, which feeds rank_merge mrx_v[2p]/[2p+1].
  - Exactly the plan buses. Lane flt, decode, overwrite and rate faults are carried in-band and sticky.
  - Plan fix needed: the type's module and content module were both ot_s81hd_mesh_ep, which cannot elaborate.
  - Bench (Verilator 5.050, ot-run epyc1), CHECKED: PASS, 400/401 records x 2 copies bit-exact, 0 faults; the forced m_tx fault shows up in-band. Mutants 1-4 FAIL as required. Max latency 40/42 edges. The CRC-impairment windows produced no replay-visible latency, so replay is not claimed as tested.
- hd_ctl: NOT written, STOP + ASK. Its function cannot be fixed from evidence without inventing contracts:
  - (a) Issue/START authority. The historical ctl starts on "x loaded && !busy". Codex model.json says issue must come from a compiled START/admission contract "owned separately". Which applies?
  - (b) MTP. The 5 draft lanes are removed from the plan, but contents still list dsfd_mtp_seq. What is the current producer/consumer mapping of seed/DHSTEP/DHRES/ROWS?
  - (c) H4 tl_o/ca_i/cb_i (276 b) to the lep IDX master: what does ctl drive and consume?
  - (d) CSR/HFWD/STATUS. The historical ctl took these from host frames; now hd_host is HBC. Which source configures plen/glen/rank/grp/rbase/cal?
  - (e) The landing observer ports (fault/ready) can only be named once (a)-(d) exist. Proposal: the fault input is a bit of ot_s81hd_fault_state_hsf0.other_events_i, and the ready input is the START gate.
  - Also, ctl must flag a missing mesh record at the position's compiled date.
- hd_host: NOT written, ASK. dsdv_hostb_stage_hbc needs job_active/starter_armed, which come from ctl and have no plan bus. It also needs status_t_host/kd, the 1104-b from_prev/local_ro/return_ro rings (the plan has only 2 x coll + 276-b h_tx/h_rx), and compiled BOOT/RETURN dates ( if absent). What is the plan mapping, and who owns the dates?

## [HEAD-RTL-2 2026-10-26 19:50 PDT] CONTRACT NOTE hd_ctl / hd_host (per RULING HEAD-RTL 19:35). Written before the RTL.

Branch claude/head-rtl2-1026 (base claude/head-rtl-1026@fa6598bd6), worktree epyc1:/srv/opentallas-scratch2/claude/wt/head-rtl2-1026.
Sources of every function: historical HSF0 ctl (results/arch/s81_head_source_1025/hsf0_reference, 04718b43a5) and its Codex
extractions on main (xb_ingest, xstore_replay, issued_tags, ar_control = rank_merge + result_landing + fault_state, host276,
best64, mesh64_rx), Codex ot_s81hd_lep0N_core, dsdv_hostb_stage_hbc (S81 s0N instance in ot_s81sl_slice_lepw_mab_hbc_prod_mu_72),
compose_tok_ds / ds_rom_mtp.json token DAG, reset_tree.py START broadcast (decision 13c). New = marked NEW.

1. START (static schedule, ruling 1). Plan delta: reset.start = "broadcast" (die START pin, rides the reset wavefront; every
   mission tap releases at START + its published static release offset). hd_ctl and hd_host get reset.start_role "bootstrap"
   (they must take host config before START, the KV/QC bootstrap rule): raw wavefront reset for link/config/ingest state plus
   ONE registered local START tap, bound to the core input `start_i` (ctl) / `starter_armed` (host). Every other head type
   stays mission. ctl issue dates are static: position k issues its x stream at S + ISS_OFF + k*ISS_PER (S = first edge with
   start_i high; ISS_OFF/ISS_PER are compiled CSRs from the host, NEW CSR 9). No 'x loaded && !busy' start. At its date the x
   store must be complete (xb_ingest loaded_ready) and the previous position retired, else sticky fault (never a stall, never
   a skip). The merge must fire by issue date + MRG_DL (compiled CSR 10 [15:0]); a missing own/peer mesh record at that date
   is a sticky fault (the hd_mesh obligation from the 19:30 note).
2. MTP (ruling 2; compose_tok_ds / ds_rom_mtp.json). The DAG puts draft.head0..4, draft.markov0..4, draft.fixed (group DH)
   and mc.mtp_seq.* on the head die with NO link; RELEASE_RACK + owner leaning: the draft rides copy-B, no draft SerDes.
   Mapping: dsfd_mtp_seq (closed child, unchanged) stays in ctl. RESULT <- merged rank RESULT (result_landing). token ->
   ring lepk_o0 kind K_TOK 5 + RESULT copy to host. SEED and DHSTEP -> ring lepk_o0 kind K_DFT 7 (NEW ring kind; HSF0 type in
   gidx[3:0], frame[527:16] as the 512-b flit; kind 7 is unused on every ring in rtl/). ROWS and DHRES <- ring lepk_i0 kind 7
   frames (same encoding). The 5 draft lanes are not resurrected. GAP (not fabricated): the Markov head (draft.markov*, a
   transfer ratio in the DAG, "no closed hardware") has no RTL anywhere, so no on-die producer of DHRES exists; DHRES/ROWS
   arrive only if a ring producer exists. AR is complete without it (glen 0).
3. lep0N 276-b links tl/ca/cb (ruling 3). Census: only h4_tl__0 ctl.tl_o -> lep0N.tl_i, h4_ca__0/h4_cb__0 back. Codex
   lep0N_core instantiates ot_s81hd_lep_idx_nr with IDX_EN = 0, where tl is unread and ca/cb are constant 0 (generated
   ot_s81hd_lep_nr.sv header: "unread / 0 at IDX_EN 0"); the head has no index rank tree (H4 = layer-die indexer). No
   consumer and no producer -> PLAN ERROR: plan delta deletes the three ports and the six buses; lep0N_core drops the three
   ports and feeds its IDX_EN-0 leaf tl with a declared dead constant (COORD 10-25 dead-input rule: parameter-proven unread).
   unit_o0[44:0] = {mu_c[33:0], mu_rc[10:0]} and ctrl_i0 = mu_rt: as historical ctl/lep0N_core. lepf_o0 = ctl fault -> lep
   sl_f. NEW bus lep_fault_i (Codex head_lep_plan_delta, approved).
4. Config via hd_host = HBC endpoint (ruling 4). host -> ctl on h_rx_i: HSF0 553-b frames over host276 (3 beats, <= 1 frame /
   3 cycles): CSRW (type 6: 0 plen, 1 glen, 2 rank, 3 {ngrp,grp}, 4 rbase, 5 RESULT dest/src, 6 {cal_off,cal_per},
   7 status req, 8 run, 9 {ISS_OFF[31:16]... see RTL}, 10 MRG_DL) and HFWD (type 7, 512-b payload -> ring kind 6 in calendar
   slots). ctl -> host on h_tx_o: RESULT (type 9) and STATUS (type 8) frames, RESULT first, STATUS held (one entry).
   Plan delta: h_tx widened 276 -> 277; bit 276 = registered job_active (xb_ingest: issue -> matching token retirement),
   the S81 HBC job_active function (there hb_status_t_host[65] = issuer busy). Spine ft slot hd 276 -> 277 (8 um gap free).
5. hd_host (ruling 'derive from dsdv_hostb_stage_hbc'). Contents: 2 x dsfd_coll_lane_w_safe8_ntf (HOST0 = HFWD/RESULT plane,
   HOST1 = CSRW/STATUS plane, as historical host lanes 0/1) + dsdv_hostb_stage_hbc ENABLE 1 (HBC1 loader, affine book, RX).
   from_prev = HOST0 HFWD frames formed as kind-6 ring beats {flit at [532:21], kind 6, v} (HBC1 records ride kind 6 by
   contract); to_local (HBC-consumed records removed) -> HFWD frames to ctl; HOST1 CSRW frames pass to ctl only while
   context_valid (config gated by the loaded HBC context). job_active <- h_tx bit 276; starter_armed <- START tap.
   RETURN_LOCAL 0 (no local sequencer status on the head; RETURN_ARRIVAL_DEADLINE needs no date). Compiled dates
   BOOT_HEADER_EDGE / BOOT_COMMIT_EDGE / CLOCK_RESET_ID are parameters published by the host programme (as on S81: the
   prod_mu_72 HBC_* parameters); default all-ones = not admitted, never fabricated. Remaining HBC ring outputs (f_host,
   ks_*, arm_*) have no head consumer: declared observer/dead outputs or a delta, decided in the RTL pass.
6. Observers (ruling task 3): clock-landing observer = module ot_s81hd_ctl, instance u_core, fault_port lep_fault_i
   (feeds fault_state bit 10 = other_events/fault vector; the collector ORs cland_up_fault in), ready_port start_i (the
   START gate; the collector ANDs cland_up_ready in). Both are one-bit inputs already bound to real nets, as gate_observer needs.

## CODEX notes 2026-10-26 20:12 PDT takeover
Root/head_ctl implements approved19:50 contract for ctl/host; mesh realRTL completed fa6598bd6. Strict head bind waits these providers; no synthetic asbuilt.
