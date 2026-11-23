# QC V3 SLE CTL south ingress review

Codex viewed the inherited `sle_ctl__cla4f6f12f` placement after the design watchdog stopped its route. Verdict **FAIL** for further route on that form.

Images viewed on E10 at `/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V3/private/QC-SLE-R5/sle_ctl__cla4f6f12f_1122180114/gen/sle_ctl__cla4f6f12f/run/layout_review/place/{layout,density}.png`.

- The south-edge B_TW landing feeds a dense stream north across the lower-left block and its obstructed path to the central controller. Several open regions have little cell demand. The exact round-10 report has 33,065 overflow, 29,496 H and 3,569 V. The dominant columns are x=240–320 µm and y=80–320 µm. The x=280/y=160 bin contributes 3,790. The most frequently named nets in the congested edges belong to `u_bin_b_tw_data_i` and the B_TW data bits.
- The north `fclk_in_cws1_i` M7 entry at (322.08, 1336.544) conflicts with its budget tap reference in preflight. That is a distinct issue from the south data funnel.
- Seat the incoming banks in separate legal paths toward the S and W controller faces. Preserve registered stage depth where those paths fit the reach limit. Price any additional cycles in the lane schedule. Restore agreement for the north clock entry and check its escape on the revised layout. Check pin alignment, routing capacity, and PDN continuity in the revised plan and placement.
