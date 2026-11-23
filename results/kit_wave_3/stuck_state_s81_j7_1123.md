# S81 09:39 STUCK-STATE and KV hub_C attempt 4

All 26 S81 rows in the alert are retired 07:34 J7 event `18a2688b741` forms with explicit current holds. The additional raw cancellation `slice_station__t40__clc8fb2c8c` is terminal SIGNED on E8 and was correctly excluded by the alert. The J8 lint-advisory placeholders are different from new runs. Inherited J7 sibling `col_h10_r1__t1__cld01bb4ae` route job `a3029c31fe27` is a separate exact case.

H10 R1 maps to COLY/ECORR in S81 J9 Wave A `520b067a45c9` (S81-COL-J9). The old `pva3a8bfd1` infrastructure retry became obsolete at the J8 event change. SerDes t1 stale cuts map to S81-MISC-SERDES-J9's revised family coverage. Its owner must identify the exact changed t1 form before any release. t2 additionally has the canonical falling-edge reset validator repair `0a1ed3c1330` and passing regeneration. Its prior independent physical BAD verdict still applies. Gunit maps to GUNIT-TAPS-1 with the gunit l1f/l1c relay changes in gate10c plan `0e32aea4d155`.

The 16 SVC rows are owned by S81-SVC-J9. The changed shared plan is the WESTRIP/engine-order/land-cap/edge-strip/tap chain. The three old source-wrapper usage failures also need the flat-IRG `2a24a958d7` compatible tool and strict rebind. Edited placement, then exact visual review, is required before route. No retry of a superseded input was submitted.

| S81 exact J7 cut | J9 disposition |
| --- | --- |
| `col_h10_r1__t1__cl95b37463__pv0713a75a` | COLY/ECORR changed H10 R1 form |
| `col_h10_r1__t1__cl95b37463__pv69c7e9a6` | COLY/ECORR changed H10 R1 form |
| `col_h10_r1__t1__cl95b37463__pv6a7ae122` | COLY/ECORR changed H10 R1 form |
| `col_h10_r1__t1__cl95b37463__pv86f5e3b9` | COLY/ECORR changed H10 R1 form |
| `col_h10_r1__t1__cl95b37463__pva3a8bfd1` | COLY/ECORR changed H10 R1 form |
| `col_h10_r1__t1__cl95b37463__pvce76611c` | COLY/ECORR changed H10 R1 form |
| `gunit__t1` | GUNIT-TAPS-1 + l1f/l1c on gate10c |
| `serdes__t1__clb45db5be` | SerDes J9 revised transport/relay form, exact binding owed by owner |
| `serdes__t1__clfe1f0815` | SerDes J9 revised transport/relay form, exact binding owed by owner |
| `serdes__t2` | SerDes J9 reset-validator recovery plus revised placed transport form |
| `svc_hi_dsdv_svc_pvso_entry__t1` | SVC split/realign, strict rebind and exact macro/face review |
| `svc_hi_dsdv_svc_pvso_entry__t2` | SVC split/realign, strict rebind and exact macro/face review |
| `svc_hi_dsdv_svc_rs__t1` | SVC split/realign plus strict compatible flat-IRG rebind |
| `svc_hi_dsdv_svc_rs__t2` | SVC split/realign, strict rebind and exact macro/face review |
| `svc_hi_dsdv_svc_rs__t3` | SVC split/realign, strict rebind and exact macro/face review |
| `svc_hi_dsdv_svc_rs__t4` | SVC split/realign, strict rebind and exact macro/face review |
| `svc_hi_dsdv_svc_rs__t5` | SVC split/realign, strict rebind and exact macro/face review |
| `svc_hi_dsdv_svc_rs__t6` | SVC split/realign, strict rebind and exact macro/face review |
| `svc_lo_dsdv_svc_rs__t1` | SVC split/realign plus strict compatible flat-IRG rebind |
| `svc_lo_dsdv_svc_rs__t2` | SVC split/realign, strict rebind and exact macro/face review |
| `svc_lo_dsdv_svc_rs__t3` | SVC split/realign, strict rebind and exact macro/face review |
| `svc_lo_dsdv_svc_rs__t4` | SVC split/realign, strict rebind and exact macro/face review |
| `svc_lo_dsdv_svc_rs__t5` | SVC split/realign plus strict compatible flat-IRG rebind |
| `svc_lo_dsdv_svc_rs__t6` | SVC split/realign, strict rebind and exact macro/face review |
| `svc_lo_dsdv_svc_rs__t7` | SVC split/realign, strict rebind and exact macro/face review |
| `svc_lo_dsdv_svc_rs_w__t1` | SVC split/realign, strict rebind and exact macro/face review |

## KV D28 hub_C

The inherited hub `kv3_hub_C@4` container `intel2:dpkit-kv3_hub_C-1760664` stopped at 09:39 under the standing watchdog after 131 minutes of stage-log silence. The final OpenROAD log proves that global placement actually converged at iteration 425, overflow 0.0987, and estimated parasitics in 12 seconds. Its last line at 07:23 was `Report metrics stage 3, global place...`. The retained kit has the `3_2_place_iop.odb` checkpoint, with no completed `3_3_place_gp.odb` or detailed placement image. The hang window is global-place metric reporting or immediate output, with the exact internal operation unresolved.

The free infrastructure retry was immediately refused by the current `VIS-COVERAGE.tsv` DRAFT gate, owner KV-102. The changed hub_C E row is in KV-D29 full K3 and needs the strict emitted candidate and exact placed render. The KV owner's corrected `46f088d331af` place-only probe covers sys_c, a different type. The old hub_C attempt is evidence for KV-D29/FAM-KV-HUBC-SYSC-R2 and FLOW-OPS. Its retry remains behind the existing visual gate.
