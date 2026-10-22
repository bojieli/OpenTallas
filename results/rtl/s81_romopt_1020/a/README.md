# S81-ROMOPT-A (10-20): O1 GU_MERGE + O2 12 q pairs default ON in the S81 die compile

Owner 10-20 ~08:45: implement the ROM-layout options now, as ROM contents and compiler only. No tile re-closure, no RTL
change, and physical views stay byte-identical. This sub-lane covers O1 (gate ++ up merged) and O2 (all 12 q pairs with
pair rotation), made default ON together with CALPIPE.

Branch claude/s81-romopt-a-1020 is based on claude/s81-romopt-1020 @7f845e6e0. The fleet dir is
ep9:/srv/opentallas-scratch/claude/s81-romopt-a. Its root is the s81-rate3 root plus this branch's tools/s81_dv,
tools/s81_slice and toksim_s81_compose.

## 1. Release defaults (tools/s81_dv/layer_prog/xs_flags.py)

| option | default | role |
|---|---|---|
| OT_XS_GU_MERGE | 1 | O1: gate ++ up of one expert placed as one matrix (gu 24 -> 18 phases, shared 4 -> 3) |
| OT_XS_QPAIRS | 12 | O2: all 12 q pairs, active subset rotated per phase (wq_b 15 -> 11, wo_b 5 -> 4, idx.q 8 -> 6 phases) |
| OT_XS_CAL_SEGMENT | 1 | reused calendar intervals; layer rows 1868 / 2006 <= 4096 |
| OT_XS_TOPO, OT_XS_PROP | 1, 1 | real 122-frame topology; the legacy 8-owner deal compiles phantom rows (RATE3) |
| OT_XS_COMPACT_TAILS | **1** | short tails allocate only their real super rows (O2 capacity). Qualified here on all 5 FP ops x 4 frames; costs +2 edges on wq_b / wo_b |

- An environment value always wins. `=0` selects the legacy behaviour of that option.
- **O1 only** (the O1 measurement): `OT_XS_QPAIRS=10 OT_XS_COMPACT_TAILS=0`.
- `OT_XS_LEGACY=1` makes all the legacy values the defaults, so every pre-10-20 record reproduces.
- xs_place.py, xs_topo.py and xs_field_calendar.py read the flags through xs_flags. The xs_place diff is small.
- Measured span tails are in `xs_field_calendar.ROMOPT_TAIL`, keyed by (QPAIRS, COMPACT). Each tail is the max over the
  benched frames.

## 2. CAP emitter fix for GU_MERGE (compiler only; no RTL)

**Cause.** `xs_calendar.cmd_cap` refused GU_MERGE=1 with 'slice share not contiguous'. A slice owns gate j and up j for
j in [a, a + n), which is two disjoint row runs. ot_s81sl_cap decodes only one range per cfg_d:
- e = tag - rbase < rcnt
- leaf = (e >> 6) % 5
- word = obase + 64 (e >> 6) // 5 + e % 64

**Fix (`xs_place.merged_cap`).** The compiler-written frame row tags of a merged matrix are:
- gate j -> 640 s + (j - a)
- up j -> 640 s + 320 + (j - a)
- cfg_d: rbase = 640 s, rcnt = 320 + n, obase = the unmerged gate region (2 x 64 words allocated).

Every row then decodes to the same (leaf, word) as the two-matrix placement, so the consumer layout is unchanged.
Tags of other slices fall outside the range and fault (F9). Tags stay below 2^14, so row[15:14] remain free for the
flags, and rcnt fits in 11 bits.

**Deal change.** Each frame now takes whole (gate j, up j) pairs, gates first. Gate j and up j share a CAP pairing slot
((row + 8 pos) mod 64), and this order keeps them out of the same phase. Phase counts are unchanged (gu 18, shared 3).

**Check (`xs_calendar.py cap`, new `--die-src` for TOPO).** For every row of the layer it verifies four things:
- decode in range;
- distinct (leaf, word);
- other slices fault;
- **layout identical to a GU_MERGE=0 reference compile**: same (slice, leaf, word) for every row, same VP rows used, and
  0 gu pairing-slot collisions.

