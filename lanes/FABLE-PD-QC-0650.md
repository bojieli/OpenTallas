# FABLE-PD-QC-0650: S4r2 + sidecar review, the four far-negative types, S4k failure classes

2026-11-15 05:55 PST, FABLE-PD-QC. Technical PD only. Read: FABLE-PD-QC-0300, FABLE-CLOSURE-STRATEGY (05:1x), FABLE-TRIAGE-QC, handoffs DIE-QC-103 and CLAND-BIN, queue to 05:37.

MEASURED = read by me from a plan, sidecar, bound RTL, placed dump or wave table. INFERENCE is marked.
Work dir (read-only, nothing of a lane changed): epyc9 `/srv/opentallas-scratch2/claude/fable-pd-qc-0650/` (`an*.py`, `fw*.py`, `census.py`, `hop_census_4types.log`).

Not available at this time: the S4r2 and S4q2 binds have no `bind_report.json` yet, the four CTS probes are at kit_rtl / gen, and no type has a placed database on S4k. So nothing below is a bind or timing result for S4r2.

## 0. Decisions

1. **S4r2 station counts are right; the sidecar sites are not.** Every bc_o bus has 2 stations and every bc_i bus has 1, on all 18 cb types including both _s2 types. But the sidecar puts `u_bin` on the same point as the plan station on all 32 buses, so the first hop (ring -> `u_bin`) is 368-634 um and the next is 0. 317.6 um is the `equal_hop_um` field (route / 4), not a hop between the sites as written.
2. **Fix is the sidecar only:** `u_bin` at 1/4 of the route, the plan station stays at 1/2, `u_st` stays at 3/4. No plan, bind or latency change. Then all 32 buses are at 178-320 um.
3. **cbf_q00_s2 is not fixed by S4r2 and is not in the sidecar.** Its tiles `u_t10` and `u_t01` have swapped origins against the port windows: bc_i10 runs 2,042 um, bc_o01 2,485 um. Same in S4k. Swap the two origins.
4. **The four far-negative types are three different classes,** and only part is ring -> bin. The fw types are 65 % core -> boundary-out register. sle_fw_v1 and sle_fw_v2 (4 types) have no internal station in S4k at all.
5. **On S4k now the first stop is generation:** 15 rows failed at kit_rtl at 05:35 on three sources that exist only on epyc9.
6. Adopt S4r2 when its bind passes, with the corrected sidecar. Do not wait for the s2 or fw work.

## 1. S4r2 + sidecar

### 1.1 Counts (plans `zz_s29_qc103_s4k / s4q2 / s4r2.json`, `internal_stations`)

| bus kind | S4k | S4q2 | S4r2 | types in S4r2 |
|---|---|---|---|---|
| bc_o (01, 11, 21, 31, 03, 13, 23, 33) | 0 | 2 on 03/13/23/33 | 2 on all | cbf_q00 x2 + s2, cbn_q00 x3, cbx_q10 x4, cbn_q01 x3, cbn_q11 x2 |
| bc_i (00, 10, 20, 30, 02, 12, 22, 32) | 0 | 1 on 00/10/20/30 | 1 on all | all 18 |
| na_i00 | 4 | 4 | 7 | cbf_q00 x2 + s2, cbn_q00 x3 |

Equal on all four columns of each class, and the W5 slice (the _s2 types) has the same counts. This is the form of FABLE-PD-QC-0300 section 2.3. The W5 PARAM_REGEN cause is removed in the plan; the bind decides.

### 1.2 bc_o hops in the S4r2 plan

219-253 um on MY tiles, 389-400 um on R0 tiles (bc_o13, bc_o33, bc_o31). All at or under 405. No station inside a tile. Exception: cbf_q00_s2 bc_o01, section 1.4.

### 1.3 bc_i: the sidecar (`zz_s29_qc103_s4r2.cland_bin_sites.json`, 16 types, 32 buses)

Bound order, read from `bind_s29q103S4RQ/rtl/qfd_qc_cb_f_q01__cbf_q01.sv` lines 2553-2612: ring (`u_cland_bc_i02`) -> `u_bin_bc_i02` -> `u_lpad_bc_i02` (D=1, this is the plan station) -> `b_d` (`u_st`) -> tile tap.

Sites as written (um, Manhattan between the points):

| bus (type) | ring -> `u_bin` | `u_bin` -> station | station -> `u_st` | `u_st` -> tap |
|---|---|---|---|---|
| bc_i00, bc_i10 (cbf_q00) | 633, 625 | 0 | 319, 311 | 317 |
| bc_i30 (cbx_q10), bc_i32 (cbf_q11, cbn_q11) | 633, 625-633 | 0 | 311 | 317 |
| bc_i10 (cbn_q00) | 614 | 0 | 302 | 308 |
| bc_i22 (cbf_q11, cbn_q11) | 578-587 | 0 | 293 | 291 |
| bc_i00 (cbn_q00) | 426 | 0 | 207 | 213 |
| bc_i20 (cbx_q10) | 387 | 0 | 198 | 196 |
| bc_i02, bc_i12 (cbf_q01, cbn_q01) | 368, 377 | 0 | 181 | 178-187 |

