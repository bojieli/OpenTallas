# FABLE-PD-KV-1500 (2026-11-20 14:55 PST): worst-path mechanism of the 8 held placed KV kits, against D26 R3

Reviewer: FABLE-PD-KV-1500 (Fable). Read-only: nothing launched, cancelled or patched; no STA run, no DB opened.
Source: each kit's `run/reports/asap7/*/base/3_detailed_place.rpt` (ideal clock, placed), kit `constraint.sdc`, `macros/*.lib`,
`landing_placement.tcl`, `cland_fclk_targets.txt`, bound RTL, and the D26 contract `plan_c.json` (epyc8 kv-d23-compose8/d26_raw/d26_contracts).
Kits: KV-D25e3 wave items listed in lanes/AUTO-REVIEW-HELD.tsv (kv3_pv skipped: FABLE-FIX-KV-PV-R2). Owner of every fix: KV-PLAN-R1.
Marking: **V** = I read the file this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.

## 0. Verdict

1. **hub_Wo (-1040) and sys_c (-987) are missing stages on one die-crossing status wire each. Not a slew problem, not a core pin.** Worst-path slew 224 / 158 ps; both paths are one flop to one flop through 58 to 70 repeaters.
2. **hgi v3, v5, v6, v7, v8 (-315 to -353) are not data-path failures.** The worst path is a port into a hardened clock-landing core, timed with an ideal clock. Its floor at zero wire is -275 ps by arithmetic. The kit's own POST_CTS script removes it. In the `clk` group these five kits are at -5 ps or better.
3. **hgi_v1 cl141fc26e (-410) is real:** a landing-monitor fault flop to a collector flop, about 1,320 um, no stage.
4. **D26 R3 fixes none of the three real paths** (hub_Wo, sys_c, hgi_v1 collector). It has no row on them. It also does not change the hgi measurement, so the D26 hgi kits will be held again by the same placed test unless the test changes.
5. The core-pin max_transition finding (e7ebced0c4e) is not the cause of any of the eight. One residual slew class exists on sys_c (section 4).

## 1. Per type (V unless marked)

| Kit | WNS | Worst path | Cells / data delay | Path slew | Mechanism | D26 R3 fixes it |
|---|---|---|---|---|---|---|
| kv3_hub_Wo a9 (intel1) | -1039.6 | `u_bin_i_astk_WN__u_strip_u_strip_g_ep_N__u_ep_zo/eq` -> `u_u_efault.fault` | 70 BUFx6f + AND5/AND4 reduce, 1,792 ps | 224 | missing stage | no |
| kv3_sys_c a7 (epyc7) | -986.6 | `u_bin_i_serdes_E_tx_up/q` -> `u_bout_o_dcal_dob/q[2]` | 58 buffers, 0 logic, 1,756 ps | 158 | missing stage | no |
| kv3_hgi_v1__cl141fc26e a2 (epyc2) | -410.1 | `u_cland_monitor_1/u_fault_port/q` -> `u_cland_collect_rst_n_t45/fault_o` | 22 cells (34 buffers, OR2), 1,136 ps | 188 | missing stage | no |
| kv3_hgi_v3 a6 | -352.6 | port `ft27_i[6]` -> `u_cland_ft27_i/d[6]` (core `kv_cland_w1057_ew_94a44`) | 1 BUFx2, 82 ps after the 166.6 input delay | 66 | ideal-clock measure of a hard landing core | not needed, see section 3 |
| kv3_hgi_v5 a6 | -315.1 | `ft24_i[984]` -> `u_cland_ft24_i/d[984]` | 1 BUFx2, 41 ps | 27 | same | same |
| kv3_hgi_v6 a3 | -343.1 | `ft29_i[6]` -> `u_cland_ft29_i/d[6]`; second -312 on `u_cland_ft8_i` (`kv_cland_w1045_ns_ddbeb`) | 1 BUFx2 | 77 | same | same |
| kv3_hgi_v7 a3 | -321.3 | `ft25_i[6]` -> `u_cland_ft25_i/d[6]` | 1 BUFx2 | 39 | same | same |
| kv3_hgi_v8 a6 | -315.1 | `ft26_i[984]` -> `u_cland_ft26_i/d[984]` | 1 BUFx2, 41 ps | 28 | same | same |

All eight kits were generated on runtime b9800fc7c548, which does not carry e7ebced0c4e (no `OT_PLACE_MAX_TRANSITION` in `config.mk`).

## 2. The two -1 ns paths

**hub_Wo: the efault collector.** `ot_dp_efault #(.AGE(23), .N(26)) u_u_efault` computes `fault <= fault | (armed & ~&eq)`: one flop takes the `eq` flag of all 26 input landing ranks in one cycle. Die 1278.72 x 1676.16 um. The worst source rank sits in the NW corner (ring rect 18.6-45.4, 1561.7-1658.9); the fault output writer is in the SE (1246-1279, 133-148). Manhattan distance about 2,700 um (I: the site of the `fault` flop itself was not read; the 1,792 ps of repeated wire agrees). It is one endpoint. The plan generates this cell in 29 of 56 KV types (pv 10, hg 8, pc 6, hroot, hub_C, hub_Eo, hub_Wi, hub_Wo), always as a single-cycle reduce with N = in-lanes, so every large type carries the same exposure.

