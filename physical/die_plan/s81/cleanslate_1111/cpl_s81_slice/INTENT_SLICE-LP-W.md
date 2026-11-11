# INTENT SHEET SLICE-LP-W (CPL-S81-SLICE, plan 99f40d35071d)

Delta: `delta_SLICE-LP-W_99f40d35.json` sha256 `ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356`; adopted types 0/2.

**Dataflow.** S face coll_i<k> (514 b, staged) -> ln<k> (coll_lane, M5 OBS) -> lnl<k> (inland, 559 b, ~105 um) ->
the lep SRAM banks (558 b; banks broadcast 557 b back to every lnl) ; ln<k> -> coll_o<k> (512 b) back out of the S face.
E face lepk_i0/lepk_o0 (2 x 1104 b) + lepf/flt/lpc feed the lep SRAM banks directly (p2p, no core on the path).
**Timing-critical pairs:** coll_i -> ln stations, ln<->lnl (559 b), lnl<->lep banks (400-800 um, the longest).
**Intended layout:** four lanes side by side over their own S windows, each lnl directly above its ln, lep banks above the
lnl row, and the E-face lep windows AT the lep bank rows.  In lepw_mus_LP__t2 the E windows sit at y 6-538 against ln3
(15-um street, 86 um needed for 2212 b): the lep traffic must cross the lane row -> GRT 463k overflow (class F).
Placement cannot fix this without breaking the lane chain (intent search: no legal improvement) -> REDESIGN: move the
two 1104-b windows lepk_i0/lepk_o0 (and the abutting lepw_mus_C__t1 W-face lepk windows + the 2 die ports kd_s_0S__0 /
ku_s_0S__0, same y) up by 622.08 um (72 x 8.64) to y 628-1109, beside the lep banks; the 1-2 b lepf/flt/lpc control
windows stay at y 488-538 next to the lnl rs_k/flt pins (moving them too created R3 >405-um bundles in G0C).  With no core
move the entry jam is gone (entry 1.825 -> 0, model cost 2.825 -> 1.0) and the C partner's W jam over capc5r clears too.
lepw_mu_LP__t2: the fine-tune delta made G0C R3-INTERNAL bundles ln.rx -> lnl.n_rxv >= 499-577 um (worst bit) -> dropped, KEEP.

## Per type

| type | moved | bit-mm | worst cut V/H | entry | rs p99 | chain corr | longer links | SVG |
|---|---|---|---|---|---|---|---|---|
| dsdv_slice_lepw_mus_LP__t2 | 0 | 4194.5 -> 4194.5 | 0.245/0.3 -> 0.245/0.3 | 1.825 -> 1.825 | 0.928 -> 0.928 | None -> None | 0 | dsdv_slice_lepw_mus_LP__t2_after.svg |
| dsdv_slice_lepw_mu_LP__t2 | 0 | 3776.5 -> 3776.5 | 0.242/0.261 -> 0.242/0.261 | 0.0 -> 0.0 | 1.058 -> 1.058 | None -> None | 0 | dsdv_slice_lepw_mu_LP__t2_after.svg |

## Dataflow links of dsdv_slice_lepw_mus_LP__t2 (top 30 by bits; length um before -> after)

