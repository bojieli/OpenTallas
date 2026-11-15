# FABLE-PD-PHY-0710: QC + KV PHY types, undiagnosed failures (2026-11-15 07:10 PST)

Scope: technical PD. Read-only review; no builds launched. Sources: `autopilot/kit_wave_stages.tsv`, `autopilot/log.txt`,
`tools/failure_breakdown.py` (06:42 run), plans S3P_2 / S4P on epyc9, signoff.json records on epyc2 / epyc10 / rtx-pro.

## 0. Result in five lines

1. QC "other flow error" is 15 rows now (was 11): 3 PHY rows + 12 kit_rtl rows. All 15 are FLOW. None is a P&R design result.
2. The 3 QC PHY types need no sign-off: the counter already takes them out of both totals (127 of 130). The wave still tries to build them: 35 failed attempts.
3. One real design defect sits behind the PHY rows: the plan of record S4P pin windows are not on the PHY macro pins (up to 383 um on N faces, 2,972 um on phy_serdes_b). Fix by regenerating the modeled abstract, not by moving plan windows.
4. New live QC flow blocker found: `feed_s29.json` and `regions_s29.json` exist next to the S4P plan on epyc9 only. 21 gen FAILs in 7 min (06:36-06:43); it will hit the 39 re-keyed rows on 5 of 6 gen hosts.
5. KV kv3_phy and kv3_phy_v1 are both signed off and counted (KV 5/56). The two wave rows are stale rows of older attempts.

## 1. QC: the 15 "other flow error" rows

| rows | items | stage, event | exact error | class |
|---|---|---|---|---|
| 2 | phy_serdes (a13), phy_ucie_kv (a14) | gen, S3M2 | `gen phys: ERROR hard wrapper <type>: requires a placed macro with LEF and TT/FF views` | FLOW (wave builds a hard-IP type) + plan content (section 2) |
| 1 | phy_serdes_b (a8) | kit_topology, S3M2 | `ValueError: native clock table must resolve inside its declared native base` (item plan `tl-qcphysdb/por/plan_s29_qc103_phyb.json`) | FLOW, same cause |
| 6 | sle_ctl__cl372cea1c, cl503337ff, cl503337ff__v1, cl67434795, cl67434795__v1, cla4f6f12f | kit_rtl, S4P | `bind: ERROR preferred HDL source missing`: `treeA/physical/qwen_missing_phy/.../ot_qfd_serdes_112g_x12_phy_s597_bb.v`, `.../ot_qfd_ucie_x64_phy_bb.v` | FLOW, kit input missing |
| 6 | sle_st_a_v1 x3, slw_st_a_v1 x3 | kit_rtl, S4P | same | FLOW, kit input missing |

- The 12 kit_rtl rows are the same class as the 27 "kit input missing" rows: 143 FAIL lines on 60 items, 05:54-06:33. They read "other flow error" only because the stage-table reason is cut at 240 characters and the `PROVISIONAL[...]` prefix fills it, so `FAIL_MAP` never sees "preferred HDL source missing".
- Already fixed by KIT-OPS-5 (06:5x RESULT c): sources copied to 5 hosts, 39 rows re-keyed. Checked: the three files are present on epyc7/8/9/10, intel1, epyc2. The 12 rows relaunched at 06:46.

### New blocker behind it (not yet owned)

`clock_landings.LandingError: count frame files not found: feed plan_of_record/feed_s29.json -> None, region map plan_of_record/regions_s29.json -> None` at gen: 21 FAILs on 14 items, 06:36-06:43 (cbf_q01_s2, cbf_q11, cbn_q01, cbn_q11, coll_core, sle_hc2, sle_sc_v2/v3, sle_stm_v2, slw_sc_v1 x3, slw_sc_v2, tt_ctlm).

| host | `die-qc-103/treeA/.../plan_of_record/feed_s29.json`, `regions_s29.json` | S4P plan |
|---|---|---|
| epyc9 | present (3cf41947b13e, f332354c7f8b) | present e7aff46e6130 |
| epyc7, epyc8, epyc10, intel1, epyc2 | MISSING | present e7aff46e6130 |