**Result: PASS for L0 / L2 / L14 / L20, in O1, O1+O2 and the default.**
- Faults 0.
- 30,336 / 34,432 / 40,832 / 34,432 rows decode with 0 differences.
- VP rows 1600 / 1664 / 1792 / 1664, equal to the reference.
- Evidence: static/cap_*.json.gz, static/cap_*.log.

**Still open, not caused by this change:**
- Down, wq_b and wo_b slices with spans over 64 rows already share pairing slots inside one phase: 512-696 cases a
  layer, with the same counts as the unmerged reference.
- The CAP consumer timing (FIN lifetime and registered cfg path; Codex consumer audit) is not admitted.
- Production `write_images` still writes phase-local tags. The rank or cap tags are applied by `gen --tags rank`, which
  now honours `cap_tag`.

## 3. Regenerated compiler output (L0 / L2 / L14 / L20)

**Frame ROM via-map + cfg7 images.** The legaliser ran in full (`imagesa.py`) on four frames:
- u_f_0L00 (8-frame slice, h9)
- u_f_2L00 (7-frame slice, h9)
- u_f_3L01 (6-frame slice, h10)
- u_f_3L02 (6-frame slice, h9_MX)

On every frame and every layer the legaliser faults are 0, cfg7 rows are <= 4096, and the pair fill is <= 8192. Per-image
sha256 values are in images_<cfg>/<L>/<frame>/manifest.json.

| cfg | L0 phases | L2/L20 phases | L14 phases | max fill L0 / L2 / L14 |
|---|---:|---:|---:|---|
| O1 (images_o1) | 80 | 89 | 123 | 1088 / 1152 / 2224 |
| O1+O2, no compact (images_o1o2) | 75 | 82 | 99 | 1088 / 1152 / 1464 |
| **O1+O2 default (images_o1o2c)** | **75** | **82** | **99** | 1088 / 1152 / **1352-1448** |

The golden tie (`xs_place.py tie`, every placed row against the layer fixture) is bit-exact on all four layers in every
configuration (images_*/tie_*.json).

**Die field calendars.** These come from `xs_field_calendar.py die`, run for slices u_s_0S, u_s_2S and u_s_3S (the 8-, 7-
and 6-frame slices). The output includes field calendars, is_d, the shared calendar via-map images (sha256 in
compile/*/L*/images.sha256) and the CAP descriptors (above).

| cfg | wq_b | wo_b | shared_gu | experts_gu | down | wo_a | router | idx.q | layer rows L0 / L2+ | MU 46 AR / 10+1 MTP |
|---|---|---|---|---|---|---|---|---|---|---|
| O1 | 15/2060 | 5/828 | 3/653 | 18/2811 | 21/2892 | 12/2893 | 5/1269 | 8/1177 | 1868 / 2006 | 0 / 0 collisions |
| **O1+O2 default** | **11/1566** | **4/703** | 3/655 | 18/2811 | 21/2896 | 12/2893 | 5/1269 | 6/925 | 1868 / 2006 | 0 / 0 collisions |

Each cell is phases / compiled span. Every op is static PASS on every layer and every slice. The three slices give the
same die-wide phase list. The selftest is 23/23 in each of release, legacy and default+compact (static/).

## 4. RTL benches: release p4l RTL, bit-exact, Verilator 5.050

**FSEQ go-sequence benches (`fseqa.py`, 60 runs).** The tb_toksim_fgu_seq release frame exes are:
- v_h9nx_e5 (u_f_0L00, u_f_2L00)
- v_h10_e2 (u_f_3L01)
- v_h9MX_e1 (u_f_3L02)

