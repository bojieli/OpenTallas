# FABLE-PD-KV-1840 (2026-11-20 18:40-19:15 PST): KV D27 open items, station/cycle scan, 20 held placed rows

Reviewer: FABLE-PD-KV-1840 (Fable). Read-only. No dump, no STA, no DB opened, nothing launched, cancelled, signalled or patched.
Sources read: D27 private tree (epyc8 kv-plan-r2/d27/tree, plan 3d152d53d5b5, asbuilt 7950f7cf5d14), D26 R3d candidate (epyc7
d26_contracts/source_gate_r3b, plan f81cafc24d3a), `tools/die_plan/native_istations.py` of that tree, the D25e3 wave kits
(`3_detailed_place.rpt`, bound RTL, `reset_taps.tcl`, `reset_tree.tcl`, `landing_placement.tcl`, macro LEFs, place logs).
Marking: **V** = read this round. **I** = inferred. **P** = proposal. Earlier review: lanes/FABLE-PD-KV-1500.md (still valid).

## 0. Verdict

1. **D26 R3d will be refused by the strict bind again (V, static replay).** `n3_cycles.py` raised the 12 eN lanes 6 -> 8, but
   `kv3_hgi_v1*` has no station row on `i_ectl_Q_N_eN`; the rule wants source 6 + destination 0 = 6. Posted URGENT 18:5x. Section 2.
2. **The sys_c / hub_Wo reset legs are not a reach problem of the tree. They are one unassigned consumer class (V).** Every
   `u_bin_<bus>` landing bin takes the module-wide `rst_n`, which the bind ties to ONE leaf tap in mid-type. The kit re-point
   only moves FIRM flops, and the bins are not FIRM. The same class is the reset path on all 11 held pv rows (-425 to -2,224 ps).
3. **PDN-0006 is not missing M6/M7 power pins (V).** The signed pc view that builds (pc_v3) also has M5-only power pins. The split
   views differ in the obstruction export: M6/M7 are large merged blocks instead of exact wires.
4. The efault staged form can cover all 29 types from plan points; it does not yet place the `fault` output hop (I).
5. None of the 20 held rows has a CTS result. No D26 row clears any of them by itself; D27 as composed clears the worst path of sys_c only.

## 1. Open D27 items: root cause and fix

### 1a. Reset reach on sys_c and hub_Wo (V) -> a kit/bind re-point, yes

| Kit | bound RTL | leaf tap site | failing bin | bin landing ring | distance (I) | recovery slack |
|---|---|---|---|---|---|---|
| kv3_sys_c a7 | `wire rst_n = rst_n_t40;` (line 3999), `u_rrl_172 ... // boot pad tap 40` | (1049, 954) | `u_bin_i_host_boot_go` | (134-177, 380-397) | about 1,450 um | -241.9 |
| kv3_hub_Wo a9 | `wire rst_n = rst_n_t21;` (line 3927), `u_rrl_16 ... // boot pad tap 21` | (597, 853) | `u_bin_i_ahub_am_WN` | (1218-1261, 86-103) | about 1,400 um | -119.9 |
| kv3_hub_Eo a3 | `wire rst_n = rst_n_t48;` | - | (worst path is `u_bin_i_host_die_rst_n/q` -> core `u_astk_EN`, -747.0) | - | - | - |

- `rst_n` users: sys_c 122 cells (66 `u_ist_`, 22 `u_bin_`, 21 `u_bout_`, 12 `u_ft_`); hub_Wo 325 (26 `u_bin_`); hub_Eo 316 (26 `u_bin_`).
- `reset_taps.tcl` header, rule (2): only FIRM-placed flops (face flops, ft stations) are re-pointed to the nearest tap;
  "Leaf flops (not FIRM) keep their RTL synchroniser". `u_ist_` / `u_ft_` / `u_bout_` are FIRM and get re-pointed. `u_bin_` is
  placed by the placer next to its ring and keeps the leaf tap. Nearer taps exist: sys_c tap 11 at (10.6, 330.6), tap 16 at (296.8, 484.0).
- So the plan tree does solve at 300 um (relay to tap); the tap -> consumer hop of this class is unchecked. `plan.reset` of D27
  has no `inst_taps` key (V).
