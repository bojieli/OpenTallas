# QC private placement review, 2026-11-22

Viewed the four renders from the final placed databases. All four private forms are held from route. Each targeted change can be carried independently into the next candidate.

| Item and place unit | Actual placement and next physical change |
| --- | --- |
| `slw_hc1__cl68f9248e__cle683a076`, Intel2 2600428 | The relocated HC1 return is absent from the over-reach bus groups. The heaviest surviving grid tap carries 14,845 sinks and serves the concentrated lower cluster. The upper half has few cells. Refit the clock distribution on updated V3 placement before a continuation. Exact render and read are at `intel1:/srv/opentallas-scratch2/claude/qc-plan-r12/hc1_source_read/read` (read 1534912). |
| `sle_fw_v1__cl9d029624`, epyc9 3787447 | Five new SC_EO banks are present. Several central bands and the west landing stack remain dense while long side streets sit empty. The placed scan reports 1,187 over-reach bits and four over-cycle bits. Worst clock tap 5,729 sinks. Read 50326 and render are in `epyc9:/srv/opentallas-scratch2/claude/fam-qc-fefw/sc_eo_place/read`. |
| `slw_su_c__cl19bb38ef`, Intel1 1134332 | The grid tap peak falls to 2,903 in the placed snapshot. Eight taps overlap macro footprints and 2,762 capture paths exceed 405 µm. Lower hard-macro streets remain dense. Run native cap/affinity recheck on this exact ODB to separate remaining overload from pre-CTS assignment. `intel1:/srv/opentallas-scratch2/claude/qc-plan-r12/suc_cap/read`. |
| `native59` formatter, Intel1 3999445 | The final legal placement retains 2,490 long capture paths, max 761.29 µm, with the formatter concentrated in the north-central channels between the SRAM rows. The distinct LOCAL32 form is in placement. Exact read 1482143 and render are at `intel1:/srv/opentallas-scratch2/claude/qc-plan-r12/native59_formatter/read_post_dpl`. |
