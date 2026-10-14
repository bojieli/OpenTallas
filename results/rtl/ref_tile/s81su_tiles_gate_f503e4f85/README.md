# s81su_tiles gate script, end to end, at main f503e4f85 (split-tap RTL)

`tools/s81_suhc/su_tiles_gate.sh OUT exact dpi` then `... OUT mutants dpi 8`, the two commands of composition gate
`s81su_tiles` (tools/ref_tile/composition_gates.json), run from a `git archive` of main f503e4f85 on ot-epyc1tb
(2026-10-13 14:27-14:42 PT, /srv/opentallas-scratch/claude/s81su-gtest/f503e4f85, deleted after this record).

- `exact.out`: `RUN full_dpi_m0_a0_h_t0 pass`, 0 / 1722 error rows x3 at 3,149 cycles (rc 0) = the gate's pass_regex.
- `mut.out`: 22 routed-top classes (the 21 original classes with swt -> swtl + swth and qbt -> qbtl), every class
  mutant fails with error rows; last line `SU_TILES_MUTANTS all 22 fail` (rc 1) = the gate's fail_regex.
- `tile_tops.json`: class -> mutant index and the slab instance sites of this build.

Scope: DPI float models (the loop form of the gate). The routed float primitives are covered by the `--fp rtl` record
`../s81su_tiles_gate_f6ff6785b/qualification.json` (21 classes); the split taps hold no float primitive.