- Same class on the held pv rows: `u_rrl_<k>` -> `u_bin_<bus>/eq` -1,092 to -2,224 ps on pv_v2, v2n, v3, v3n, v4, v4n, v5, v5n, v7, v1n; -425 on pv_v1.
- Fix (P), owner **RESET-RELAY-GEN-R2**: (i) class fix in the bind: every `u_bin_<bus>` gets `rst_n_t<nearest tap to its bin
  home / ring centre>` from plan points (form R `reset.inst_taps`, on main f02ccd50eb, 0 cycles), emitted for all 56 types, no
  placed DB needed; (ii) until then, `reset_leg_plan.py` on the sys_c a7 and hub_Wo a9 placed DBs gives the same rows per type
  (as done: pv_v2 13 -> 0 legs, hub_Eo 32 -> 0). hub_Eo also needs form M (core `u_astk_EN` reset port, D 8), already modelled.
  KV-PLAN-R2 only carries the rows into D27.

### 1b. pc_v1 `i_ectl_Q_N_kf` (V): third bank, with its cycle

- Row (3 clones): 1 data bit + epoch, 2 exact banks plus `face_bit_sites_um`. `kit_istations.packed_exact_geometry` refuses any
  exact packed row that also moves face registers, and requires `packed depth == banks == regs_um`.
- Geometry (I): the epoch bit runs ring (949, 318) -> (855, 677) -> (721, 946): 856 um in 2 hops (403 each with the face move, 453 without).
- Fix (P), owner **KV-PLAN-R2**: drop `face_bit_sites_um`, use 3 banks at 285 um. **The 24 lanes into `kv3_pc_v1*`
  (L361, L365, L369, L373, L381, L385 and the ES/WN/WS copies) must go `fixed_cycles` 2 -> 3 in the same row**, or the kit refuses
  "exact packed banks require every actual stage". No tool change. Tool support (face move on exact rows) only if a third type needs it.
  Check `param_regen.json` ectl response latency after the +1.

### 1c. PDN-0006 on kv3_pc__cl254f2e73 / __cl5a95b461 (V)

| View | power pins | M6 obstruction rects (largest) | M7 (largest) | M1-M5 |
|---|---|---|---|---|
| signed `qkd_kvs_pcc` in pc_v3 kit (passes PDN, in route) | M5 only | 23,768 (4 um2) | 9,715 (6 um2) | one full block each |
| `kv_pcsplit_views_1119/qkd_kvs_pcc_h_head_p` | M5 only | 12,354 (226 um2, e.g. 2.6 x 87 um) | 8,204 (568 um2, 20 x 28 um) | 600 to 21,462 rects per layer |

Both kits use the same `core_pg_M5` grid (`add_pdn_connect M5 M6`). The split views were exported by
`tools/tt_views/view_export.py` (view_export.json) with merged M6/M7 blocks that cover the M5 pin stripes, so no M6 strap can
drop a via. Fix (P), owner **KV-PLAN-R2** (view export, no re-harden): re-export the 4 split views with the abstract form of
the signed view (M1-M5 block, M6/M7 exact shapes). Adding M6/M7 power pins is not needed and would collide with the tile straps.
Not verified: the export options that differ (compare the two view_export records before the re-export).

### 1d. hub_C (V)
`kvd23_hubc_views/kv_cland_*` (6 views): each holds only `.lef`, 2 `.lib`, `signoff.json`; `hard_landing.py` needs provenance, pins,
clock contract. Sources are gone. Fix: re-freeze through CLAND-MACRO-1 (KV-PLAN-R2). 1 type. No relaunch before that.

### 1e. efault staged form (V tool text, I geometry)
- `bind_efault_stage.py` takes source points from the plan (bin relay_sites or landing band centre); the placed-kit sites file is optional.
  So `"types": ["kv3_.*"]` covers all 29 types in one event; D27 has `["kv3_hub_Wo"]` only.
- Gap: the cell site defaults to the L1 centre of the sources. In hub_Wo the `fault` output writer is at the SE corner
  (pin (1278.6, 111.6)) and `o_efault_hub_Wo_fault` has no station row (none of the 7 `o_efault_*` buses has one). Centre -> SE is
  about 1,300 um: a new unstaged hop. Fix (P): set `sites.<type>.<cell>.at_um` at the `o_efault` face register (types with that
  bus), so one depth D covers both; D rises (hub_Wo about 8), a monitor path, no lane cycles.
