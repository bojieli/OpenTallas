# KV D29 private placement review, 11-23 14:4x PST

All six exact placement layout and density images were opened. The four standalone D29 runners finished placement but their initial render wrapper was refused by the isolation guard because its destination was outside the declared kit directory. The recovered render jobs declared the existing enclosing work directory and read the completed `3_place.odb`; they did not run synthesis, CTS, routing or timing. The conclusions apply to these exact private kits and do not lift active D28 or proposed D29 holds.

| Type / evidence | Placement review | Finding and next physical change |
|---|---|---|
| HGI v4 HK6, intel1 `/srv/opentallas-scratch2/claude/kv-d29-a/hk6_hgi_v4_place` | Clear macro geometry on this probe | Four-by-four large-macro array leaves open row and column channels. Modest local clusters beside the west macros and between middle rows do not form a wall. Preserve this geometry for the next strict candidate. The HGFORM v1p2 first-error below is a separate type. |
| HROOT B4, intel1 `/srv/opentallas-scratch2/claude/fam-kv-hroot-r1/d29geom/b4_place` | Clear macro-free placement, concentrated E/ST strip | Largest local density is at lower east, with lower edge and east strips visible. B4 has no macro obstruction or continuous central wall, but the E strip and late-detail-route defect of prior kits still need exact bound-form evidence. B4 configuration is not RHI proof. |
| sys_c RANKS 46f088d331af, epyc2 `/srv/opentallas-scratch3/claude/kv-d29-c/place_sysc_46f088d331af` | Hold, boundary locality | Large middle macro and four small north macros bound a discontinuous upper strip. Stronger isolated W-edge groups and empty body space confirm routing distance is a locality issue. Prior exact S1 ten-bit u_txcal to att-tx crossing spans ~1.3 mm. Keep SYSC-D2DOUT plus explicit boundary alignment in scope. |
| PC v1 cl23 BANK2, epyc9 `/srv/opentallas-scratch2/claude/kv-d29-d/pcv1_cl23_bank2_place` | Hold, longitudinal neck | Four paired large macro blocks leave a narrow vertical center seam. Four smaller macros occupy its adjoining windows and visible placement demand persists in the seam. Retain PC-GUTTER/G1 and keep all PC held for G1-G3 and exact new placement. |
| PV v5n row-B R7 west, epyc7 `/srv/opentallas-scratch2/claude/fable-fix-kv-pv-sinkspread/w/rowb_r7_kv3_pv_v5n_place/gen/kv3_pv_v5n`, ODB 5ae0d79a950c | BAD, center and SRAM access | 587,435 placed instances, 17 macros, local density 1.065. Strong center strip between banks with concentrated center-bottom macro access. Side aisles remain substantially less used. |
| PV v5ne row-B R7 east, epyc7 `/srv/opentallas-scratch2/claude/fable-fix-kv-pv-sinkspread/w/rowb_r7_kv3_pv_v5ne_place/gen/kv3_pv_v5ne`, ODB 41c0843b51db | BAD, center and cross-bank access | 574,771 placed instances, 18 macros, local density 1.203, pin track use 0.538. SRAM access converges on the middle and left edge. Pin, clock and channel reach remain unmeasured by this particular render. |

The split-family results support corridor and clock/sink locality work after the split. R7 functional proof remains distinct from placement acceptance. These exact standalone R7 kits predate the integrated K3e LANDCAP change.

## Other outcomes

- Inherited HGFORM `kv3_hg_v1p2_1123105128` read back OT_TAP_RESET_AFFINITY/SPLIT and OT_TAP_PAIR_MACRO in config.mk. It stopped before placement at GPL: the first exact tN epoch flop seat `(1006.04,1260.79)` is off the actual row/site grid. There is no GRT result for this attempt. Preserve exact seats and correct the physical row-grid transform before a fresh placement.
- Historical HROOT D27d3 private `kv3_hroot_1122093152` has an ODB and explicit OT_DRT_NO_PROGRESS at detailed route round 20 (24,261 violations), followed by wrapper rc21. The alert's OOM classification is incorrect. Separate D28 shared `68bb968a0a3e` is watchdog DRT (best 1489 vs pre-window 1269); neither older branch warrants an unchanged restart.
- D28 PV v12 a3 separate exact review is `results/geom_review/kv_d28_pv_v12_a3_1123.md`. BAD. Do not use it as an R7 daughter measurement.

## Native placement diagnostics recovered

- HGI v4 HK6 ODB 312cbd55133e. The macro channels in the first image stay open. Native 3_5 placement bins quantify a repeated E-face boundary concentration at x1274.4 with peak 1.385 and 1397 µm spread on HST2 t1. Keep this form held pending edge-bank and fanout correction plus a new visual review.
- HROOT B4 ODB d13ad2155767. The E stripe peaks 0.856, with 649.4 µm nonclock fanout spread and 1645.573 µm root-to-sink centroid distance. Preserve open macro-free geometry and hold pending the RHI-enabled and clock-localized form.
- sys_c RANKS ODB ec400081dc82. Native placement flags 62 opposite-face spans, 1603.768 µm clock reach, 1618.1 µm nonclock fanout spread and 0.701 local density. The shifted D2DOUT candidate needs a new exact placement.
- PC23 BANK2 ODB 723e73929748. Native local density 0.919; full clock and channel reach remain unavailable in that render.
- R7 PV west/east synth top counts 375,324 and 355,938. The ODB instance counts above also include placement infrastructure.

## Inherited R7 v3/v3e reference forms, viewed 15:38 PST

Viewed exact OpenROAD native layout and density images of both E10 BANKCORE `354768183cef` reference forms. They predate the present D29 package. Both are BAD for any new route admission on these forms.

- E10 `/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D28/private/OPUS-FIX-KV-PV-R7/kv3_pv_v3_1122231545/gen/kv3_pv_v3/run/layout_review/place/{layout,density}.png`, SHA12 `f3f8f225fba7` and `0c0f7f33caa7`. Two macro columns leave a visible central opening, but the dominant cell strip crowds a horizontal lower aperture just below the two small central SRAMs, then turns into a long eastern boundary wall. Native peak local density ratio 1.108. Hot cells concentrate at the center intersection, south-center and east exit while other corridors remain sparse. Inherited route log previously restored TT `-738.53 ps` and screened true FF hold `-249.73 ps` across 23,679 endpoints.
- E10 same root, `kv3_pv_v3e_1122231609/gen/kv3_pv_v3e/run/layout_review/place/{layout,density}.png`, SHA12 `2b3d8560749f` and `084562c89446`. Native peak local density ratio 1.169. The lower cross-path is instead choked westward under u_g1_j, with a saturated western inlet, a narrow saturated vertical stitch parallel to the SRAM column and some concentrated NE bump approaches. Old TT restore `-1222.99 ps`; old GRT phase warned NDR drops. Separate focused CAD route diagnostics are historical only.
- Preserve these receipts as exact changed-form guidance. Distribute bank-access and output/cross-lane channels accordingly, then inspect exact fresh placement before any future route. Both latest controllers were inherited; this review starts no CAD route or STA.
