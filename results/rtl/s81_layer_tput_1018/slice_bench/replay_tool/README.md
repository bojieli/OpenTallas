# Cut traffic replay (LB2-S81/REPLAY, 2026-10-18)

Tool: `tools/s81_dv/dv_cut_replay.py` (subcommands `ages`, `gen`, `check`, `compose`). Self-test: `tools/s81_dv/test_dv_cut_replay.py` (ALL PASS, 26 checks).

The tool feeds each slice cut the traffic its outside neighbours send, at the cycles the compiled layer programme schedules. It also emits the words the cut must deliver to those neighbours, as checks.

- **Ages come from the die build.** Each lane's age is read from die.v: the `st_<lane>_<i>` stations and the `ld_<lane>` `.k` strap, with age = ceil(N/2) + k + 1 for a landed lane and N/2 for an unlanded one. Nothing is hard-coded, so the G8 rebuild is read the same way.
- **Stale programmes are refused.** If the programme's lane ages differ from the build's, gen stops with verdict STALE.
- **Multi-lane ports land together.** A port that spans several lanes is launched in one edge. It is checked when its slowest lane lands, so a bundle tear fails.
- **Encoded traffic:**
  - CTL line beats, with hops and src set as the ring stop delivers them. Each beat is derived at every stop on its line, using the build's ages.
  - SVCJ job words.
  - With `--host-boot`, the seq_host boot stream, f_lf, and the f_ks start.
- **Everything else is UNENCODED.** Such events make the replay `partial`, and `dv_layer_record collect` refuses a partial replay.
- **Lane sources.** Each boundary input lane is fed in one of three ways:
  - `schedule`: from the compiled programme;
  - `trace`: from the producer cut's own run (`--trace`);
  - `idle`.
- **Cross-cut check.** `compose` checks that cut A's landed output trace equals the input replayed into cut B.

## Witnesses (Verilator 5.050, ot-epyc4)

The vehicle is the G1 cut_3S build (bind9_g1, 615 instances), prebuilt object `s81-lbgap-g1/out3S_idle/obj`, with the tb sha in `cut3S_g1/`. The programme is `prog_L0_s3S`, and the runner is `run_w.sh`.

| run | replay | sim | check |
|---|---|---|---|
| w_sched | SCHEDULE | FAIL, 8 mismatches: the G8 bundle tear, the same as `dv_slice_replay` | FAIL |
| w_lane | DIAGNOSTIC `--lane-age` (each lane checked at its own landing) | PASS 32/32 | PASS |
| w_mshift | MUTANT `shift:xrW_3S_l0:1` | FAIL | FAIL (fail witness) |
| w_mcorrupt | MUTANT `corrupt:xrW_3S_l0` (bit 13 of the first word) | FAIL, 1 mismatch | FAIL (fail witness) |

On this vehicle the gen output is the same as `dv_slice_replay.py`: the input timelines are equal and out.txt is byte-identical.

## Current state on the integrated die (bind_p4l3_g123)

The committed L0 programme `compiler/prog_L0_s0S` was compiled on bind9, and its ages match bind9 exactly. On bind_p4l3_g123 it is **STALE**: 14 lane ages differ, because G3 landed the 0S lanes (for example xrW_0S 3.5 -> 9 and tvS_s_0N 8 -> 18).

L0 must be recompiled on the build. After G8, recompile it on the G8 build. `dv_layer_compile` now takes the landing age from the `.k` strap. K = E on every current landing, so this changes no output today.
