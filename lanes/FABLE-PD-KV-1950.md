# FABLE-PD-KV-1950: KV D25e / D25e2 structural review (2026-11-19 19:50 PST)

Scope: technical PD, read-only. No build, no STA run, no plan edit.
Read: D25e plan a5a8c6b96e5f and D25e2 plan 7805ac468855 (epyc8 kw45/src_kv_pin_eb1e73448bd0_hg12_7805ac46_t7ceb180_d25e2:
plan_c.json, eW_sidecar.json, tools/), compose logs (epyc8 kv-d23-compose8), k8/k9 kits (epyc9 opus-kv-hg), v8b/v8d kits
(epyc8 fable-fix-kv-pv-1119/compose/kit), ROWS-KV-SIDECAR-FALL.json, lane posts to 19:31.
"Checked" = computed here from those files. "Post" = taken from a lane post, not re-derived.

## 0. State at 19:46

- D25e (a5a8c6b96e5f): strict bind still running on epyc10 (started 01:49Z). No verdict.
- D25e2 (7805ac468855): the first strict bind (03:22Z, elab RC 0) was stopped about 19:33; the tree is being re-tooled to main
  a2fb7e6 (cp + delta-apply running). The plan is unchanged so far. So the compose window is still open.

## 1. What D25e2 carries (checked in plan 7805ac468855)

| item | in plan | evidence |
|---|---|---|
| hg section L + M on kv3_hgi_v1 x2 | YES | reg_leaf_split 2 leaves x 3 copies, 2 polylines, 64 pd2 keys, eq key (44,40), tN regs (133,1270.08),(200,950) |
| kst alias keys dropped | YES | 1904 keys per hg/hgi type (hgi_v1 1969) |
| pv +500 | YES | 128 pv -> hub_C lanes, +500 (26..38 per type) |
| 32 fall K rows | YES | 30 ports K-1 / sched_lat-1, 2 ports K+1 / sched_lat+1, depth unchanged |
| tools >= 6e2f4ee27af8 | YES | tree tools carry reset_replicate tail_clear and ot_dp_dly_keep (TRUNK-CHAIN) |
| 16 pv tail_clear "sync" rows | NO | all 16 kv3_pv* reset_replicate rows are {rsync, copy_depth 4}, no tail_clear key |
| core-tap v2 rows (24 pcc pins) | NO | kv3_pc* core taps still 318 / 320 (pcc), 193 / 196 (pcf) |
| pc sink offsets v2 (+30 / -64) | not a plan item | tree side; DIE-CORETAP has not rebuilt the tree |

The tail_clear key is read in bind.py (emit_type calls reset_replicate), so it is a bind-time row. If the strict bind
restarts without it, class R costs one more 2.5-h bind. Add the 16 rows (FABLE-FIX-KV-PV-rows_R.py) before the restart.

## 2. Conflict checks on the composed rows

| check | result |
|---|---|
| M sites against the 18 hard cores of hgi_v1 (both types) | PASS. 6 split sites, 7 polyline vertices, 6 segments, pd2 (40,340) / (60,700), eq (44,40), tN regs: 0 inside a core, 0 segments cross a core |
| M hops | tN 142.9 / 387.1 / 82.0 um. k9 hooks: hst2 path 501 um, hop 250; hst3 path 788 um, hop 394 (11 um under 405). Reset tree max placed hop 289 |
| pv station hops, 16 types | PASS. 0 internal_station hops over 405 (Manhattan). Post: routed max 404.5 |
| K against latency | PASS. Lane latency delta = K delta on 32 / 32 ports; sidecar added_cycles changed on the same 32; row base K = D25e sidecar K on 32 / 32; all other count_aligned keys identical |
| fall margins after the rows | min lo +912, min hi +601 ps (need 100), computed from the rows file. A 38 ps move from offsets v2 cannot break them |
| latency total | 172 lanes, +484 = pv +500 (128), hgi tN +12 (12), fall -30 +2. Lane pads changed 0. Matches the compose post |
| reset form | hgi_v1 raw branches end on cland_reset_ft0_i (both types), as the 041f1eefb09 fix intends. tail_clear not present, so nothing to check against consumers yet |

Findings that are not D25e2 regressions (same in D25e):
- 544 kst relay_sites keys per hg / hgi type (476 on kv3_hgi) and 4 kt station rows lie 20 to 63 um inside the head_e2 /
  head_e4 outlines (x 185.76 and 807.84; lanes e4 -> e0 and e6 -> e0). k7 / k8 show 0 kt ends at CTS, so the legaliser moves
  them and timing holds. Advisory: re-site to the y 553-683 channel when the e0 core is re-hardened.
- tN station hop 409.8 um on 7 hgi types (v2 x2, v3 to v7); hub_Eo 420.4 / 408.9; hub_Wo 408.6.

Pairing rule (not a conflict today): plan pcc 318 and the pcsink_fix tree (+68 / -54) are one consistent set. Core-tap v2
(279.5, target +30) and offsets v2 must land in the same event. One without the other shows 38 ps of false pcc skew in
declared-insertion die STA (S81 cw6: -242 -> -508 for this reason).