The same two files exist in `wt/qc-s29-tree2/.../plan_of_record/` on all 6 hosts with the same sha. The plan path moved to treeA; its two sibling files were not copied with it. One evidence row: cbf_q01_s2 attempt_6 on epyc10.

## 2. QC PHY types: root cause

Facts from the plan of record `zz_s29_qc103_s4p.json` (sha e7aff46e6130) against `zz_s29_qc103_s3p_2.json` (the plan the HARD-IP views were made on):

| field | S3P_2 (views archived 11-14) | S4P (plan of record) |
|---|---|---|
| contents `lef`, `origin_um`, `orient`, `physical_inst`, `physical_master` | set | absent (only `lib`) |
| module | `..._pw_phy_serdes` wrapper | bare macro name |
| phy_serdes N windows | 753.0-810.7 um, M5 (= macro pins) | 781.9-1036.5 um, M7/M5 |
| phy_ucie_kv N windows | 276.7-501.0 um, M5 (= macro pins) | 4.3-255.4 um, M7/M5, plus `phy_rst_i` |
| phy_serdes_b E windows | y 2216-2317, M6 | y 4.3-259.0, M6/M4 |

- S4P does not carry the S3P PHY form. `type_macros()` is empty without `lef`, so gen refuses. This is the exact `requires a placed macro` error. S3P was never adopted (S3Y G0 = 36 errors, DIE-QC-103 11-14 15:08), so the "credit on S3P adoption" for the three COUNT-DIRECT rows will never arrive.
- It does not need to arrive: `hard_ip_types()` in the counter classes all three as structural hard IP on S4P (QC types 127, 130 including hard IP). They are outside numerator and denominator.
- So for the count this is pure flow noise: phy_serdes 13, phy_serdes_b 8, phy_ucie_kv 14 attempts, BLOCKED-FLOW since 11-14 18:36, still in `only_items` and `hard_wrappers`.

### The design defect that stays (die level)

Macro pin geometry (LEF): serdes 1,199 FDI pins on the top edge, M5, pitch 0.048 um, x 753.0-810.6. UCIe kv: 1,171 FDI pins, top edge, M5, pitch 0.192 um, x 276.4-501.2. Macro fill of the partition: serdes 1563.57 x 2320.056 in 1563.84 x 2324.16 (4.1 um strip on top); UCIe 777.6 x 777.6 in 777.6 x 777.6 (0 um).

Distance from macro pin to S4P plan window, no cell site available in between:

| type (instances) | bus | macro pins | S4P window | lateral offset |
|---|---|---|---|---|
| phy_serdes (2) | tx_flit 597 | x 753.2-781.8 | x 909.0-1033.8 | 156-252 um |
| phy_serdes (2) | rx_flit 597 | x 781.9-810.5 | x 781.9-906.7 | 0-96 um |
| phy_ucie_kv (1) | tx_flit 583 | x 277.2-388.9 | x 130.0-252.0 | 137-147 um |
| phy_ucie_kv (1) | rx_flit 583 | x 389.3-501.0 | x 5.9-127.7 | 373-383 um |
| phy_serdes_b (1) | all 1,199 | N edge, x 753-811, y 2320 | E face, y 4.3-259.0 | about 782 + 2,190 = 2,972 um |

- N-face types: under the 405 um hop check, but unbuffered, and the 4.1 um strip holds about 85 M4 + 64 M6 tracks (4.1 um over the 0.048 / 0.064 um pitches) against 597 nets crossing one cut. The wires must run on M6+ over the macro (LEF OBS is M1-M5).
- phy_serdes_b: 2,972 um unbuffered is 7.3 x the 405 um hop check. The S3P form (E windows y 2216-2317) still left about 836 um; the archived record says `matches_every_pin_in_window: false`. COORD ruled that "by design" on 11-14; on the numbers it is a timing exposure on 1,199 nets.
- G0 does not see any of this: it checks plan window against plan window. The die GRT prototypes use plan-shape abstracts, so they do not see it either.
- The HARD-IP wrapper netlists carry 5 BUFx2 cells (3 epoch + 2 alias) with no row to sit in (PDN-0006 / PDN-0190). Not checked further.