So 20 of the 32 buses, on 12 of the 16 types, keep a first hop of 426-634 um (517 bits each). Only cbf_q01, cbn_q01 and bc_i20 are under 405. The fix is one point per bus: `u_bin` at route / 4 (cbf_q00 bc_i00: 317.6 um from the ring along the S channel). Hops after the fix: 178-320.

Second source for the same register: the plan `relay_sites` of cbf_q01 holds `u_bin_bc_i02/*` at y 295.9, the sidecar says y 362.9. Keep one. CLAND-BIN's hook should read the sidecar and the plan rows for `u_bin_bc_i*` should go.

The cbf_q01 eq proof now running uses the S4k sidecar (0 plan stations, 3 hops of 243-249 um). It proves the hook, not the S4r2 sites.

### 1.4 The _s2 types

- cbf_q01_s2: bc_i02 369/369, bc_i12 377/378. Same as cbf_q01. Not in the sidecar; add it with the same sites.
- cbf_q00_s2 (1 instance, c_W5_bf_00): `u_t10` is at (86.4, 1304.6) and `u_t01` at (691.2, 77.8). In cbf_q00 they are the other way round. The module and the port windows are the same (bc_i10 on S at x 626-716, bc_o01 on N at x 4-94). Result in S4r2: bc_i10 hops 1,022 / 1,026 (route 2,042 um, 511 um per hop even with `u_bin` and `u_st` sited), bc_o01 hops 832 / 821 / 832 (route 2,485 um). S4k has the same routes with fewer registers.
- More stations on these two buses only would break the equal count in W5. Fix: swap the two origins (plan event on one type, orientations already match the cbf_q00 rows). INFERENCE: the swap is a plan error, not intent; DIE-QC-103 confirms against the ft slots of that type before the edit.

### 1.5 Side effects

- Latency (from 0300 section 2.3, not re-measured, bind pending): A +1, B +3, C +3, D +3; near root +4, far root +10; SKEW_S 13-14, SKEW_N 12 inside 3..27. DIE-QC-103's regen shows lanes {+3: 336, +1: 96}, which matches.
- Flops: about 570 k added (estimate from 0300). The G0 density line of the cb types decides.
- Other types: none change RTL. 18 cb types regenerate; cb builds on S4k are spent when S4r2 is adopted.
- Not covered by S4r2, same cb types (cbn_q11 placed dump, section 2): `u_lpad_nb_i*` pad chain not spread (514 hops, max 773 um), d-chain (627 hops, max 469).

## 2. The four far-negative types

No CTS database exists, so no endpoint slack. What exists is the last placed dump of each (older events, named below). Census of zero-logic register -> register hops over 405 um, through buffers and inverters (`census.py` on `geom/geom.tsv`).

| type (dump) | hops over 405 | family | share | max um |
|---|---|---|---|---|
| slw_fw_v3 (S4C a8) | 5,736 of 30,905 | `u_core.*` -> `u_bout_*` (x_stm_o, x_stm_p1_o, x_ctl_o, x_fe_p*_o, dd_wo, ard_wo) | 3,755, 65 % | 1,277 |
| | | ring -> `u_bin` (st_wi 1,088, dr_wi 520, x_ctl_i 57) | 1,665, 29 % | 1,862 |
| sle_fw_v2 cl69f5e854 (S4C a5) | 7,095 of 29,620 | `u_core.*` -> `u_bout_*` | 4,668, 66 % | 1,348 |
| | | `u_bin_x_stm*_i` -> `u_bout_st_eo` (straight through the type) | 1,087, 15 % | 1,151 |
| | | ring -> `u_bin` (x_ctl_i 581, dr_ei 420, cmd_ei 116) | 1,117, 16 % | 1,224 |
| sle_st_b_v2 clfde1249e (S3R a5) | 863 of 38,486 | ring -> `u_bin` (x_hc*_i 392, x_st_a_i 287) | 679, 79 % | 1,226 |
| | | `u_nbo_pad` -> `u_bout_x_fe_o` | 128, 15 % | 829 |
| | | reset tree branch -> leaf | 31 | 586 |
| cbn_q11 cl49ae4555 (S3R a3) | 2,931 of 40,446 | ring -> `u_bin_bc_i*` -> `u_st.tap_d` | 1,477, 50 % | 477 |
| | | `u_lpad_nb_i*` chain, `u_bin_nb_i*` -> pad | 722, 25 % | 773 |
| | | d-chain | 627, 21 % | 469 |
| | | reset relay `u_rrl_*` -> `u_bin_na/nb_i*/eq` | 2 | 1,466 |

