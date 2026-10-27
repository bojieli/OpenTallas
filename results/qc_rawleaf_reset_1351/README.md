# Exact local QC rawleaf reset-capture correction

Source95444301f, independent geometry PASS codex/pv-review-1351-1027@1110109e1 results/geom_review/codex_pv_review_1351/rawleaf_successor_review.md. ParentQwen explicitly authorized this exact local placement repair, noRTL/pin/cyclechange.

Original input (read-only): intel2:/srv/opentallas-scratch2/claude/qc-a0-kits-1027/rawleaf/kits/ot_qwen_tile_lsl_rawfault_m3_a0k/run/results/asap7/kq_ot_qwen_tile_lsl_rawfault_m3_a0k/base/3_place.odb, kit23a47eb989d590c7.

Corrected actual checkpoint: intel2:/srv/opentallas-scratch2/claude/codex-geom-1351/rawleaf_anchor_local/3_place.odb. NativeDPL ot-run unit oth-ubuntu-3804312-1793135073 exit0, no displacement in the local legalization step. Input and output were mounted separately, original input read-only. Every unrelated cell was temporarily locked only during localDPL, then its original status restored; runtime assertions refuse any unrelated location/orientation change.

Independent exact compare establishes ONLYtarget u_ls.g_lrst2.g_rt[1].u_rt.q origin31.752,135.000/R0 ->31.860,129.060/R0 andPLACED->FIRM differ. All other geometry/statuses, instance inventory, ports and rows are identical. Complete pin-to-first-sequential maximum144.915um (old150.963FAIL);132465all-timedpairs/max155.790um/0over405/0loops;56172COREcells row/offrow0;Epin5.9/N.7. New actual full/zoom images personally viewed by independent reviewer. Normal source/canary/AP gates and eventual clock/timing/DRT remain; no route/signoff claim.

rawleaf_reset_anchor.tcl is the narrow source hook for this exact diagnosed master and row. place_successor.tcl reproduces the localDPL step with source kit at/src and fresh output directory at/out; it does not require a full kit copy. Existing failure records remain. Earlier rawleaf_anchor trial used unconstrained globalDPL, which moved unrelated cells: FAIL locality and not selected. Its output/logs remain in its distinct runtime directory. No old kit file was edited.