## 3. QC: ranked fixes

| # | fix | level | owner | evidence / effect |
|---|---|---|---|---|
| 1 | Copy `feed_s29.json` (40,446 B, 3cf41947b13e) and `regions_s29.json` (11,275 B, f332354c7f8b) into `die-qc-103/treeA/physical/die_plan/qwen_compute/plan_of_record/` on epyc7, epyc8, epyc10, intel1, epyc2; re-key the LandingError rows uncharged. Extend the source guard to the plan's sibling inputs. | flow | KIT-OPS-5 | 21 FAILs in 7 min; 5 of 6 gen hosts |
| 2 | Take phy_serdes, phy_serdes_b, phy_ucie_kv out of the QC wave (`only_items`, `hard_wrappers`, `item_inputs.phy_serdes_b`); drop the 3 COUNT-DIRECT rows or mark them "not needed"; make `failure_breakdown.py` skip `hard_ip_types`. | flow | KIT-OPS-5 | 35 failed attempts; types are outside the 127 |
| 3 | Classify before the 240-character cut (strip the `PROVISIONAL[...]` prefix in `label()` or store the error first). | flow | KIT-OPS-5 | 12 rows mislabelled today |
| 4 | Regenerate the three modeled abstracts with the FDI pins on the S4P plan pin sites: per-bit x and layer from the type's plan pin table (`tools/qwen_missing/link_phy_gen.py --nface --tall`, `tools/qwen_kv_die/phy_gen.py`). LIB views unchanged. New view revision directory, as nface_tall_1017 was. | type (view) | new lane needed (TL-QCPHYSD ended 11-14 19:21) | offsets 96-383 um go to 0; no plan window moves, G0 untouched |
| 5 | phy_serdes_b: E-face pin variant. The generator already writes a west-face M4 block (`west=True`, tp8 revision); use it for the tall s597 frame and place the macro MY, or add an east mode. Pins on the S4P E windows y 4.3-259. | type (view) | same new lane | 2,972 um goes to 0 |
| 6 | Next QC event: add the window-free content fields to the three types (`lef`, `origin_um`, `orient`, `physical_inst`, `local_reset_pins` for UCIe). Windows stay. | plan (fields only) | DIE-QC-103 | makes the die views read the real macro LEF |
| 7 | After 4-6: one die-level pin-to-window check per PHY instance with the real macro LEF (0 um expected), then the die STA rows for the FDI pins from the macro LIB (TT clk->q 117.3 ps, setup 64.8 ps). | die | DIE-QC-103 | closes what G0 cannot see |

Not recommended: moving the plan windows to the macro pins (S3P / S3Y form). Measured 11-14: 36 G0 errors; needs the coll column left edge moved from 777.6 to <= 751.68 um across coll_s, coll_f0-f5, coll_n, tt_ctlm, coll_ucie.

## 4. KV

Both types are in `signed_types` of the counted plan (KV 5/56: kv3_io_ft, kv3_phy, kv3_phy_v1, kv3_sys_SD, kv3_sys_SD_v1). Since 06:5x the KV wave is under `hold_items "*"` (53 `schema.full_area_hard_ip` gen fails = source skew, held until MERGE-QUEUE-1 DONE), so the two rows now read "held by die owner".

### kv3_phy_v1, "timing after route" (wave row kv102fx attempt_3, epyc2, 11-14 01:19)