**sys_c: lane L356.** Bound RTL line 51: `o_dcal_dob` bit 2 is the forward of `i_serdes_E_tx_up` to hub_Wi. Die 2160 x 1036.8 um. The input ring is on the E face (2099.5-2142.7, 994.8-1012.1); the `o_dcal_dob` writer starts are in the SW (x 12-116, y 10-276) with the face pin at (0, 335). Manhattan distance 2,750 to 3,075 um (I, from landing sites), no station. One bit, one endpoint.

Both are status signals, off the token path. Extra cycles cost nothing but the lane latency entry.

Second class in both kits: reset relay hops. sys_c `u_rrl_172` -> `u_bin_i_host_boot_go/eq` recovery -241.9 (32 buffers, 1,033 ps); hub_Wo `u_rrl_16` -> `u_bin_i_ahub_am_WN/eq` -119.9 (34 buffers, 918 ps). These are relay legs well over the 300 um cap.

Third class in both kits: `cland_fstart_in_*` port -> flat ring `s_d` / `s_tag` / `u_wen`, 6 to 10 cells in the 250 ps the falling-edge capture leaves after the 166.6 ps input delay. sys_c 16 groups, -241.8 to -2.5; hub_Wo 30 groups, -206.4 to about -25. Ideal-clock measure; the same class on kR after GRT was 50 ends to -54, all on missing-route nets (R, KV-PLAN-R1 09:30).

Not measured: how the 4,074 (hub_Wo) and 2,669 (sys_c) violating endpoints split by class. The report prints one path per group. KV-SYSC-1119 (R, 11-19 07:37) proposed station rows for `word_data` -> `rx_payload` / `srx` / `svc` (3 each), `tx_payload` (1) and `link_cfg_data` (2); I could not confirm from this report whether D25e3 carries them. `place_wire_ratio.tsv` still lists `rx_payload` -> `svc_d1` legs of 421 and 461 um.

## 3. hgi v3 to v8: why -315 is not a setup failure

Report for hgi_v8 (same shape on all five):
- arrival 207.12 = 166.60 input delay + 40.5 (port, BUFx2, wire);
- required -107.99 = 416.50 (falling edge) - 145.51 "macro clock tree delay" - 378.98 library setup of `d[984]`.

Slack with zero wire is 416.5 - 145.5 - 379.0 - 166.6 = **-274.6 ps**. No placement can beat that, so the -300 rule is testing a constant. The lib (`kv_cland_w1057_ew_94a44_tt.lib`): `d[]` setup_falling 294 to 379 ps, `fclk` min/max_clock_tree_path 133-146 / 585-651 ps. `kv_cland_w1045_ns_ddbeb` is the same class (-265 to -312). The other landing cores are fine (`w1560_ew_0433f` d setup 48-69 ps).

The kit already handles this at POST_CTS: `cland_fclk_target.tcl` (FABLE-FIX-QC-N N4.1) pads the forwarded clock to the pin. `cland_fclk_targets.txt` in hgi_v8: `u_cland_ft26_i` 179.2 ps, `u_cland_ft4_i` 151.0 ps. With a propagated clock the 145.5 ps ideal compensation is gone and the pad is added: 416.5 + 179.2 - 379.0 - 207.1 = about +10 ps (I, arithmetic; not measured on these kits).

`clk`-group setup on the five kits: hgi_v3 worst -4.7 (`u_hst2_t2.u_reg.ti_b[1496]` -> `u_head2_e0`, pin slew 1,365 ps, the one core-pin slew path I found); reset recovery -0.8; v5 to v8 no negative `clk` path in the report.

What does stop these D25e3 hgi kits is hold, not setup: 5,105 head-core front ends to -277.6 FF (R, FABLE-PD-KV-0945 section 3; kR). That is what the D26 lockups are for. So routing the held D25e3 hgi kits gains nothing; the point is that the D26 hgi kits must not be held by this test.

## 4. Core-pin max_transition (e7ebced0c4e, CORE-LIB-LIMITS-1330)

- The landing-core libs carry no `max_transition` at all (0 occurrences in `kv_cland_w1057_ew_94a44_tt.lib` and `w1560`), so the finding's premise holds for KV. It is not what sets WNS here: the pin slews on the worst paths are 19 to 77 ps.
- hub_Wo: 0 slew, 0 cap, 0 fanout violators.
- hgi: 192 to 348 slew violators, worst 406 to 476 ps against 320. Mild; mostly `u_head*_g_t_*_u_kst*.kp_o` flop pins and wire repeaters.
- **sys_c: 161 slew violators, 114 of them inside 11 flat landing rings, worst 3,533 ps** (`u_bound.u_cland_i_serdes_E_tx_up/wire163978/A`; also `kvs_ctl_oobs__*`, `kvs_ctl_boot__link_cfg_*`, `kvs_attn_attn__tx_*`, `kvs_ctl_kvi`). They survive place repair and are on none of the reported paths. This looks like the post-repair move class (CORE-LIB-LIMITS open item 2, DLY-REPAIR-1 f2e64e5d3b2) rather than the core-pin class, but the nets are not identified: that needs one DB read.