- Not covered by this form: hgi_v1 `u_cland_monitor_1/u_fault_port` -> `u_cland_collect_rst_n_t45` (-410, 1,320 um). Needs its own
  station row; D27 has none.

### 1f. sys_c `o_dcal_dob` (V)
D27 row is consistent: 9 stations, hops 281-282 um, L356 78 -> 87 = source 9 + destination 78. `o_serdes_E_tx_up` 7 stations at
274 um. `o_dcal_flt` / `o_dcal_tks` stay at 6 stations with 331 / 325 um hops: accept for D27 (single bits, 8 % over); a 7th
station needs +1 on L357 / L359.

### 1g. The 9 FAILED rows

| Row | Cause (V) | Cleared by | Owner |
|---|---|---|---|
| kv3_pc__cl254f2e73, __cl5a95b461 | PDN-0006, 1c | split view re-export | KV-PLAN-R2 |
| kv3_pc_v1__cl23f6a148, __cl4ea58a5c, __cl7f648944 | kf exact row + face move, 1b | D27 row, 24 lanes +1 | KV-PLAN-R2 |
| kv3_hub_C | 6 landing views without provenance, 1d | view re-freeze | KV-PLAN-R2 |
| kv3_hub_Wi | SRAM row class at place (R, KV-PLAN-R2) | D26 apply | KV-PLAN-R2 |
| kv3_pv_v6n | `OT_CLAND BAND FAIL u_cland_ft9_i`: 531 cells, need 183.2 um2, band 223.9 um2 (ratio 0.82), no legal site | larger ft9_i band row in D27 | OPUS-FIX-KV-PV-R3 |
| kv3_pv_v8 | bind stale against the plan | D26 apply (rebind) | KV-PLAN-R2 |

## 2. Lanes whose cycles do not follow their stations

Method: static replay of `native_istations.annotate` (fixed_cycles == source stations + deepest destination row for natively
stationed OUT buses; kit lanes fixed >= stations), lane ends taken from the first and last port. Check: on the D27 plan
(= R3c + rows) it reproduces the R3c refusal exactly (L415 and the other 11 tN lanes, nothing else).

| Plan | native lanes equal | kit lanes at or above | mismatched |
|---|---|---|---|
| D26 R3d f81cafc24d3a | 915 | 600 | **12: L392 L396 L400 L404 L412 L416 L456 L460 L464 L468 L476 L480** (`o_ectl_Q_N_eN`, fixed 8, source 6, destination 0) |
| D27 3d152d53d5b5 | 916 | 600 | 12: the tN lanes L395 ... L483 (fixed 8, source 6, destination 4), already known |

- R3d: the eN +2 of N3 is a bind pad that follows the tN station count (`n3_rows.py` line 4), not a station row. Fix: `n3_cycles.py`
  raises tN only (8 -> 10), eN stays 6; recompose. Same script for the next D27 compose.
- D27 has no other mismatch: L356 (87 = 9 + 78), the KV-SYSC-1119 rows and the 351 re-spaced forward legs all agree.
- Not replayed: the latency-table depth checks (`cycles < base + stations`) and LATCHECK; both tables were regenerated by `gen.py latency`.
- New rows that will need cycles with them: 1b (24 lanes +1), a 7th station on `o_dcal_flt` / `o_dcal_tks`, any hgi_v1 collector row.

## 3. The 20 held placed rows (all KV-D25e3, runtime without `OT_PLACE_MAX_TRANSITION`; no CTS result on any)

