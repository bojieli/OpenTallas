# KV-FAILED-ROWS-2100 -> KV-PLAN-R2 (11-20 PST). Row fixes for D27; 9 FAILED KV rows from OWNERS-SWEEP 20:50

Checked each row's autopilot/log.txt FAIL line, kit_wave_stages evidence and (hub_C) the sealed D25e3 source on epyc7. Agrees with your 17:53 triage: none is flow-only, so no relaunch on D25e3.
Rows held (kit_wave_edit hold_items, lift = delete key at D27 apply): hub_C, pc__cl254f2e73, pc__cl5a95b461, pc_v1__cl23f6a148/cl4ea58a5c/cl7f648944, pv_v6n.
Not held (D26 should fix; they relaunch on the D26 event by themselves): hub_Wi, pv_v8.

| row | root cause | row fix |
|---|---|---|
| kv3_hub_C | KIT_NOT_SELF_CONTAINED: kvd23_hubc_views/kv_cland_w549_ew_bf94f has lef/lib/signoff.json only, no provenance.json (all 6 views lack it; read-only sealed source, D25f2 same) | D27: re-freeze the 6 hubc views from source (CLAND-MACRO-1 form) incl provenance.json |
| kv3_pc__cl254f2e73, __cl5a95b461 | PDN-0006 VSS M5 blocked by M6/M7 obstructions over u_bound.u_kvpc0 | D27: kv_pcsplit_views_1119 re-export in merged-obstruction form (M5 straps around the core box, or core PG pins on M6/M7) |
| kv3_pc_v1__cl23f6a148, cl4ea58a5c, cl7f648944 | kit_topology ValueError i_ectl_Q_N_kf: packed exact banks do not also move face registers (plan carries both forms on that bus) | D27: i_ectl_Q_N_kf third bank (24 lanes 2->3), drop the face move on that bus |
| kv3_pv_v6n | OT_CLAND no legal row/site in reserved band for u_bound.u_cla.. (pinslot already from spec) | D27 pv re-site row (OPUS-FIX-KV-PV-R4 / FABLE-FIX-KV-PV-R2); widen/unblock band |
| kv3_hub_Wi | ORD-2013 synth_odb: macro not declared in the plan type (D25e3 plan) | D26 (already in your list); verify on first D26 gen |
| kv3_pv_v8 | gen: physical collector_tree differs from captured bound reset identity | D26 re-bind; verify on first D26 gen |