Answers:
- cbn_q11: the cb class. S4r2 (bc_i22, bc_i32, bc_o23, bc_o33) plus the corrected sidecar covers half. The nb_i pad chain and d-chain are generator siting. INFERENCE: -861 ps does not come from 477 um hops; the two reset-relay hops of 1,411-1,466 um or the 773 um pad hop are the candidates, the probe names it.
- sle_st_b_v2: ring -> bin, the same class as cb. Stations needed: x_hc1_i (516 bits, 1,226 um) +2, x_st_a_i (652 bits, 867 um) +2, x_fe_o (256 bits, 829 um) +2. All 11 st_b types have 0 internal stations in S4k.
- fw types: **another class.** The core output registers sit mid-type and the boundary-out register is at the pin, up to 1,348 um away; x_ctl_o leaves on the N face.
  - S4k has stations on 5 buses of the 6 slw_fw types only (x_stm_i, x_stm_p1_i, x_fe_p1_i, x_ctl_i, ard_wo), and their plan hops are 397-735 um.
  - sle_fw_v1 (2 types) and sle_fw_v2 (2 types, the -453 one included): 0 internal stations in S4k.
  - sle_fw_v3 already has the full form: 19 output and 4 input buses stationed, plan hops 146-368 um. Its last dump has 1,599 hops over 405 against 8,176 for sle_fw_v2.
  - Needed on the other 10 fw types: the sle_fw_v3 station set. From the dumps: x_ctl_o +3, x_fe_p*_o +2, x_stm_p1_o +2, x_stm_o +1, dd_wo / dd_eo +2, ard_wo / ard_eo +2, st_eo +2, and `u_bin` equal-hop on st_wi, dr_wi, cmd_wi, x_ctl_i.
- Reset-start is not the main class in any of the four (2 to 31 hops).

The probes run on S4k, where sle_fw_v2 and st_b have no stations. They will give the endpoint names but will not close.

## 3. Failure classes on S4k now (wave table 05:39, 137 QC items)

| class | rows | note |
|---|---|---|
| kit_rtl FAIL, S4K event, 05:35 | 15 | `bind: ERROR preferred HDL source missing`: `treeA/physical/qwen_missing_phy/nface_tall_1017/ot_qfd_serdes_112g_x12_phy_s597/..._bb.v`, `.../nface_tall_g5_lclk_1020/ot_qfd_ucie_x64_phy/ot_qfd_ucie_x64_phy_bb.v`, `treeA/rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv`. Present on epyc9, absent on epyc7 and epyc2 (checked). |
| kit_rtl FAIL, S4C event (stale) | 5 latest | same class, older bind |
| RUNNING on S4K | 38 | none placed yet |
| infra (OOM, orphan, exit 143) | 5 route/place, 10 retry | cbx_q10 x4, sle_stm_v1 |

Technical class behind the running types (24 QC types with a placed dump): 22 fail the 405 um hop check (max 1,018-1,862 um), 24 fail pin -> first register (max up to 716 um). By the census in section 2 the order is: core -> boundary-out, ring -> bin, bin -> bout straight-through, pad chains. No route or DRC class is visible yet on S4k.

## 4. Levers, ranked

| # | lever | owner | effect |
|---|---|---|---|
| 1 | Copy the three sources to all gen hosts; take the source list from `bind_report.json` of S4KQ, not from the S4CR/S4KR list | KIT-OPS-5 | 15 S4K rows restart |
| 2 | Regenerate the S4r2 sidecar: `u_bin` at route / 4; add cbf_q01_s2; drop `u_bin_bc_i*` from plan `relay_sites` | DIE-QC-103 | 32 buses to 178-320 um |
| 3 | Adopt S4r2 when the bind is clean (0 errors, R8 changed 0, LATCHECK, G0 baseline, SKEW inside 3..27) | DIE-QC-103 | cb crossing class closed on 17 of 18 types |
| 4 | Sidecar reader in the hook, then the cbf_q01 proof on the S4r2 sites; default-on only at 0 hops over 405 | CLAND-BIN | proves 2 and 3 in a placed database |
| 5 | fw family: sle_fw_v3 station set on the other 10 fw types, one event, equal depth per bus across the family | DIE-QC-103 | 3,700-4,700 hops per type |
| 6 | st_b family: stations on x_hc*_i, x_st_a_i, x_fe_o in all 11 types | DIE-QC-103 | 680-860 hops per type |
| 7 | cbf_q00_s2: swap `u_t10` / `u_t01` origins | DIE-QC-103 | routes 2,042 and 2,485 um become 1,253 and 665 um, as cbf_q00 |
| 8 | Spread `u_lpad_nb_i*` and the d-chain | TYPE-QCCB-GEN | 1,350 hops in cbn_q11 |
| 9 | Read the probe CTS per endpoint family; confirm or replace the cbn_q11 inference | DIE-QC-103 | names -861 |

## 5. Stop list

1. No adoption of S4r2 with the sidecar as written, and no quoting of 317.6 um as a hop until the sites are regenerated.
2. No release of sle_fw_v1, sle_fw_v2, slw_fw_* or st_b types into route on S4k: no station form on the failing buses.
3. No extra stations on cbf_q00_s2 bc_i10 or bc_o01 alone (breaks W5 again).
4. No waiting on the probes before levers 5 and 6: the placed dumps already name the buses.
5. No pin of kit_rtl to epyc9 as the fix for lever 1.
6. Still in force: 0300 stop list 1-8, and no G2 beside the ring as default.