## 5. D27 rows, ranked (owner KV-PLAN-R1; P)

| # | Row | Evidence | Types | Form |
|---|---|---|---|---|
| 1 | efault collection as a staged reduce: each landing rank's `eq` reduced locally, then relayed in hops <= 300 um to `u_efault`; same for the landing monitor `u_fault_port` -> `u_cland_collect_*` leg | hub_Wo -1039.6 (2,700 um, 1 end); hgi_v1 -410.1 (1,320 um) | generator change, 29 types with `u_efault`; measured on 2 | pipeline rows, +cycles on a status path; AGE gates the local term, so the relay depth only delays the report |
| 2 | sys_c lane L356 `i_serdes_E_tx_up` -> `o_dcal_dob[2]`: 9 to 10 stations at 300 um, or carry the bit on an E-side lane so it does not cross the type | sys_c -986.6 (2,750-3,075 um, 1 end) | sys_c | station row; update the L356 latency entry |
| 3 | reset relay reach: `u_rrl_172` -> `host_boot_go` rank (sys_c), `u_rrl_16` -> `ahub_am_WN` rank (hub_Wo): add relays to 300 um with the reset reach script | -241.9 / -119.9 recovery | sys_c, hub_Wo; scan the other large types | fixed reach script, no hand rows |
| 4 | sys_c: confirm the KV-SYSC-1119 station rows are bound (`word_data` -> E-face outputs 3 each, `tx_payload` 1, `link_cfg_data` 2) | R, 11-19 07:37; 421 / 461 um legs in `place_wire_ratio.tsv` | sys_c | station rows |
| 5 to 9 | the FABLE-PD-KV-0945 list unchanged: astk `sc_v` memory register + `eo_q` stage + bin seat; astk tap split; pv over-core traffic; first pc GRT class; hg/hgi superset | lanes/FABLE-PD-KV-0945.md section 5 | hg, pv, pc | as listed there |

Not plan rows, same priority as row 1:
- **Placed review test (ROUTE-RELEASE / WAVE-FLOW):** read the `clk` and `asynchronous` groups for the -300 rule, or add the `cland_fclk_targets.txt` pad and drop the ideal macro-tree term for `fclk_in_*` ends on hard landing cores. Otherwise 5 or more D26 hgi kits are held at place for a constant.
- **sys_c regen on a runtime with e7ebced0c4e and f2e64e5d3b2**, then name the 114 ring nets from the DB.
- **Landing cores `kv_cland_w1057_ew_94a44` and `w1045_ns_ddbeb`:** `fclk` tree 133 to 651 ps inside the core and `d` setup to 379 ps force a 151 to 179 ps clock pad in every parent. A re-harden with a balanced write clock removes the pad. Low priority while the pad works.

## 6. Stop list

- No route release of the D25e3 hub_Wo or sys_c kits: -1040 / -987 are single unstaged wires that repair cannot close.
- No repair, ECO or re-place retry on hub_Wo or sys_c for these paths; no buffer or slew setting for them.
- No reading of hub_Wo or sys_c as a core-pin slew case, and no regen "for e7ebced0c4e" expecting the -1 ns to move.
- No hold of a D26 hgi kit on placed WNS when the worst group is `fclk_in_*` into `kv_cland_w1057_ew_94a44` or `w1045_ns_ddbeb`.
- No route of the held D25e3 hgi v3 to v8 kits either: their blocker is the head-core hold class that only the D26 lockups fix.
- No claim that D26 R3 fixes hub_Wo, sys_c or the hgi_v1 collector path.
- No new hgi_v1 cl141fc26e build expecting section N to close -410; measure the collector leg on the D26 kit first.
- No re-harden of the landing cores before row 1 and row 2 are in a plan.

## 7. Not checked

- Endpoint counts per class on any kit; the `u_efault` flop site; wire lengths are from landing sites, not from the DB.
- Whether another -1 ns path sits behind the reported one in the `clk` group of hub_Wo or sys_c.
- The 114 sys_c ring nets at 3.5 ns.
- The post-CTS value of the hgi landing-core class on these kits (arithmetic only).
- hub_Ei, hub_Eo, hub_Wi, hub_C, hroot, pc and pv for the efault path.
- D26 R3b itself: at 14:44 the gate is still waiting for memory on epyc8 (intel2 `~/tmp/kvplanr1/d26_r3b_gate.log`, last written 11:26, launcher PID 1927491 alive, admissible 0 GB). Not started 3 h 20 min after launch, with the cut at 20:00.
