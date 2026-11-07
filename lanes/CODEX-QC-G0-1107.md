# QC G0 disposition — 2026-11-07 06:43 PST

Read-only disposition of the existing report `/home/ubuntu/.local/state/fleet-viz/g0c_reports/qwen_compute_plan_of_record_plan_qc52.json.g0_report.json`: **20 errors = 13 hard_cores + 4 geometry + 3 hard_pinreg**. No new check, build, plan edit or credit change. This is the report's captured effective plan; the stale local POR file is not used as its replacement.

The 13 hard-core findings are three collector origins and five origins in each of two SU1 clones. They are representation debt: re-encode each physical origin on the 8.64 µm lattice and carry the residual in `track_offset_um`, preserving `origin_um + track_offset_um`, orientation, outlines, pins and cycles. This is a candidate correction for the plan owner; no already-written QC lattice fix was identified in the bounded current queue review, and none was applied here. The existing S81 split-core lattice/track-offset precedent does not constitute a QC fix.

| Report row | Type | Core | Report origin µm | Disposition |
|---|---|---|---|---|
| 45 | `coll_core` | `g_xf_1` | `[203.04, 1105.92]` | Private representation correction needed; preserve effective physical position. |
| 46 | `coll_core` | `g_xf_3` | `[406.08, 1343.52]` | Private representation correction needed; preserve effective physical position. |
| 47 | `coll_core` | `g_pf_3` | `[8.64, 1319.04]` | Private representation correction needed; preserve effective physical position. |
| 48 | `slw_su_l1__clcc9d0155` | `cl_cws0_i` | `[439.776, 1280.88]` | Private representation correction needed; preserve effective physical position. |
| 49 | `slw_su_l1__clcc9d0155` | `cl_flt_su_c_i` | `[581.04, 17.28]` | Private representation correction needed; preserve effective physical position. |
| 50 | `slw_su_l1__clcc9d0155` | `cl_rsn_i` | `[184.896, 4.32]` | Private representation correction needed; preserve effective physical position. |
| 51 | `slw_su_l1__clcc9d0155` | `cl_x_su_c_i` | `[527.04, 179.28]` | Private representation correction needed; preserve effective physical position. |
| 52 | `slw_su_l1__clcc9d0155` | `cl_x_su_c_p1_i` | `[539.136, 400.896]` | Private representation correction needed; preserve effective physical position. |
| 53 | `slw_su_l1__cla2a78701` | `cl_cws0_i` | `[439.776, 1280.88]` | Private representation correction needed; preserve effective physical position. |
| 54 | `slw_su_l1__cla2a78701` | `cl_flt_su_c_i` | `[581.04, 17.28]` | Private representation correction needed; preserve effective physical position. |
| 55 | `slw_su_l1__cla2a78701` | `cl_rsn_i` | `[184.896, 4.32]` | Private representation correction needed; preserve effective physical position. |
| 56 | `slw_su_l1__cla2a78701` | `cl_x_su_c_i` | `[527.04, 179.28]` | Private representation correction needed; preserve effective physical position. |
| 57 | `slw_su_l1__cla2a78701` | `cl_x_su_c_p1_i` | `[539.136, 400.896]` | Private representation correction needed; preserve effective physical position. |

The active `src_b44ba_qc4/plan_qc53_candidate_v4.json` and both private `dq87t/<SU1>_vS/plan_v4_ringviews.json` still contain all five off-lattice SU1 origins. `cl_rsn_i` has moved from the report's `[184.896,4.32]` to `[4.32,25.92]`; its x remains half-lattice, so that coordinate change does not establish resolution. The other four origins match the report. Private SU1 copies add six real signed-ring LEF/lib references only; this fixes the earlier `hard_landing KeyError lef` class, not the lattice or station class. Both kits remain private, with four contract children.

| Report row | Type | Slot / stage | Finding | Disposition |
|---|---|---|---|---|
| 177 | `slw_su_l1__clcc9d0155` | `cws0` stage4 | 63 actual-bit sites intersect `cl_rsf_i`, first reported bit172 | Unresolved plan geometry; explicit station re-site needed. |
| 178 | `slw_su_l1__clcc9d0155` | `rsf` stage1 | Same63-site intersection | Same private candidate correction, with counts/cycles preserved unless a priced new form is required. |
| 179 | `slw_su_l1__cla2a78701` | `cws0` stage4 | Same63-site intersection | Same class and correction. |
| 180 | `slw_su_l1__cla2a78701` | `rsf` stage1 | Same63-site intersection | Same class and correction. |

The private plans retain the captured `cws0` and `rsf` bit-site arrays. DQ87-TYPES posted PLACE/LEC passes, but the current SU1 followthrough owner confirms there is no actual station-resiting evidence. Keep these four findings open; do not infer clearance from PLACE PASS. Existing healthy GRT work continues. This is separate from SU0's outgoing-bundle pipeline redesign.

| Report row | Type | Missing report dependency | Disposition |
|---|---|---|---|
| 182 | `phy_serdes` | `physical/qwen_missing_phy/nface_tall_1017/ot_qfd_serdes_112g_x12_phy_s597/ot_qfd_serdes_112g_x12_phy_s597_tt.lib` | Dependency resolution/capture debt; existing exact file is present in full checkouts. |
| 183 | `phy_serdes_b` | Same SerDes TT library | Same single dependency; no PHY rebuild or replacement library needed. |
| 184 | `phy_ucie_kv` | `physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_tt.lib` | Same capture/path class, second existing dependency. |

Both full checkouts `/home/ubuntu/OpenTallas` locally and on Intel2 contain those exact paths: SerDes16562bytes and UCIe17474bytes. These same three sparse-checkout missing-library findings were already documented by DIE-QC-59 on11-01 and the earlier G0 lane. The fresh temporary release-tree capture still reports them, so its dependency closure or relative source-root resolution must be corrected by the counter/capture owner. Do not present this as absent physical collateral, a newly failed PHY, or a new sign-off gate.

Evidence read: existing fleet-viz report; E2 `kw27/src_b44ba_qc4/.../plan_qc53_candidate_v4.json`; E2 `dq87t/mksu1.sh` and both `*_vS/plan_v4_ringviews.json`; queue DQ87-TYPES03:53/05:09 and DIE-QC-59; existing full-checkout PHY library paths; current SU1 owner confirmation. No new validation sweep was run.
