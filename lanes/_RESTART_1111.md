# Restart table 11-11 (limit stop 03:3x)

The old account hit its weekly limit at about 03:30 PST. The owner re-logged in on a new account at 03:35 and said "continue". The automatic Codex handoff (handoff/claude_to_codex_20261111_0335.md) never started work: the Codex pane sat idle at its prompt. COORD set the autoswitch state back to `claude`. Codex has nothing to hand back.

Rule (owner 10-25): no mass resume. Stopped lanes restart as FRESH, short, narrowly-scoped successors, a few at a time, critical path first. Each successor reads its predecessor's last queue posts (grep the tag/lane name in lanes/COORD-REVIEW-QUEUE.md) and COLLECTS the predecessor's running jobs before launching anything. No duplicate launches: check ot-run/ps/docker for the predecessor's units first.

## Stopped lanes (failed on the 429), by priority for the 12:00 cut

| prio | lane | old id | scope / next step | successor |
|---|---|---|---|---|
| 1 | KW-FIX-43 | a45d90b462ee277cc | 12:00 cut src per die (Option A approved 03:3x: main tree at the cut sha + results/ + gen_phys halving-off + overlays; gates: porous+off present, 1 gen dry run per die, hard links only). Batches after the cut. S81 pause until the canonical bind shas exist. epyc2 is place/route only for S81/HBM. Carry vsn6b-s7. | wave 1 |
| 1 | DIE-PROTO-1 | a1ed981c5676cd5ae | S1 die GRT+STA. Running: KV epyc8 (02:48), HEAD hp1d intel1 (03:11). Queued crit: QC Ac, HBM Ac (epyc7), S81 A_crit (epyc7). crit_watch.sh kills old epyc8 waiters by exact PID. Deliver the hd_mesh seam answer to HEAD-92/successor. | wave 1 |
| 1 | DIE-S81-85 | a91ace1d16de86c15 | S81 12:00 event compose (svc deltas composed, launch held; CPL-S81-MISC 6195be42; bk_sel (a) post-cut; lint fixes; stscan by 11:00; COL-H9R0 only if probe+S2 by 11:15; col_h10 x_i0->u_cf S2 item). | wave 1 (with S81 composer prep a928e79f8a849cc1b) |
| 2 | DIE-QC-97 | af5a05b78501cf5e4 | QC 12:00 event (stdir c4519ff4 -> 5677e710, VIS-TRIAGE-QC 6 deltas, cbf_q00 held ARCH). Open: NEWFAIL cbn_q11 post-CTS hold -357/9793 classify; slw_hc1 = STATION-INVERSION. | wave 2 |
| 2 | HEAD-92 | afc51e5f4ec49bbdd | HEAD 12:00 event at 11:30 on l48hp1 (lepB+S03, hd_ctl C1, start_q, H2, hp1 sites); G0/EQ/strict bind/route_supply. Waiters: zlp_eco, h2_eco, spnzp, ctlzp, mesh_a2lec, ds8d. | wave 2 |
| 2 | DIE-HBM-98 | a3a065fd3b4d230a6 | HBM die owner. HBM-COMPOSE (ac0bf1f904c562e1e, not stopped) composes 12:00. Post-cut: phantom-correction event, ft_s0 re-derive (HBM-FTROUTE), 104 missing >405 links. | wave 2 |
| 2 | KW-FIX-44 | ad6ed0127ec3638b8 | Disk reclaim epyc2/epyc4 (archive signed attempts, dead-lane dirs only); localhost image census (af971398 vs fleet 16470cea; read-only first); KIT_TOPOLOGY_BIND_STALE GRT-ARM[off] class. | wave 2 |
| 3 | HBM-CORES-B | adf5204cb4034d7c1 | HBM hard cores; wsw_H13_eco1 provenance (no build commit; record-as-is vs strict); jobs FLC-W2, q3bc_R1, opsbg_C3 on epyc8. | wave 3 |
| 3 | CPL-KV-PV | a95826861b530717e | kv3_pv: pv_v2_base GRT ov 3,131,015; 5 arms pending (waiter bzmyjne7z). If no orders-of-magnitude cut -> REDESIGN to DIE-KV. | wave 3 |
| 3 | CPL-S81-MISC | a3e6a26befbd79fbb | 4 GRT probes on epyc8; bk_sel (a) is post-cut. | collect only |
| 3 | CPL-S81-STN | a980198507b8afb97 | t51 intent deltas. | wave 3 |
| 3 | CPL-QC-2 | a4c91a177a94a748a | QC clean-slate split. | wave 3 |
| 3 | CPL-HBM-2 | abe27818a9f92c359 | spb2/spt0 GRT probes. | wave 3 |
| 3 | VIS-TRIAGE-S81 | a794dde66c3e212e6 | COL-H9R0 r0_new/r0_stock probes (normal queue); READY 8ba82dd0af93. | collect only |
| 3 | VSN6-B | a9cbf3359c33eb2f9 | vsN6 form4 (READY 855a498 approved, merging). | wave 3 |
| 3 | HOOK-L14Q | a080e157195ab451d | serdes bind hook (BMC pinned Yosys 0.68). | wave 3 |
| 4 | others | | q_sm MPL-0020 a0fcf082e21c90ff1, BATCH4b a8dd6c618a844a622, BIND-SUBTYPE-2 af87cb1a90cc6f033, vsN2 a515006766b3a318c, QC glue LEC a071b1eaf08569199, s_4N ft-lane a2d211e86a3248e9e, NW/NE_io halo ac5ab0838823bde5b (30 um ring wins; build nw_a30/ne_a30), HBM channel geometry a344d05e40e844b29 (rev 3 post), h9 ROM a51a23e2c40dae5e3, S81 27 late-tap a337b26c802378498, dma banks_cp a875bb5841e152f0b, sle_fw_v3 a685f8bf202423497 | later waves, one family at a time |

## Not stopped (idle or running; they wake on their own waiters)
ROOT-MERGE-57 a34d486710e981f85, FEAS-AUDIT-1 aea7437779f984bd0, HBM-COMPOSE ac0bf1f904c562e1e, STATION-FIX-HBM a97107ca43adbf276, S81 inverted chains a15d38f573a804a60, QC die over-reach a1f1c396e8f7f0ff6, S81 G0C lineage ab7c3fc17b284a993, HBM-FTROUTE a406784901225fca3, CORE-PLACE-1 a6ffa4d5273d9cdd5, S81-SVCRS-3 a014f7b88c14d3bc0, CPL-S81-SVC ae9708bb5342e0559, GRT-PATCH-1 af44f24231f26cb2f, VIS-TRIAGE-HBM afb7fffbbb972b85e, CPL-S81-SLICE a9848a0a1b394cc98, ab8dc4d7fc4018b19.
