TOK-KV inherited actual FAROBS collection, 2026-10-29 23:23 PDT.
Inherited intel1 tok-kv-6-1029/kvl/far_v3, no duplicate/restart.
First far new_fault at near38569/far38287 =08 unexpected RX: rv1 ev0 es0,
epoch1 hdr00500, slot_bad0 crc_bad0. Expectation arrives at38571: +2 late.
Next HOST record38570 also08. Far abort38570, then KV misses the halted far's
WITNESS at39644 (04), as expected. Original far_v3 evidence retained untouched.
Source coupon (prior232307 receipt) independently measured Ccal +2 from raw
KV epoch->5forwardregs vs nativebc4EP_SKEW3. The existing compiler offset=-2
matches this phase; source HOST/PHY/native receiver passes corrected170.

Native target11 used to lose offset on image rebuild. d2d_cal_seq_image emits
D2D_CAL_OFS only when nonzero (zero historical header unchanged), and native
kv_static_programme reads it into --ofs. Actual66word rebuild on offset-2 image
PASS; old0 rebuild is CAUGHT at K words1,9,23. Malformed explicit metadata caught;
legacy missing field reads0. Four focused parser/coupling tests PASS.

Offset-only compile at oldattentionpad86 FAILS (retained log): native attention
requires1775 edges but shifted CMD gives1773. Coherent run_mu833 now correctly
reprices existing service pad86->88 from base1687, need1775. Full boot/programme
compile and new DCAL profile/frames still running at collection. No waiver.
No production RTL/clock change; no whole-token/G5/rate/physical claim yet.
