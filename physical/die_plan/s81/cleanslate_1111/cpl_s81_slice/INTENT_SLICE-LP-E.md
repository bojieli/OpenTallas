# INTENT SHEET SLICE-LP-E (CPL-S81-SLICE, plan 99f40d35071d)

Delta: `delta_SLICE-LP-E_99f40d35.json` sha256 `ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356`; adopted types 0/2.

**Dataflow.** Same lane structure as LP-W: S face coll_i<k> (staged) -> ln<k> -> lnl<k> (559 b) <-> lep SRAM banks;
ln<k> -> coll_o<k>.  **Timing-critical pairs:** coll_i -> ln stations, ln<->lnl, lnl<->lep banks.  **Intended layout:**
lanes over their S windows, lnl above its ln, banks above (= the plan).  The intent fine-tune (shift <=250 um, no flip,
links >=32 b within 1.2x+20 um and reach) found nothing for lepe_mu_LP__t2, and its lepe_nh_mus_LP__t1 result made G0C
R3-INTERNAL bundles (ln.rx -> lnl.n_rxv worst bit 572-607 um > 405) -> dropped: KEEP both.  Before evidence for
lepe_nh_mus_LP__t1: routed DB job 50acdf2cf527 (epyc2 kw43-wave-1109n attempt_7, 11-11 01:13) failed GRT-0116 with total
overflow 48123 (M6 46799), hot band between the lnl cores and the SRAM bank rows (the lnl<->bank links).  The failure is not a placement class: the signed coll_lane view (dsfd_coll_lane_e_safe8_ntf_signed_1107)
carries solid OBS on M1-M6 (COORD queue, DRT-0073 item), so over the two ln cores only M7 is left and every H route between
the lnl/bank row and the E/W faces detours around them -> fix in the view (OBS only to M5, like the plan assumes) or a
die-owner window move; no core move under the intent rule.

## Per type

| type | moved | bit-mm | worst cut V/H | entry | rs p99 | chain corr | longer links | SVG |
|---|---|---|---|---|---|---|---|---|
| dsdv_slice_lepe_mu_LP__t2 | 0 | 3758.9 -> 3758.9 | 0.242/0.261 -> 0.242/0.261 | 0.0 -> 0.0 | 1.058 -> 1.058 | None -> None | 0 | dsdv_slice_lepe_mu_LP__t2_after.svg |
| dsdv_slice_lepe_nh_mus_LP__t1 | 0 | 2383.3 -> 2383.3 | 0.141/0.164 -> 0.141/0.164 | 0.0 -> 0.0 | 1.076 -> 1.076 | None -> None | 0 | dsdv_slice_lepe_nh_mus_LP__t1_after.svg |

## Dataflow links of dsdv_slice_lepe_mu_LP__t2 (top 30 by bits; length um before -> after)