## 3. Blockers after D25e2

### pv

| rank | class | root cause | measured evidence | fix | owner |
|---|---|---|---|---|---|
| 1 | -675 (v8b) / -629, final -533 (v8d) | TRUNK-CHAIN tool defect, not a floorplan class | Checked: in both tt_setup_repair logs every worst endpoint (103 / 185 iterations) is u_pd3_i_pvw_u_ctl_cmd_*_pvg*_p*_*.r[0]/D. OT_TAIL_SITE merged 32 in both kits | Already on main 1b95661b75 and in the D25e2 tools. Needs the D25e2 bind, then one kv3_pv_v8 kit. Accept: merged 0, worst endpoint leaves the pd3 class. No kit has shown it yet | FABLE-FIX-KV-PV |
| 2 | reset recovery -255 (post) | spine to async clear pins of 20 copies in one cycle | post only | the 16 tail_clear rows, before the bind (section 1) | KV-D23-COMPOSE |
| 3 | hold, pre-GRT FF | cross-tap zero-logic hops between about 240 taps | Checked, v8b: 54,601 endpoints, cross_tap 47,549 at -135.1, port_in 4,448 at -98.2, same_tap 118; TNS -1,566,502 ps. repair_timing -hold shows iteration 0 after 2 h 10. Non-tap cells 539k / 520k (largest closed kit: 517k) | (a) split the 47,549 by launch kind from the v8b DB. (b) same-tap or lockup form on FIRM zero-logic hops (clock.ft_hop_lockup, as on kv3_io_ft_v1), not buffers. (c) 3-way x cut if cells stay over 517k after repair | FABLE-FIX-KV-PV |
| 4 | 557 of 1583 relay_sites keys unmatched in both kits | not read | OT_RELAY_SITES line, both kits | read the key form (hg had an alias form with the same symptom) | FABLE-FIX-KV-PV |

Unknown: what the pv worst path is once rank 1 and 2 are gone. Neither kit has a GRT TT number.

### hg / hgi

| rank | class | root cause | measured evidence | fix | owner |
|---|---|---|---|---|---|
| 1 | M is in the plan before its proof | k9 was in global placement at 19:39 | k8 (L only): total 27,571 = landing band 11,008 + hst3 fan-out 10,156 + about 6,400 elsewhere. M targets the first two | wait for k9 iteration 5 before the D25e2 bind is sealed, or accept one more event | OPUS-FIX-KV-HG |
| 2 | M hst3 trunk uses the middle channel x 294-389, y 640-950; hst3_g lands near (340,696) | same channel k6 overloaded (+21,000, x 310) and k7 (15,490, W3 x 340) | k6 / k7 posts; geometry checked | Stop rule: k9 bin x 200-400, y 600-1000 over 5,000 -> hst3 polyline [[200,950],[650,950],[650,618]]. Same 782 um, hop 391, stays in the y 899-1002 channel, crosses no core (checked). Unproven | OPUS-FIX-KV-HG |
| 3 | family coverage | L / M rows exist on hgi_v1 x2 only = 12 of 64 hg + hgi partitions | Checked: all 19 types carry the same u_hst#_g / t# chains and the 1559-bit tN bus; 17 types have no polyline and no split | after k9: one family event with per-floorplan rows (8 hg types have 27-30 cores) | OPUS-FIX-KV-HG |
| 4 | hgi_v1 TT -199, 5 ends | 4 FSTART ends (NORAWB) + dead eq flop | k8 post | raw-branch regen (D25e) and the eq key (D25e2). Not kit-proven: next kit must come from the D25e2 bind | OPUS-FIX-KV-HG |

### die

- Hold -182.6 TT is a contract number; measured pairs 0 (real views: cores 38 / 68, types 4 / 56). Cause stays the regular-tap
  spread of 106 to 197 ps (0845 review). Offsets v2 are worth 25 to 50 ps at most. 358 ports need more than the 130 cap, so
  the lever is the kit hold fix to the window. Owner: KV-PC-HGI-1119 pilot, DIE-LEVEL-CHECK-1119 for the measured re-run.
- Crossings: F1 0 / 3915 is the generic form. The shipped sidecar (hub_C, 3595 ports) with the 32 rows is a lower bound
  (start-edge ambiguity not included). Owner KV-CROSSING-1119: re-time the D25e2 bound sidecar in fall form.
- 172 lanes moved: token sim at die before any type on D25e2 is counted.

## 4. Stop list

- Restarting the D25e2 strict bind without the 16 tail_clear rows.
- Core-tap v2 in the plan without the v2 tree, or the reverse; citing die hold from a mixed pair.
- Treating -675 as a pv floorplan or cycle problem: no more pv cycle rows until a kit on the fixed bind is read.
- Hold buffers for 47,549 cross-tap ends on a 539k-cell pv kit.
- Sealing M as final before k9 iteration 5; porting L / M to the other 17 hg / hgi types before k9.
- Any hst trunk polyline through x 294-389 if k9 repeats the k6 / k7 bins.
- Folding F1 / P4 K rows onto the hub_C sidecar.
- More tree offset passes to move die hold.
