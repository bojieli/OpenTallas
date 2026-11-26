# Qwen compute HC1 and HC3 retained final layout review

I opened the native final placement and routing renders for the three completed E7 kits below and compared the specific visible routes with each kit's final timing and DRC reports. The current C1q type dictionaries match the retained kits' type dictionaries. The kits use older parent source bundles.

| Exact retained type | Visual review | Final reports and disposition |
| --- | --- | --- |
| East HC1 sle_hc1__cl22c1ff36__pve289215f | The north pin bundle follows a continuous west-side routing staircase. The lower collection street carries dense layered crossings where it meets the central XH and XL cells. The final route render and empty DRC report show this geometry can be routed on the retained kit. | Final setup worst −19.03 ps on XL1 internal woff→m. The TC virtual START input check is −170.01 ps to u_run_in. Exact matching parent START arrival is required before interpreting that check as a parent deficit. Keep timing and release holds. |
| West HC1 slw_hc1__cl3449ea95 | The same north-to-west routing staircase joins a crowded south edge. Two individual north sideband routes traverse otherwise sparse upper area. The final DRC report is empty. | Final setup WNS −113.64 ps, 8,792 failing setup endpoints. Worst path is internal to XL1_7 from g_flat final reduction to asm_d[0][23], so parent START timing cannot explain the main setup problem. Virtual START is also −170.86 ps. Keep held and trace shared West XL1 reduction/assembly timing. |
| West HC3 slw_hc3__cld86a7ad4__pvfd488b8f | The left vertical bundle and south escape are dense and continuous. The block retains open routing space east of its active cell banks. The final DRC report is empty. | Final setup worst +21.84 ps. The final report counts 1,578 failing hold endpoints, with the displayed TC boundary b_hw_i[1445]→u_bin_b_hw_i/q at −119.30 ps. Check the timing distribution and paired BHW producer before modifying the routed floorplan. Keep held. |

Each kit already contains its own final_placement.webp, final_routing.webp, 6_finish.rpt, and 5_route_drc.rpt under its run/reports/asap7 design directory. The reports are from the same retained kits as the reviewed images. The West HC3 type reviewed here is pvfd488b8f. It is independent of pvcca9ff41 in the HC3 cancelled-state investigation. No release decision or signed count changes.

## Exact E7 kit paths

- kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/sle_hc1__cl22c1ff36__pve289215f_1124052616/gen/sle_hc1__cl22c1ff36__pve289215f
- kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-C1O-COMPOSE/slw_hc1__cl3449ea95_1125084302/gen/slw_hc1__cl3449ea95
- kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-C1O-COMPOSE/slw_hc3__cld86a7ad4__pvfd488b8f_1125084746/gen/slw_hc3__cld86a7ad4__pvfd488b8f