| src | dst | bits | role | len |
|---|---|---|---|---|
| core:lnl1 | core:ln1 | 1071 | p2p | 444 -> 444 |
| core:lnl3 | core:ln3 | 1071 | p2p | 444 -> 444 |
| core:ln0 | core:lnl0 | 559 | p2p | 105 -> 105 |
| core:ln2 | core:lnl2 | 559 | p2p | 105 -> 105 |
| core:lnl0 | macros@669,801 | 558 | p2p | 722 -> 722 |
| core:ln1 | core:lnl1 | 558 | p2p | 105 -> 105 |
| core:lnl1 | macros@669,801 | 558 | p2p | 411 -> 411 |
| core:lnl2 | macros@669,801 | 558 | p2p | 500 -> 500 |
| core:ln3 | core:lnl3 | 558 | p2p | 105 -> 105 |
| core:lnl3 | macros@669,801 | 558 | p2p | 811 -> 811 |
| macros@669,801 | core:lnl0 | 557 | broadcast | 722 -> 722 |
| macros@669,801 | core:lnl1 | 557 | broadcast | 411 -> 411 |
| macros@669,801 | core:lnl2 | 557 | broadcast | 388 -> 388 |
| macros@669,801 | core:lnl3 | 557 | broadcast | 699 -> 699 |
| core:lnl0 | core:ln0 | 556 | p2p | 205 -> 205 |
| core:lnl2 | core:ln2 | 556 | p2p | 205 -> 205 |
| face:coll_i0 | core:ln0 | 514 | p2p (staged station) | 131 -> 131 |
| face:coll_i1 | core:ln1 | 514 | p2p (staged station) | 131 -> 131 |
| face:coll_i2 | core:ln2 | 514 | p2p (staged station) | 131 -> 131 |
| face:coll_i3 | core:ln3 | 514 | p2p (staged station) | 131 -> 131 |
| core:ln0 | face:coll_o0 | 512 | p2p | 130 -> 130 |
| core:ln1 | face:coll_o1 | 512 | p2p | 130 -> 130 |
| core:ln2 | face:coll_o2 | 512 | p2p | 130 -> 130 |
| core:ln3 | face:coll_o3 | 512 | p2p | 130 -> 130 |
| core:lnl1 | core:lnl0 | 2 | serialisable (control/status) | 311 -> 311 |
| core:lnl3 | core:lnl2 | 2 | serialisable (control/status) | 311 -> 311 |
| core:lnl2 | core:lnl0 | 1 | serialisable (control/status) | 812 -> 812 |
| core:lnl3 | core:lnl0 | 1 | serialisable (control/status) | 1123 -> 1123 |
| face:lpc_i0 | core:lnl0 | 1 | serialisable (control/status) | 1409 -> 1409 |
| core:lnl2 | core:lnl1 | 1 | serialisable (control/status) | 501 -> 501 |

## Timing-critical pairs of dsdv_slice_lepw_mus_LP__t2

- {"kind": "plan station", "conn": "bus:coll_i0", "launch": "face flop", "capture": "u_bound.u_u_ln0.rx", "stages": 1, "bits": 514}
- {"kind": "plan station", "conn": "bus:coll_i1", "launch": "face flop", "capture": "u_bound.u_u_ln1.rx", "stages": 1, "bits": 514}
- {"kind": "plan station", "conn": "bus:coll_i2", "launch": "face flop", "capture": "u_bound.u_u_ln2.rx", "stages": 1, "bits": 514}
- {"kind": "plan station", "conn": "bus:coll_i3", "launch": "face flop", "capture": "u_bound.u_u_ln3.rx", "stages": 1, "bits": 514}
- {"kind": "plan station", "conn": "bus:lpc_i0", "launch": "face flop", "capture": "u_bound.u_u_lnl0.rs_k", "stages": 3, "bits": 2}
- {"kind": "link beyond 396.9-um reach", "src": "core:lnl1", "dst": "core:ln1", "bits": 1071, "len_before": 444, "len_after": 444}
- {"kind": "link beyond 396.9-um reach", "src": "core:lnl3", "dst": "core:ln3", "bits": 1071, "len_before": 444, "len_after": 444}
- {"kind": "link beyond 396.9-um reach", "src": "core:lnl0", "dst": "macros@669,801", "bits": 558, "len_before": 722, "len_after": 722}
- {"kind": "link beyond 396.9-um reach", "src": "core:lnl1", "dst": "macros@669,801", "bits": 558, "len_before": 411, "len_after": 411}
- {"kind": "link beyond 396.9-um reach", "src": "core:lnl2", "dst": "macros@669,801", "bits": 558, "len_before": 500, "len_after": 500}
- {"kind": "link beyond 396.9-um reach", "src": "core:lnl3", "dst": "macros@669,801", "bits": 558, "len_before": 811, "len_after": 811}
- {"kind": "link beyond 396.9-um reach", "src": "macros@669,801", "dst": "core:lnl0", "bits": 557, "len_before": 722, "len_after": 722}
- {"kind": "link beyond 396.9-um reach", "src": "macros@669,801", "dst": "core:lnl1", "bits": 557, "len_before": 411, "len_after": 411}
- {"kind": "link beyond 396.9-um reach", "src": "macros@669,801", "dst": "core:lnl3", "bits": 557, "len_before": 699, "len_after": 699}