Each run has one golden case and three mutants:
- **golden** at the compiler floor P: must PASS (bit-exact values and cycle-exact RET).
- **calendar P-1** (down: P125 and P120, because P129 has margin): must FAIL.
- **swap** (two q elements' ROM images exchanged): must FAIL.
- **shift** (expected RET +1 edge): must FAIL.

**All 60 runs behave as expected** (summary.json `fseq_bad = []`). Fail witnesses are check_*.log and run_*.log.gz in
each fseq_<cfg>/<frame>/<op>/.

Max measured span over the four frames:

| cfg | wq_b | wo_b | shared_gu | experts_gu | down |
|---|---:|---:|---:|---:|---:|
| fseq_o1 (O1) | 2060 (15 ph) | 828 (5) | 653 | 2811 | 2892 |
| fseq_o1o2 (O1+O2, no compact) | 1564 (11) | 701 (4) | 655 | 2811 | 2896 |
| fseq_o1o2c (default) | 1566 | 703 | 655 | 2811 | 2896 |

**Single-phase release frame bench.** This is the S81-ROMCAP col_h9_l4 / LK5 binary, as used by ROM12 bench12
(`bencha.py`):
- experts_gu phases 1-3 and wq_b phases 1-2 PASS.
- The swap and shift mutants FAIL.
- This holds for O1, O1+O2 and the default (bench_*/).

**Sources.**
- rtl/<build>/sources.sha256 lists every one of the 78-79 build sources. All of them match the bench root, except the
  FSEQ testbench, whose sha 54da91d2 is the committed results/rtl/s81_rom12_codex_1020/fseq_src/tb_toksim_fgu_seq.sv.
- The binary sha256 and the verilator.version (Verilator 5.050 2026-07-01 rev v5.050) are recorded per build.
- bench_*/rtl_sources_checked.log: all OK.

## 5. Physical views unchanged

The diff check was:
`git diff --name-only origin/main...HEAD | grep -E '^physical/|\.(lef|lib|gds|def|odb|v|sv|svh)$|^rtl/|macro|abstract'`.
It returns only testbenches and evidence copies under results/ (the ROM12 / RATE3 benches). Nothing under physical/ or
rtl/ changed, and no .lef / .lib / .gds / .def / .odb file changed.

**ROM macros used by the frame q / BF elements and the calendar ROMs.** These are
physical/asap7_memory_macros_v2/ot_rom_4096x274_m8 and ot_rom_4096x72_m8.
- Their .lef, .lib (tt/ss/ff) and .v hash the same on origin/main and on the branch.
- The bench's ROM models are the same files: sha 9e83cdca / f9606abe in every build's sources.sha256.

**Why the views do not depend on ROM contents.** The generator is tools/mem_compiler/rom_gen.py, a via-programmed NOR
mask ROM:
- The macro is compiled once. Every cell carries its transistor, and only the drain via differs.
- The LEF holds no content, and the Liberty is characterised with every via present.
- The personalisation is a separate per-instance `<INSTANCE>.viamap.hex`. The behavioural .v loads it by `$readmemh` from
  `+OT_ROM_DIR` or `VIAMAP`.
- rom_gen.json records `content_independence` for the lef and the liberty.

The compiler outputs here are exactly those viamap files (plus cfg7 / xs ROM viamaps of the same macros). No option
needed a physical view.

## 6. Token rate (compose_a.py = RATE3 compose_rate3.py rule; compose/)

Only measured, bit-exact spans are substituted:
- Each op value is its compiled span. The span's tail is the measured FSEQ max over the four frames.
- Each op keeps the record's unchanged wire / CAP adder.
- wq_b uses the spine-go origin, the conservative ROM12 convention.
- 160 nodes are substituted per op.
- shared_gu is a parallel node, so it is not substituted (as in RATE3).

The die calendars come from compile/fcal_<cfg>_u_s_0S.

| scenario | AR tok/s | MTP tok/s |
|---|---:|---:|
| baseline: CALPIPE as on the branch (8-owner record) | 915.9 | 2,869.4 |
| after O1 (GU_MERGE, 10 pairs, real-frame compile) | **934.9** | **2,919.7** |
| after O1+O2 (release default, compact tails) | **953.1** | **2,967.8** |
| O1+O2 without compact tails | 953.3 | 2,968.1 |
| O1 + F8 window prefetch | 947.4 | 2,949.1 |
| O1+O2 + F8 (RATE3 contents-only headline config) | 966.2 | 2,998.1 |

## 7. Open items (not this sub-lane)

- **Per-stage expert map and exact ROM capacity (S81-ROMOPT-B).** Compact tails are now the default, which lowers the
  per-pair fill (L14 1464 -> 1352-1448).
- **Multi-slot legaliser O3 (S81-ROMOPT-C).**
- **CAP consumer timing qualification**, and production row tags in write_images.
- **The F8 SVC MU-occupancy check.**
