# VIS-ROM: closure-blocking (severity-1) findings, status

Updated 2026-10-16 02:45 PT. Maintained by VIS-ROM. The table is updated as owners reply and route/gate verdicts land; the full evidence is in `findings.json`.
State values: **fixed-routed** (fixed and the route closed or improved on the cited metric) · **fix-in-gate** (fix built; gate or route running, or the gate improved but the tile is not closed) · **not-started** · **refuted** (the finding was wrong, with the evidence).

| finding | die | master | owner | state | evidence (before -> after, job) |
|---|---|---|---|---|---|
| QC-01 | Qwen compute | qfd_tile_nk rp2_45 | Q-COMPUTE-DIE | fix-in-gate | W glue strip fixed by the r3 fences (8a47f4f41): DPL illegal cells 170 -> 92, the W strip is clean, and the remaining cells sit in the LSL pin gutters. The tile still fails DPL-0033. The next step is the r4 macro repitch, which is at risk from QC-11: its side-by-side LSL abutment fails the kit's floorplan check. |
| QC-02 | Qwen compute | qfd_tile_nl rp2_45 | Q-COMPUTE-DIE | fix-in-gate | r3: illegal cells 96 -> 53. Still DPL-0033; the remaining cells are in the LSL gutters. Next is r4: tap glue moves into the empty NE slot and the ROM-top band widens. |
| QC-05 | Qwen compute | qfd_xs_tap | Q-DVM+LINK | fix-in-gate | xt10 (21bec030e): S bus 26.5 -> 159 um (20.9 -> 3.5 pins/um), ck at the N-face centre. Gate WARN with 0 FAIL: setup +120.3, hold +12.9 ps, ck insertion 294 ps. Waiting for the route and native audit (pass-1 capture was 502 ps). |
| D-QC-02 | Qwen compute | die n_rst_field fan-out | Q-COMPUTE-DIE | refuted (pending measure) | The 1,585-terminal net came from a RELAY-SKIP diagnostic: `_reset_tree()` returns early under OT_RELAY_SKIP=1. The FULL generations r2h1/r2h2/r2h3 build a registered tree. This becomes final when their GEN reports rst_field fan-out and reset_over_500=0. Still open inside it: xcol rst_n is declared INOUT in the abstract. |
| QKV-01 | Qwen KV | qkd_pv (2x16 PV column) | Q-KVSYS-DIE / Q-ELEM | not-started | 1144.8x9309.6 um vs 8987.7 um of north clear height (-321.9 um). The owner's N/S split candidate pvw0/pvw1 (1080x8640) exists, but the south spine is 1,287 um wide against the 1,598 um it needs. No placement has changed. This is decided by the kvs11 die trial (still at PDN) or a split-PV case. |
| QKV-02 | Qwen KV | qkd_ectl_a_tp8_epoch_direct | Q-ELEM | not-started | The manual recovery is stuck at 4 DRT shorts (no change since 10-15 23:12). The re-pin kit (row buses split over both SRAMs, rs on two layers) has not been built. |
| QKV-03 | Qwen KV | qkd_d2d_static | Q-KVSYS-DIE | not-started | Moved from Q-DVM+LINK to this owner. 45 GRT overflows in the 20 um SRAM channel, and nothing has run since r1sp-r3sp. Fix: a channel of 40 um or more. |
| QKV-04 | Qwen KV | qkd_rly_* relays | Q-KVSYS-DIE | not-started | The kvs11 elements.lef still has rly_2089 with 4,178 M4 shapes on a 105.8 um face (20.9 pins/um). The abstract needs regenerating at 8 pins/um/layer or less. |
| QKV-13 (r2) | Qwen KV | return_slots mc_r3 | Q-KVSYS-DIE | not-started | Running in the loop as submitted: one reset flop drives 8,940 loads, and in->reg is -69.5 ps at the gate. (sev2: listed here because it was submitted before its images were checked) |
| S81F-01 | S81 | relay faces (rly_283/266_EW + small relays) | S-DIE | not-started | Generator fc() at tools/dsrom_s81_fulldie.py ~L6986 is unchanged on main, and branch claude/sdie-relayface-0030 has no commits. 100% of input bundles face away (~835k bits); native launch is 243/237 ps. |
| S81F-02 | S81 | dsfd_cfifo | S-ELEM-PQ | not-started | The die binds --cfifo-v2, but no closed v2 view with xd2/xf2 exists, so 68,864 bits are unbound. |
| S81H-01 | S81 | dsfd_host_c | S-ELEM-PQ | not-started | 4 CTS roots, 22,965 hold violations left. An n5 job.json is prepared (1c8f71915) but not submitted, with no evidence the clock roots were merged. |
| S81H-02 | S81 | dsfd_stage_seq_static c9/c10 | S-ELEM-PQ | not-started | c9 FLOORPLAN_MARGIN at 66% util. The c10 RTL is larger again, and no grown-outline c10 kit or gate exists. |
| S81H-14 (r2) | S81 | dsfd_vm_static_wfc_ctl | S-VM | not-started | Owner confirmed: e_q in the serial domain samples x43f, vm_fault and x34f from the core domain (OT_MULTI_ROOT refusal). It needs a structural CDC fix and was not resubmitted. |

**Summary:** 14 rows. 3 fix-in-gate, 1 refuted (pending its measurement), 10 not-started, 0 fixed-routed yet.
The two largest open levers are S81F-01, a single generator fix that changes ~3,000+ relays, and QKV-04, a single abstract regeneration for every KV relay.
