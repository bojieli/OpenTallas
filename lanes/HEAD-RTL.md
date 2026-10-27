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
