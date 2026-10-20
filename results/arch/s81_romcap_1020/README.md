# S81-ROMCAP (10-20): ROM capacity and frame-phase packing on the p4l(-MU) release die

Task (COORD 02:45 item 3, COORD 03:02, OWNER 03:06): check ROM capacity before F10 (expert rows over 2 frames, AR
990 -> 1,140); report frames free per die; find out WHY p4l packs 2-12x more phases of one op per ROM frame than the old
die; give options with cost and AR/MTP effect. Contents-only (same ROM tile views) goes in this release.

Files: `capacity.py` / `capacity.json` (arithmetic), `project.py` / `projection.json` (the S81-RATE composer re-run,
FIX table copied from claude/s81-rate-gap-1020 540f0a0d4), `bench_gumerge/` (RTL frame bench of the one lever built here).
Code: `tools/s81_dv/layer_prog/xs_place.py` `OT_XS_GU_MERGE=1` (default 0 leaves every record byte-identical).

## 1. Why p4l has 2-12x more phases a frame: a compiler layout choice, not MU area

| op (L0, frame u_f_0L00) | old die price (m221pq, 1,792-pair field) | p4l measured | p4l rows/frame | rows/phase now |
|---|---:|---:|---:|---:|
| attn.wq_b | 1 phase | 11 (15 with idx.q) | 64 | 6 |
| attn.wo_b | 1 | 4 | 40 | 10 |
| ffn.experts_gu | 4 | 24 | 6 x (5 + 5) | 4 |
| ffn.down | 5 | 21 | 7 x 10 | 4 |
| attn.wo_a (BF) | 4 | 12 | | |

- **The hardware supports far more rows per phase.** The q element (`ot_v41_rom_elem_w10`, bound as
  `ot_v41_rom_elem_q_qxpq_w10` NB 2) takes NSEG = 8 segments in up to 8 classes per phase, with NCH 16 chain slots a
  lane. Its cfg7 row already holds all 25 words (8 segments + 8 classes + 1 + 8) for every phase.
- **The p4l compiler uses a small part of it.** There are three restrictions, all in software:
  1. `frame_return_plan` (D2, 10-17) legalises **one segment class per element per phase**. The docstring says "the
     cadence of several slots in one element is not modelled (legaliser refuses)".
  2. `xs_place` places **one matrix per phase**. A SwiGLU expert's gate and up rows (4.5 + 4.5 a frame) therefore take
     2 + 2 phases of 4 rows; the last phase of each holds 0-1 rows.
  3. Every phase uses the **same 10 of the frame's 12 q pairs** (`NPAIRS = 10`). nseg = 5 needs a multiple of 5.
     2 q pairs a frame (16.7 % of q ROM) are never written.
- **The old price modelled one 1,792-pair field with LPT placement and many segments per element**
  (`v41_rom_ksplit_bankmap`). The p4l DV die is 122 independent 10-pair frame fields, the safe-design regional choice.
  So rows per phase dropped from ~13-64 a frame to 4-10.
- **Not MU area.** p4l and p4l-MU use the same frame masters (`col_h9` 12 q + 3 BF, `col_h10` 12 q + 4 BF) with the same
  q element. MU hardware is in the slices and svc. The frame loss came from the p4h regional service slices
  (1,184 -> 1,130 slots) and is ~5 %.

## 2. Capacity (capacity.json; modelled, word = 256 data bits; FP4 64 / FP8 32 elements)

- Die: 122 frames (90 col_h9 + 32 col_h10), 1,464 q pairs.
  - All 12 q pairs a frame: 23.99 M q words. As compiled (10 pairs): 19.99 M.
  - One routed expert (rank quarter): 138,240 words. Dense FP8 per attention layer: 1.00 M (L0), 1.17 M (L2), 2.40 M (L14 Engram).
- Content: 40 x 384 = 15,360 experts a rank. That is 139.6 per die on 110 stages, or 158.4 on 97 stages.

| per die | fill, 10 pairs (now) | fill, 12 pairs | frames free, 12 pairs (196,608 words a frame) |
|---|---:|---:|---:|
| 110 stages, attention stage L0 | **101.6 % (does not fit)** | 84.7 % | 18.7 |
| 110 stages, L14 (Engram) | **108.6 %** | 90.5 % | 11.6 |
| 110 stages, expert-only stage | 96.6 % | 80.5 % | 23.8 |
| 97 stages, attention stage L0 | **114.5 %** | 95.4 % | 5.6 |
| 97 stages, L14 | **121.5 %** | **101.3 %** | -1.5 |

