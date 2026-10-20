# TOKSIM-S81B/FGU 10-19: ffn.experts_gu / ffn.shared_gu measured on the release frame RTL

Vehicle: one die frame `u_f_0L00` (master col_h9_l4 -> `col_h9_l4_nx_b`, LK 5, slice u_s_0S, 10 q pairs) of the release
GEN mu4c (`claude/s81-bind-mu4-1019@19bf4121e`). The frame's full 82-phase L0 field (rank 0) is compiled once by
`xs_place.compile_frame` (tok2 `e9ed82c83` tools): real rank-0 rows, K 5120, FP4 expert / FP8 shared ROM images,
measured_class calendars, 0 faults. The frame holds 6 activated experts (61, 69, 112, 170, 299, 357) x w1/w3 x 5 rows
= 24 phases (4 + 1 rows each, 60 rows), and shared w1/w3 = 4 phases (10 rows).

Bench: `tools/s81_dv/layer_prog/qf_producer/tb_toksim_fgu_seq.sv` (tb_s81dv_frame + a go sequence + `+RETIRE`). The DUT,
the spine and the lane encoder are unchanged. Checker: `toksim_fgu_check.py seq`. It maps every RET word to its
phase's compiled calendar, shifted by that phase's go. Then it runs the unchanged `xs_place check` on each phase:
the golden segment-tree values must be bit-exact, every row's segments must be covered once, and every row must tie
to the fixture's BF16 value. Any GO_LATE, XO, FAULT or unassigned word fails the run.

RTL: 78 of 78 simulated RTL files are blob-identical to 19bf4121e (`rtl_blob_vs_release_19bf4121e.txt`). The only
file that differs is the new bench. Every run used Verilator 5.050 on ot-epyc9.

## Results (definition: go of the first phase at the spine -> last RET word at the frame root, edges)
| op | phases / rows | floor period P | span go0 -> last RET | fail just below |
|---|---|---|---|---|
| ffn.experts_gu | 24 / 60 | 145 | **3,680** (= 23 x 145 + 345) | P 144: frame FAULT status 11 |
| ffn.shared_gu  | 4 / 10  | 146 | **798** (= 3 x 146 + 360) | P 145: FAULT |
| shared + experts back to back | 28 / 70 | 147 (146 not run) | **4,314** | P 145: FAULT |

Single phase (job 3): go -> last RET = 346 for a 4-row experts phase and 345 for a 1-row one; shared 361 / 360. Swap
and shift mutants of p20 FAIL (errors 5 / 1).

Jobs:
- job 3 (`oth-ubuntu-711808-1792462925`): gen, singles, shared sweep at P 200..600. All PASS.
- job 3 experts sweep: hung in GO_LATE 4 for 2 h, killed. Cause: the bench tied the spine's `r_v` to 0, so the spine
  never retires an op and at most 4 tags can be in flight. This is a bench limit, not an RTL bug.
- diag1 (`oth-ubuntu-1081528-1792470443`): showed the hang at go 4; shared floor between 140 and 160.
- job 4 (`oth-ubuntu-1137230-1792470786`): rebuilt with `+RETIRE` (rows written back to the spine after each phase's
  last calendar word). Experts sweep 140..600; shared 141..200 at R1; R0 control at 160/200 is identical to R1.
- job 5 (`oth-ubuntu-1415027-1792471061`): the combined 28-phase run, and the floors at 141-144 and 146.

## What the numbers do not include (state when composing)
- The die wire is not included. Old DAG: r8 die wire 140 per phase + 28 s81_die_tiles. On a back-to-back sequence only
  one x round trip and one hub return tail is exposed. This matches the FIELD wq_b record, which also stops at the
  frame root.
- The rate is one uniform go period. Alternating 4-row and 1-row phases might space more tightly, so these values are
  upper bounds for this frame.
- Only one frame (u_f_0L00, L0, rank 0) was run. Other frames and layers are assumed to have the same 5-rows-per-matrix
  placement; this is not proven to be the critical frame.
- Owed edges not in the RTL of record: xg successor +1 on xw (x into the frames, +1 per instance if bound). CAP
  EDLY24/WL3DLY16 lands after the frame root, so it is outside this definition. The CFG7 PINREG +4 (XDLY 4) is already
  in the bench.
