# Ordinary KV DCAL bc2 frozen native audit

The ordinary component is CLOSED, but is **not SAFE32 ready and is not qualified for parent adoption**. Frozen source 569419a7d, record43122e84b, automatic merge0677219da, job `qkd_d2d_cal_seq_pin_bc-bc2-569419a7d`; terminal verdict batch20261019_081308. This packet performs read-only pickup; no new gate, route, source change, REVIEW, or submission.

| Frozen routed evidence | Result |
|---|---:|
| TT setup / FF hold | +161.00 / +27.38 ps |
| DRC | 0 |
| TT native launch / capture | 178.48784 / 126.14655 ps |
| FF native launch / capture | 126.96046 / 93.63660 ps |
| TT / FF measured boundary spread | 5.1 / 5.1 ps |
| TT native violating launch>220 / capture>190 | 0 / 0 |
| TT / FF combinational ETM pins | 0 / 0 |
| SS sensitivity setup | -145.71 ps |

`native_etm.py` reads the committed actual TT/FF/SS exported routed libraries, subtracts measured launch insertion and adds measured capture insertion using `tools/hier_contract/pinreg_audit.py`. `native_etm.json` retains every pin, clock reference, and export SHA. This establishes own-boundary timing only; parent-relative clock mismatch remains unmeasured. SS launch268.89719 ps and negative SS setup are sensitivity evidence, not TT/FF qualification failures or an SS closure claim.

Fleet read-only OpenROAD census in `odb_census.py` and `odb_census.json` pins both actual1_synth and6_final ODB hashes. On ot-epyc7 the completed units are oth-ubuntu-3211158-1792430880 (initial census) and oth-ubuntu-3212461-1792430935 (explicit clock exclusion). The first attempted unit3210438 exited1 on an ODB Python rectangle accessor; no original files were touched. Final293FF versus source253FF is explained by original `3_3_place_gp.log`:40 output pins were split to cloned flops (80cells added,29loadless removed). The additional FFs are not reset source replicas.

**Source/reset blocker:** source reset net `u_ot_pr_core.release_q\\[1\\]` has206 reset sinks through inverter2647; `rst_n__ot_rl1\\[0\\]` has45 reset/set sinks through inverter2738. TIEHI1461 has252static loads, reported separately from functional control/reset. All final immediate nonclock net loads<=32, but physical reset buffering does not replace source-owned reset replication/ownership. The old spec's40-load noncritical waiver cannot discharge current SAFE32. External reset entry has a generated two-register landing wrapper; the RTL adds its own two-register release before the inner sequencer. Source-safe replication must preserve the existing reset/program edges and independently prove initialization; no proposed extra latency or HOLD/IGNORE change is adopted here.

**Actual GEN7 binding:** `gen7_binding.json` pins the read-only4db097403 case's current die and binding report. Actual masterqkd_dcal is REAL qkd_d2d_cal_seq_pin_bc, no missing inputs/widths. Actual flags include DCAL_BC/DCAL/STATIC_DIE/MU=1. Instance wiring includes btx/brx/bad/bdt from boot link_cfg relays and merged dcfg to the link, tok_start to n_ks_lprg_st, central clockn_clk_core_c and resetn_rrs_n_rst_link_t0__m_0__s0[0]. However **fault is unread**, along with adm_done/cal_ready/layer/running. Thus the tile's COL/RUN/STALE/EARLY sticky faults are not connected to a parent consumer in this case. Parent fault fold, reset clearing, admission/STATUS schedule and relative native clocks remain open. Relevant current tool mapping is `tools/qwen_kv_die/kv_die.py:dcal_binding`:EP_SKEW3/GO_OFS0/MUT0, defaultSTART_ADJ,21.6x34.56 slot.

Functional frozen daemon bench logs are retained under `benches/`: primary PASS bootwrites66/admissions2/tokens2/layers36/events2809/runtime_writes6 on Verilator5.050; all five expected-failure witnesses detect dropped runtime writes, stale boot image, collision, write-while-running and admission-before-base. These are the already-completed exact source tests, not new whole-die token evidence.

Geometry PNGs were viewed from the committed original kit:21.6x34.56um, no macros, one full standard-cell region, W/E signal faces, S-center clock beside the cell region; aspect1.60. Original measured synthesis265um2/core522.5472um2=50.7%; exported child lint PASS with no pin blockage/access violation, seven M5VDD and seven M5VSS stripes. Actual routed pin rectangles are retained in census. No SRAM/macro contact obligation exists in this leaf. Parent slot and physical pin maps must still bind the exact frozen view.

This is the ordinary AW11/32-entry configuration source. It is not an expanded OVL AW12 calendar and cannot be reused under changed included image/constants or ports without exact source-bound requalification. The actual GEN7 transport still has the separate TXDP21-versus-required22 mismatch; this packet does not fix or waive it. `/root/kv_ovl_closure` retains expanded OVL ownership.

Frozen remote route root (read-only): `/srv/opentallas-scratch/claude/closure-loop/qkd_d2d_cal_seq_pin_bc-bc2-569419a7d/routes/qkd_d2d_cal_seq_pin_bc_bc2_569419a7d/work/orfs`; actual data under `results/asap7/opentallas_qkd_d2d_cal_seq_pin_bc_asap7_ref_qkd_d2d_cal_seq_pin_bc_bc2_569419a7d/base`. All own audit jobs terminal.