| Rows | Place WNS | Worst path class (V) | Cleared by |
|---|---|---|---|
| pv_v1, v2, v2n, v3, v3n, v4, v4n, v5, v5n, v7 (10) | -4,402 to -26,168; 7,333 to 16,636 setup ends; 15k to 38k slew violators | inside one pad delay line `u_pd<N>_*_t_<k>.r[j]` -> `.q` (astk owner_response, pvw ctl_cmd, vport vo): 2 cells, one unrepaired long wire | pad trunk rows of OPUS-FIX-KV-PV-R3 (pad_min_stations 16 + hop latch placement) and a regen with the slew limit. Not D26; D26 "pv station 300" does not touch this class |
| the same 10 + pv_v1n | -425 to -2,224 (asynchronous) | leaf-tap reset to `u_bin_*` | 1a (RESET-RELAY-GEN-R2) |
| pv_v1n | -7,679 | `u_vport_E.fault` -> `u_ist_o_vport_E_N_f_0`: flop to first OUT station, unstaged | first-hop row, OPUS-FIX-KV-PV-R3 |
| sys_c a7 | -986.6 | L356 `i_serdes_E_tx_up` -> `o_dcal_dob[2]` | D27 row (a). Next: reset -241.9 (1a), then 16 `cland_fstart` groups to -241.8 (ideal-clock class) |
| hub_Wo a9 | -1,039.6; 4,074 ends | efault reduce | D27 efault_stage (1e, with `at_um`). Next: `cland_fstart` -206.4, reset -119.9 (1a) |
| hub_Eo a3 | -747.0; 6,236 ends | `u_bin_i_host_die_rst_n/q` -> core `u_astk_EN` reset port | form M D 8 (RESET-RELAY-GEN-R2, place proof running on epyc10). No D26 / D27 row yet |
| hgi_v1__cl141fc26e a2 | -410.1 | landing monitor fault -> collector, 1,320 um | no row in D26 or D27 (1e) |
| hgi_v3, v5, v6, v7, v8 | -315 to -353 | port -> hard landing core, ideal-clock constant (floor -275) | nothing to fix in the plan. Review rule 81c8692c1cdf (clk group, cland-port exclusion) clears the test; D26 lockups fix their real blocker (hold). These D25e3 kits stay unrouted; the D26 kits replace them |

## 4. Ranked fixes (by held + failed rows unblocked)

| # | Fix | Rows | Owner |
|---|---|---|---|
| 1 | `u_bin_*` reset to the nearest tap for every type (bind class fix; per-type rows until then) + form M on hub_Eo | 14 held (11 pv, sys_c, hub_Wo, hub_Eo) | RESET-RELAY-GEN-R2 |
| 2 | pv pad trunk rows + slew-limit regen; pv_v1n first hop; pv_v6n ft9_i band | 11 held + 1 failed | OPUS-FIX-KV-PV-R3 |
| 3 | R3d: eN back to 6 (`n3_cycles.py` tN only), recompose, re-gate; then apply D26 | unblocks D26 (8 hg holds, hub_Wi, pv_v8, hgi) | KV-PLAN-R2 |
| 4 | efault_stage on `kv3_.*` with `at_um` at the fault writer | hub_Wo + 28 exposed types | KV-PLAN-R2 |
| 5 | pc_v1 kf third bank + 24 lanes 2 -> 3 | 3 failed | KV-PLAN-R2 |
| 6 | split view re-export (obstruction form) | 2 failed | KV-PLAN-R2 |
| 7 | hgi_v1 collector station row | 1 held | KV-PLAN-R2 |
| 8 | hub_C view re-freeze | 1 failed | KV-PLAN-R2 |

## 5. Stop list

- Do not wait for the running R3d bind (unit oth-ubuntu-2269370-1795228393) to finish green; it cannot. Do not run `apply_d26.sh` on f81cafc24d3a.
- Do not add `n3_cycles.py` as it stands to the D27 compose.
- No more reset relays, no re-site of the reset tree and no relay depth change for sys_c / hub_Wo: the tree is not the cause.
- No M6/M7 power pins on the split pc views and no re-harden of them before the obstruction export is compared.
- No third kf bank without the 24 lane cycles; no relaunch of the 3 pc_v1 kits, the 2 pc kits or hub_C on the unchanged plan.
- No route release of any of the 20 held D25e3 rows. No regen of the pv rows "for the slew limit" alone: the reset and pad-trunk paths remain.
- Do not remove `auto_visual_review_skip ["kv3_hgi*"]` before the pinned runtime carries 81c8692c1cdf.
- No claim that D26 clears a held row, or that D27 clears hub_Wo before the `fault` output hop is sited.

## 6. Not checked

- Bin positions come from the landing ring boxes, not from a DB. Endpoint counts per class. The pv slew figures per path.
- The view export options behind 1c. The epoch-bit bin site in 1b (geometry inferred from the row).
- LATCHECK and latency-table depth for section 2. The D27 bind result (bind.log empty at 18:5x).
- Whether the hub_Eo form M proof on epyc10 has a place result.