- Row: `TT -34.25 FF -204.04; late-ECO exhausted (1 it, 6,720.5 s): TT -34.25 -> -248.44, FF -204.04 -> -0.51, DRC 0`.
- Split of the FF hold (TYPE-KVPHY 11-14 00:42, from signoff.json): 297 violators; -204.04 is an input-port start (11 port starts); 274 are output-port endpoints (`o_phy_Q__sN_piN_d2/d3`, `rhN` against vclk out_min 55); internal reg -> reg is 12 endpoints at -10.94 ps. TT setup -34.25 on 3 endpoints is inside the -42 gate.
- Root cause of the FAIL: the wave late-ECO fixed port-start and port-end hold with delay cells and paid 214 ps of setup for it. The type itself had an 11 ps internal hold miss on 12 endpoints.
- Closed 11-14 01:48 by form B: resume from `4_cts.odb` with `OT_PREGRT_FF_HOLD=1`, guard 45, `OT_GRT_NONPORT_HOLD=1`. Record `epyc10:/srv/opentallas-scratch2/claude/type-kvphy/pg/kv3_phy_v1/signoff/signoff.json`: DRC 0, antenna 0, TT setup -18.72 ps (3 endpoints), FF hold internal 0, 264 output-port endpoints at -17.30 ps (parent), cells 2,818,275 as reported, outline 864 x 1520.64.
- Level: type. Owner: none needed for the type. Class fix: KIT-OPS-5 (late-ECO hold scope = non-port endpoints only, as GRT already does).

### kv3_phy, "re-sign (flow tag)" (wave row kv101ns provenance, epyc2, 11-13 20:18)

- Row predates the re-sign. AUTO-RESIGN RECORDED 11-13 22:51 on tag `flow-20261113-ai-kv`: verdict SIGNED, DRC 0, TT setup +15.65 ps, FF hold -1.67 ps on 1 port-start endpoint (`i_kvpc_Q_N_pc__po`, parent), LEC EQUIVALENT. Record `epyc2:/srv/opentallas-scratch3/claude/auto-resign/qwen_kvsys/kv3_phy__flow-20261113-ai-kv__0d63f21a/signoff/signoff.json`.
- Root cause: flow only. The wave stage table keeps the old provenance row because the re-sign ran outside the wave.
- Level: none (flow). Owner: KIT-OPS-5.

### KV fixes, ranked

| # | fix | level | owner | evidence |
|---|---|---|---|---|
| 1 | `failure_breakdown.py`: skip every item that is in `signed_types`, whatever its last wave row says (today only "signed (count pending)" rows are skipped). | flow | KIT-OPS-5 | 2 counted types listed as failures |
| 2 | Late-ECO: hold target on non-port endpoints only; stop if TT setup falls below -42. | flow, class | KIT-OPS-5 | TT -34 -> -248 in one 6,720 s iteration |
| 3 | When `hold_items "*"` lifts on kvgeom6: confirm both records against the kvgeom6 block before any re-key. Outline is equal (864 x 1520.64). Pin identity not checked here: compare `pins_canon_sha256 6b426b6b9289` (kv3_phy_v1 kit freeze.json) with the kvgeom6 freeze. | plan check | KV-102 | plan sha moved c4e85947 -> caf6cdfe |
| 4 | Die STA FF hold rows for the parent debts: kv3_phy_v1 264 output-port endpoints at -17.30 ps; kv3_phy 1 input endpoint at -1.67 ps. | die | KV-102 | signoff.json `io_hold_parent NEEDS_PARENT` |

## 5. Stop list

1. No more wave attempts on phy_serdes, phy_serdes_b, phy_ucie_kv (35 so far; they cannot pass and do not count).
2. No S3P adoption for PHY credit, and no plan-window move to the macro pins: 36 G0 errors, coll column shift.
3. No reliance on the phy_serdes_b "by design" ruling for die timing: 836 um (S3P) or 2,972 um (S4P) unbuffered on 1,199 nets.
4. No rebuild or relaunch of kv3_phy or kv3_phy_v1 on their old wave rows: both are signed off and counted.
5. No late-ECO run that targets port-start or port-end hold on a type (kv3_phy_v1 lost 214 ps of setup).
6. No QC S4P relaunch on epyc7, epyc8, epyc10, intel1, epyc2 before the two count-frame files are in treeA there.

## 6. Not verified

- Pin identity of the two KV records against kvgeom6 (only the outline).
- Wire delay of the PHY pin-to-window runs: distances are measured from LEF and plan, no STA was run.
- Which hosts the 21 LandingError attempts ran on, beyond the one epyc10 row; the file check on the 6 hosts is direct.
- AGIdock copies of the QC HARD-IP rows (read the rtx-pro copies only).
