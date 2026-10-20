# KV-FUNC-OPENS (Claude 10-19): GEN7 strict functional opens classified and proven

Die: GEN7 strict bound die SHA 7006cbd0 (/srv/opentallas-scratch/claude/kv-exact-padgap-1019/gen7_strict on ot-epyc5). Strict binder = this branch's tools/die_port_bind.py (main + 6 contract names) over the GEN7 source tree, via rebind.sh (same RTL/strap/model inputs; baseline reproduces 45,863/69).

| Class | Unread bits | Open types | Prover / owner |
|---|---:|---:|---|
| (a) relay width padding (literal-0 MSB tail / chain-head lane) | 36,120 | | kv_relay_zero_tail.py |
| (a) landing tie_hi/tie_lo literal outputs | 73 | | kv_relay_zero_tail.py (landing_tie_contract) |
| (a) PVW residual roles (CP/X branch cargo 4,756, reset copy 448, DL bit35 62, cmd zero 56, busy/out_age 34, age_pv 16) | 5,372 | | kv_pvw_residual_roles.py |
| (a) ASTK/head/ECTL roles (kpv lanes 1..15 1,920, ECTL er_addr 384, er_owner tail 384, lt 84, zo 4, hs 1, branch dups 1,170) | 3,947 | | kv_misc_unused_roles.py |
| (a) chain ends / exports with internal consumer (pc er/completion/ko, grp tok/tep, grp_h o_dn, ctl kg, host slice bgo/fo, d2d slot/index) | | 19 (468 pins) | kv_open_tail_roles.py |
| (b) real consumer to wire | 0 | 0 | none found (misc_b.patch = optional kpv lockstep fault fold, not applied) |
| (c) fault/STATUS/admission -> KV-RETIRE | 351 (landing fault outputs) | 50 (kc.kf x4, dcal fault/cal_ready/adm_done/running/layer, d2d recovery_cycles, 43 host_root_admission ports) | landing_faults_for_retire.json, open_ports_classes.json |

Combined chain (zero_tail -> pvw_residual -> misc -> open_tail) on GEN7: unread 45,863 -> 351, output_open 69 -> 50; every other summary field unchanged (input_tied 0, undriven 0, multi 0). Evidence: combined/rebind4_port_bind_v2.txt (unit oth-ubuntu-2014675-1792435938), combined/output_pads.combined_open.json.gz. GEN8: kv_port_bind_v2.sh with OT_KV_STATIC_DIE=1 OT_KV_FUNC_OPENS=1.
ROOT review flags (structural-role calls, not padding): KPV_LOCKSTEP, ECTL_ER_ADDR, SEQ_HS, pc completion_v/we (run phase), d2d att_rx_slot (slot-link source not pinned). Contracts are die-SHA pinned: a GEN8 die must re-derive (provers refuse stale die/source).
