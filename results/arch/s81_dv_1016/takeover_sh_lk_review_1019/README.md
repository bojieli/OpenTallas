# SH lk APIPE8 gate review: structural fixes remain

Source start60b53a1f9, exact staged snapshot in gate_result.json; gate08:10:51 WARN0FAIL, not approved. GRT overflow0, M2 usage66.88%, pin geometryPASS3107/3107.

Actual placement-RC signoff-path report raw/pc.log shows TT reg->reg -41.8ps into u_h.host.u_hi.u_eng.apb_blk[31], hold+15.34ps. Gate WARN0FAIL does not qualify that negative data path. Textbook cone ap1_gs[7] -> apb_blk[28] is753ps/20levels. Reset source u_rsc.reset_pipe[1] still1074loads; u_rr reset257loads. Pipeline the block-address path and distribute kept reset copies; do not mask timing or reset paths.

CTS native diagnostic PASS launch96.89ps(jd_o1), capture175.94ps(f_host0), TT/FF pin spread21.5/20.8ps. TT all insertion279.4ps / FF229.4; boundary means255.9/209.8. Placement diagnostic, not routed qualification.

PNGs inspected: no macros (latticeN/A), uniform full-width std rows, four full pin faces, no isolated power islands. Density is broadly green with denser pin-register rims, clock at E mid. Outline254.88x151.2 (aspect1.686), nominal fill52.6%, CTS cells area21985um2 ~59.7%core. N1207pins/254.88=4.74, W596/151.2=3.94, E447/151.2=2.96; S fits fullface.

Checklist1 PASS source boundary registers + resetlanding2 (reset landing itself2sinks). 2 PASS tile diagonal296.3um<405; no macro. 3 FAIL reset1074/257 loads. 4 FAIL realTT -41.8ps + lint753ps. 5 source runtime storage audit still required (no macros reported; inherited host SRAM must be checked, not waived). 6 PASS outline/std rows/pin faces. 7 PASS spreads and io_hold0.03; parent must match boundary means. 8 APIPE7->8 already costs+1row-start bubble/IKEY; further fixes need pricing. No REVIEW.json or submit.
