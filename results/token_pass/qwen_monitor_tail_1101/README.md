# Actual36-layer monitor-source invariance and finite tail candidate

Read-only inspection used all8 complete actual native-compact manifests and384 physical masks at intel2:`/srv/opentallas-scratch2/claude/codex-qc-programme-native-1131/rankN/{streams.json,lowered/mu_table_input.json,masks}` (source100bcd7ea). It did not use the older nominal-BTAB128 tree or infer unfinished ranks. No source images, caller, bench or RTL were changed.

**PASS_INVARIANCE_AND_TAIL_CAPACITY_ONLY:** for every slice/user, actual native457-bit instructions pidx3(XS),10(SiLU),11(XA) are bit-identical across all36 layers. The whole per-slice/per-user set is also identical across all8 ranks. This compares41,472 actual source words. Every rank's48 masks has zero physical rows covering logical3816..4095. The receipt includes all8 manifest hashes and slice-specific source words, not an inferred common word.

Current table-store capacity is106×36=3816 logical rows per slice, leaving280. Increasing every layer to eight PROG pairs/user would require114×36=4104 and does not fit4096. The concrete tail candidate preserves the106 stride and uses only8 rows per slice:

| Tail row | Local kind3 pair address | Low457-bit instruction | High457-bit instruction |
|---|---|---|---|
|3816+2u|6|same slice/user's XS3 → pidx12|same XS3 → pidx13|
|3817+2u|7|same slice/user's XA11 → pidx14|same slice/user's SiLU10 → pidx15|

The existing loader's user relocation maps local pair6/7 to global pair64u+6/7, hence instruction indices128u+12..15. For user3 these are396..399, within the native512-instruction space. Payloads already contain that user's actual VM/CROM relocation and must not be replaced with user0's bytes. The two XS payload halves are intentionally identical but retain distinct instruction indices and monitored calls.

`rank0_tail_candidate.json` contains every slice/user's exact candidate1051-bit ROM word and logical row. All8 ranks share these exact source sets; the independently emitted rank1..7 candidates remain in intel2:`codex-qwen-images-1101/monitor_invariance1131/`. The tail would raise used rows to3824 and leave272. It is a source candidate, not a new physical mask or installed programme.

## Exact monitor-call selection

The selected actual physical CALR decode segment has the following earliest source-family calls. Edges are accumulated stored deltas relative to that segment's start, not invented global dates:

| Family | Actual entry | Slice | Existing pidx | Relative edge | Dedicated candidate pidx |
|---|---:|---:|---:|---:|---:|
|attn XA|127|0|11|2368|14|
|resid1 XS|267|8|3|3387|12|
|SiLU|316|0|10|4268|15|
|resid2 XS|461|8|3|5372|13|

This is the existing `dv_lower_xhead.monitor_plan` rule: replace only the earliest producer command of each distinct family with its dedicated index; every other family command retains its original index. Do not use two resid2 calls for both XS monitors, reuse a Q/K instruction from another slice, or remap all12 XS calls. Native attention owners are0/1/2/5, matching the selected XA commands. Other slices' actual pidx11 is zero; the candidate copies those source halves without inventing a new instruction, and monitor14 must not be issued there. The installed selected image still has no12..15 commands; this table selects a possible source-preserving caller change, not an assertion it has happened.

## Loader window and cycle price

Current loader issues88 actual reads: six user PROG pairs and82 shared BTAB/CROM rows. A concrete address-sequence candidate appends two reads after the unchanged prefix:

- slots0..87: retain the exact current `row_addr(base,user,slot)` sequence;
- slots88/89: select3816+2u /3817+2u;
- keep the106 stage stride and existing1051-bit kind/address/payload interpretation.

The current7-bit slot counter and12-bit ROM address can represent those slots/rows. Kind3 local addresses6/7 already satisfy the existing `<64` validation and relocation. The last-read/last-capture/done markers must extend from slot87 to89 together. With unchanged capture/read pipelines, this adds **two occupied loader cycles per window**,1,666ps at833ps, and2.27% more reads. It is not free because words are invariant. A user with36 layer loads would occupy72 extra loader cycles (59,976ps); four such user streams occupy288 extra aggregate cycles. Whether those cycles are hidden from token latency is unproven.

The earliest selected monitor call is at relative2368, so source-level dates leave substantial room after a90-read load. However, actual table-request landing, last native write, concurrent `other_table_write`/busy windows and the common global reference must still be joined before declaring the load window safe. This inspection does not qualify new address logic or its physical timing. No load-window timing gate, RTL gate, caller activation or HEAD installation is claimed.