| src | dst | bits | role | len |
|---|---|---|---|---|
| core:lnl0 | macros@763,408 | 560 | p2p | 826 -> 826 |
| core:ln0 | core:lnl0 | 560 | p2p | 111 -> 111 |
| core:lnl1 | macros@763,408 | 560 | p2p | 515 -> 515 |
| core:ln1 | core:lnl1 | 560 | p2p | 111 -> 111 |
| core:ln2 | core:lnl2 | 559 | p2p | 110 -> 110 |
| core:ln3 | core:lnl3 | 559 | p2p | 110 -> 110 |
| core:lnl2 | macros@763,408 | 558 | p2p | 415 -> 415 |
| core:lnl3 | macros@763,408 | 558 | p2p | 726 -> 726 |
| macros@763,408 | core:lnl0 | 557 | broadcast | 826 -> 826 |
| macros@763,408 | core:lnl1 | 557 | broadcast | 515 -> 515 |
| macros@763,408 | core:lnl2 | 557 | broadcast | 303 -> 303 |
| macros@763,408 | core:lnl3 | 557 | broadcast | 614 -> 614 |
| core:lnl0 | core:ln0 | 556 | p2p | 209 -> 209 |
| core:lnl1 | core:ln1 | 556 | p2p | 209 -> 209 |
| core:lnl2 | core:ln2 | 556 | p2p | 209 -> 209 |
| core:lnl3 | core:ln3 | 556 | p2p | 209 -> 209 |
| core:ln0 | face:coll_o0 | 512 | p2p | 134 -> 134 |
| core:ln1 | face:coll_o1 | 512 | p2p | 134 -> 134 |
| core:ln2 | face:coll_o2 | 512 | p2p | 134 -> 134 |
| core:ln3 | face:coll_o3 | 512 | p2p | 134 -> 134 |
| face:coll_i2 | core:ln2 | 258 | p2p | 135 -> 135 |
| face:coll_i3 | core:ln3 | 258 | p2p | 135 -> 135 |
| face:coll_i0 | core:ln0 | 172 | p2p | 135 -> 135 |
| face:coll_i1 | core:ln1 | 172 | p2p | 135 -> 135 |
| core:lnl1 | core:lnl0 | 2 | serialisable (control/status) | 311 -> 311 |
| face:coll_i0 | core:lnl0 | 2 | serialisable (control/status) | 790 -> 790 |
| face:coll_i1 | core:lnl1 | 2 | serialisable (control/status) | 790 -> 790 |
| core:lnl3 | core:lnl2 | 2 | serialisable (control/status) | 311 -> 311 |
| core:lnl2 | core:lnl0 | 1 | serialisable (control/status) | 812 -> 812 |
| core:lnl3 | core:lnl0 | 1 | serialisable (control/status) | 1123 -> 1123 |

## Timing-critical pairs of dsdv_slice_lepe_mu_LP__t2

- {"kind": "plan station", "conn": "bus:coll_i0", "launch": "face flop", "capture": "u_bound.u_u_ln0.rx", "stages": 1, "bits": 514}
- {"kind": "plan station", "conn": "bus:coll_i1", "launch": "face flop", "capture": "u_bound.u_u_ln1.rx", "stages": 1, "bits": 514}
- {"kind": "plan station", "conn": "bus:coll_i2", "launch": "face flop", "capture": "u_bound.u_u_ln2.rx", "stages": 1, "bits": 514}
- {"kind": "plan station", "conn": "bus:coll_i3", "launch": "face flop", "capture": "u_bound.u_u_ln3.rx", "stages": 1, "bits": 514}
- {"kind": "plan station", "conn": "bus:lpc_i0", "launch": "face flop", "capture": "u_bound.u_u_lnl0.rs_k", "stages": 3, "bits": 2}
- {"kind": "link beyond 396.9-um reach", "src": "core:lnl0", "dst": "macros@763,408", "bits": 560, "len_before": 826, "len_after": 826}
- {"kind": "link beyond 396.9-um reach", "src": "core:lnl1", "dst": "macros@763,408", "bits": 560, "len_before": 515, "len_after": 515}
- {"kind": "link beyond 396.9-um reach", "src": "core:lnl2", "dst": "macros@763,408", "bits": 558, "len_before": 415, "len_after": 415}
- {"kind": "link beyond 396.9-um reach", "src": "core:lnl3", "dst": "macros@763,408", "bits": 558, "len_before": 726, "len_after": 726}
- {"kind": "link beyond 396.9-um reach", "src": "macros@763,408", "dst": "core:lnl0", "bits": 557, "len_before": 826, "len_after": 826}
- {"kind": "link beyond 396.9-um reach", "src": "macros@763,408", "dst": "core:lnl1", "bits": 557, "len_before": 515, "len_after": 515}
- {"kind": "link beyond 396.9-um reach", "src": "macros@763,408", "dst": "core:lnl3", "bits": 557, "len_before": 614, "len_after": 614}