- **cfg7 phase budget.** The limit is 1,024 phases a frame programme: 4 rows a phase in 4,096-row banks
  (`xs_place.write_images` assert). The current 7 phases per expert need 1,037 phases at 139.6 experts. That is over
  the limit. With GU_MERGE (6 per expert) it is 898 phases, which fits.
- **Frames free per die today: none.** The 10-pair layout cannot hold the average stage. The 12-pair layout leaves about
  12-24 frame equivalents (110 stages). That is not enough to replicate experts, and replication would not cut phases
  under the static schedule.
- Caveat: no per-stage expert map of the release chain is committed. The case rows are averages, so a real stage can be
  heavier. The xs_place fixture compiles only the 6 routed experts (max fill 1,088 / 8,192), so its fill is not a
  capacity check.

## 3. Options (projection.json: estimates from measured laws, NOT prices)

E = S81-RATE set E (F1 F2 F2b F3 F4 F5 F6 F7 F8) = 1,022.4 AR / 3,189.3 MTP. C = owner MTP set (F1-F5, F8) = 953.6 / 3,017.1.

| option | what | contents-only? | AR / MTP (on C) | AR / MTP (on E) | status |
|---|---|---|---|---|---|
| **O1 GU_MERGE** | gate ++ up of one expert = 1 placed matrix: gu 24 -> 18 phases (P145); also fixes cfg7 1,037 -> 898 | **yes** | **980.8 / 3,090.2** | **1,053.6 / 3,271.1** | **built + RTL-benched (below)** |
| O2 all 12 q pairs | rotate pair subsets per phase. Capacity +20 % (needed to fit the stage). wq_b R 6 -> 8 (11 -> 8 phases, P126) | yes | 993.0 / 3,123.1 (+O1) | 1,067.8 / 3,308.0 (+O1) | compiler only; not built |
| O3 k classes/element | 2-3 segment classes per element per phase. gu 24 -> 12 (k2) / 6 (k3); down 21 -> 14 / 7 | yes (ROM images, cfg7, xs) | 1,055.2 / 3,287.9 (k2+O2) | 1,140.0 / 3,493.5 (k2+O2); **1,222.7 / 3,701.0** (k3+O2) | needs the legaliser to model multi-slot cadence and a frame-bench emission measurement (incl. MTP positions x chains) |
| F10 literal (2 of 8 frames a slice per expert) | | yes | | 1,140.5 / 3,494.8 (S81-RATE) | **rejected**: routed ids are data-dependent. Under the static schedule the worst case is all 6 experts on one frame pair, about 3x slower. Replicas do not fit (section 2) |
| More S81 dies | TP8 for the FFN halves rows a frame: about the F10 gain, for ~+440 dies, 8-way all-reduce and a new chain plan. More stages alone (fewer experts a die) does NOT cut phases: every routed expert keeps its full rows a frame | no (array) | | ~F10, minus collectives | next release |
| Fewer users per die | | | | 0 per user | **no effect**: phases are per token per user; frees no ROM; aggregate falls |

O3 (k3) supersedes F10 and needs no die, ROM-tile or array change. It is the largest AR lever found (+19.6 % on E).
It reaches the ~1,134 ledger floor at k2.

## 4. Measured: O1 GU_MERGE on the release frame (bench_gumerge/, ep9 unit oth-ubuntu-2505857-1792491949)

- Compiler: the L0 field of u_f_0L00 (all XS + BF ops), with legaliser faults 0 in both cases:
  - merge 0: 82 phases (experts_gu 24, shared 4);
  - **merge 1: 75 phases (experts_gu 18, shared 3)**.
  The golden tie (`xs_place.py tie`) is bit-exact for all 6 x 1,152 + 1,152 rows.
- RTL bench: col_h9_l4 LK 5 frame bench (`xs/xs_bench.sh`, the bench_xsp4 build), Verilator 5.050.
  - Each phase checks values bit-exact against the layer fixture and every return word cycle-exact against the compiled
    calendar.
  - Merged phases:
    - p1 (gate 0, up 0, gate 1, up 1: mixed): PASS
    - p3 (1-row tail): PASS
    - p4 (next expert): PASS
    - p18 (last expert, tail): PASS
  - Mutants: swap (two elements' ROM images exchanged) FAIL with 5 errors; shift (calendar +1) FAIL with 1 error.
- The merged phases have the measured shape (fp4, K 5120, nseg 5: `ELEM_SEG`), so the pipelined P145 period law
  carries over. Pipelining is S81-CALPIPE's calendar work, not duplicated here.
