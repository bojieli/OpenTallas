# S81-ROMOPT-C 10-20: O3, k segment classes per element (ROM contents + compiler only)

Owner 10-20 ~08:45: O3 = multi-slot segment classes per element (k2, then k3), contents + compiler only, proven
conflict-free by the static checker incl. the MU calendar; STOP if it needs any physical / RTL change.
Branch claude/s81-romopt-c-1020 (from claude/s81-romopt-1020 @7f845e6e0). Flag `OT_XS_KSLOT=k` (default 1 = every
record byte-identical, proven below); ops `OT_XS_KSLOT_OPS` (default `ffn.experts_gu,ffn.down`; per-op k as
`op:k`). All runs use the
release flags explicitly: QPAIRS=12, GU_MERGE=1, CAL_SEGMENT=1, TOPO=1, PROP=1. No RTL, view or tile change.

## 1. What "k classes per element" means on the release element (and what it cannot mean)

The q element (`ot_v41_rom_elem_w10`, bound `ot_v41_rom_elem_q_qxpq_w10`, MTP 1, EARLY 1, NB 2) holds up to NSEG 8
segments in up to 8 classes a phase (cfg7 25 words a phase, unchanged), NCH 16 chain words a round, one segment-tree
adder (QD 8). The image writer (`v41_die_images_w17w10.add_phase`) already writes several segments per pair. Only the
legaliser (`frame_return_plan`, D2: one slot per element) and `xs_place` (R = 2 x pairs / nseg) limited k to 1.

Measured cadence (PV trace: the RELEASE FSEQ tb + `-DTB_PVTRACE`, same 79 source files as the release exes,
`pv/build/`; Verilator 5.050; u_f_0L00 col_h9_l4_nx LK5 + u_f_3L01 col_h10_l4 LK2; k2 + k3; gu + down):

- **k segments of ONE class (k rows, one segment index) are NOT legalisable.** They leave the element 1 edge apart on
  both macros (gu +1/+2, down +0/+1/+2, shared fp8 +0/+2/+4: `pv/sameclass_k*/*/pvfit_sameclass.txt`). Each element's
  leaf node joins its own r0 (input a) and r1 (input b, one edge later) and exits one word an edge, so slot j+1 of r0
  and slot j of r1 collide (F1) in every element (`scripts/dbg1.py` output in the lane log). This is a property of the
  frame return tree, not of placement.
- **k DISTINCT classes per element work.** Every class whose single-slot edge E(pair, seg) = e0 + last_beat(class) +
  off(pair) + seg_extra(seg) is >= 2 edges from the element's other classes emits EXACTLY at E(pair, seg):
  **2,681 / 2,681 pv words, 0 mismatches** (`pv/k2|k3/*/*/pvfit3.txt`). Closer class pairs shift (+1, fp8 adder
  interleave) and are refused. So the multi-class cadence term is 0 (`xs_place.ELEM_SLOT`) under rule E3.

## 2. Compiler (all opt-in; tools/s81_dv)

- `frame_return_plan.py`: `leaves_for(kslot)` (k distinct classes per element; E2 one pv word per macro per edge; E3
  classes >= 2 edges apart -> `PortConflict`), `legalise_k` (annealed swaps of slots between pairs / whole pairs;
  `OT_XS_KSLOT_ITERS/SEEDS/W/T0`), `plan_phase(kslot, nsr, slot_extra, stretch)`, legalised-layout cache
  (`kslot_layouts.json`, re-composed per phase, fallback search), unlegalised conflicts reported as compile faults.
- `layer_prog/xs_place.py`: `OT_XS_KSLOT`, `nsr_max` = floor(k x 12 / nseg) super rows (k2: 8 rows, k3: 14 rows a phase),
  all 12 q pairs, measured `ELEM_SLOT`, optional per-op stream stretch `OT_XS_KSLOT_STRETCH='op:f'` (k3 only, below).
- `layer_prog/xs_field_calendar.py`: `FLOORS_K[(op, k)]` measured floors / tails; a k-class op without one = compile
  fault. `tools/v41_die_images_w17w10.py`: `field.stretch` (unset = unchanged).
- `layer_prog/xs_kslot_check.py`: the static checker (E1-E5 element / ROM / cfg7, F1-F3 tree, frame RET bus per op
  across pipelined phases, layer RET disjointness, MU RET + field windows); `layer_prog/kslot_search.py`: parallel
  layout search per shape (the calendar is value-independent, so one layout serves every phase of a shape).
- k = 1 regression (`scripts/regress1.py`, ep9): with OT_XS_KSLOT unset the compile reproduces the RATE3 release
  records **byte-for-byte** (frame.json, every plan and every ROM image sha256 of u_f_3L01 gu / down and u_f_0L00 down,
  60 phases): PASS.

## 3. k2: RTL benches on the release frame exes (bit-exact + cycle-exact, Verilator 5.050)

Vehicle: TOKSIM-S81C/FSEQ `tb_toksim_fgu_seq` +RETIRE on the release 19bf4121e frame exes (v_h9nx_e5 / v_h9MX_e1 /
v_h10_e2, binary sha256 in each `summary.json`), the compiled k2 phases of `compile_frame` (`scripts/fseqk.py`), every
RET word assigned by calendar and checked per phase (golden segment-tree values bit-exact, coverage, fixture BF16 tie of
every row, cycle-exact calendar). Period sweep 120..160; mutants on the first and last (tail) phase: swap (two
elements' ROM images) and shift (calendar +1) must FAIL; fail witnesses committed (`fseq/k2/*/*/mut_*`, `run_P*`).

| op (k2) | phases (k1) | frame (slice frames) | rows | P_k floor | P_k - 1 | span at P_k (k1) | mutants |
|---|---|---|---:|---|---|---:|---|
| ffn.experts_gu | **12** (18) | u_f_0L00 (8) | 54 | **145 PASS** | 144 FAIL | 1939 | swap / shift FAIL |
| | | u_f_2L02 (7) | 60 | 145 PASS | 144 FAIL | 1938 | FAIL |
| | | u_f_3L01 (6) | 72 | 145 PASS | 144 FAIL | **1943** (2811) | FAIL |
| ffn.down | **14** (21) | u_f_0L00 (8) | 77 | **127 PASS** | 126 FAIL | 1948 | swap / shift FAIL |
| | | u_f_2L02 (7) | 77 | 127 PASS | 126 FAIL | 1944 | FAIL |
| | | u_f_3L01 (6) | 77 | 127 PASS | 126 FAIL | **1949** (2896) | FAIL |

Every period >= P_k PASSes and every period < P_k FAILs (monotone). Legaliser faults 0 on all three frames.

## 4. k2: die compile, static and MU checks (L0 / L2 / L14 / L20, slices u_s_0S and u_s_3S)

`xs_field_calendar die` (`compile/dcal_k2_s0|s3`): every op static PASS; experts_gu 12 x P145 = 1943, down 14 x P127 =
1949; all other ops unchanged (wq_b 11/1567, wo_b 4/701, shared_gu 3/652, wo_a 12/2893, router 5/1269); layer calendar
rows 1865 (L0) / 2003 (L2, L14, L20) <= 4096; MU 46 AR / 10+1 MTP (cal1): 0 collisions.
`xs_kslot_check die` (`compile/kchk_k2_s0|s3`): E1-E5, F1-F3, frame RET bus (156 gu / 219 down words a layer on distinct
edges), layer RET disjointness and MU RET (users mod period): PASS on all four layers, 0 collisions AR and MTP.
Negative controls (all FAULT as required): `xs_kslot_check selftest` 9/9 (same-edge / 1-edge classes, k + 1 slots,
repeated class, tree fault, RET-bus collision, MU RET collision; disjoint control passes), xs_field_calendar selftest
23/23 (default and k2) (`compile/selftest`); die L0 (`compile/kchk_k2_neg_*`): gu P144 and down P126 -> compile fault
`period_ge_measured_floor`; injected layer RET overlap -> `LAYER_RET_bus_ops_overlap` (gu / down); injected MU shift
(user 1 = user 0) -> `MU_RET_bus_collision` + `MU_field_windows` (7 collisions).

## 5. k3

k3 = up to 14 rows a phase: experts_gu 6 phases (one per expert), down 7. Legalising a k3 phase is a search (no closed
form): `kslot_search.py` (parallel annealing, 16-40 workers, restarts from the best layout) writes one fault-free layout
per shape to `tools/s81_dv/layer_prog/kslot_layouts.json`; the calendar is value-independent, so the compiler re-composes
that layout for every phase of the shape (0 faults asserted) and falls back to its own search otherwise. A shape is
(master, fmt, K, nseg, super rows, k, ROW COUNT, stream stretch): an odd row count leaves an idle half and changes
the calendar. Search logs: `search/`.

- **ffn.down needs a stream stretch.** Its five classes sit at beats 56/57/59/60/62 (5 units in 8-beat rounds), so
  classes 0/1 and 2/3 can never share an element (E3) and no plain k3 down layout was found (best 1-9 faults, 10-12
  rounds). `OT_XS_KSLOT_STRETCH=ffn.down:2` (xs stream rounds 8 -> 10 beats; contents only) spaces them 2 apart: all 8
  down shapes (col_h9 / col_h10, fp4 routed / fp8 shared, 10 / 11 rows) legalise.
- **experts_gu plain k3** legalises for 9, 10 and 11 rows on both masters (8- and 7-frame slices). **12 rows (the
  6-frame slices u_s_3S / u_s_4S: 72 rows / 6 frames) did NOT legalise**: best 5 tree faults with 32 root words after
  4 jobs x 40 workers x 12 rounds x 100k moves (col_h9 and col_h10), and 1-4 faults with stretched streams. The frame
  root exits one word an edge; a 12-row phase's 60 leaf words reach the root inside ~31 edges (class beats 8 + x
  station offsets 16 + paths ~7), so >= 28 sibling merges inside +-2-edge windows are needed; none found. A stretched gu
  stream also moves the element emission (-4 edges measured on st1.5: `fseq/k3_gst15`, `k3_gst2` FAIL at every period,
  values exact), so stretched gu would need its own PV measurement, layouts and floor: not pursued here.

RTL benches (same vehicle and checks as k2; `fseq/k3`, `fseq/k3_st2`, `fseq/k3_st2f`):

| op (k3) | phases | frame | rows | P_k floor | P_k - 1 | span at P_k | mutants |
|---|---|---|---:|---|---|---:|---|
| ffn.experts_gu (plain) | **6** | u_f_0L00 (8) | 54 | **145 PASS** | 144 FAIL | **1071** | swap / shift FAIL |
| | | u_f_2L02 (7) | 60 | 145 PASS | 144 FAIL | 1069 | FAIL |
| | | u_f_3L01 (6) | 72 | not legalised (12 rows) | | | |
| ffn.down (stretch 2) | **7** | u_f_0L00 (8) | 77 | **135 PASS** | 134 FAIL | 1125 | swap / shift FAIL |
| | | u_f_2L02 (7) | 77 | 135 PASS | 134 FAIL | 1121 | FAIL |
| | | u_f_3L01 (6) | 77 | 135 PASS | 134 FAIL (131-134 all FAIL) | **1125** | FAIL |

Die compile + static / MU checks (`compile/dcal_*`, `compile/kchk_*`, L0 / L2 / L14 / L20, all PASS, MU 46 AR / 10+1
MTP 0 collisions, layer rows 1929 / 2067):
- **mix = experts_gu k2 + down k3 (stretch 2)** (`OT_XS_KSLOT_OPS=ffn.experts_gu:2,ffn.down:3`): every shape of the die
  legalises; slices u_s_0S AND u_s_3S compiled and checked: gu 12 x 145 = 1943, down 7 x 135 = 1125.
- **full k3** (gu k3 too): slice u_s_0S (8-frame) compiled and checked: gu 6 x 145 = 1071, down 1125. The 6-frame slices
  cannot be compiled (12-row gu), so full k3 is a die-wide PROJECTION, not a release compile.

## 6. Token (tools/toksim_s81_compose.py via `compose_c.py`, on the O1+O2 release compile = RATE3 prop2_s0)

Only experts_gu and down change (their compiled spans + the unchanged CAP adders); every other op is asserted equal to
k = 1. Inputs: `compile/cal/*/die_field_calendar.json`; outputs `compose/` (case records gzipped).

| scenario | AR tok/s | MTP tok/s | MU aggregate AR / MTP | status |
|---|---:|---:|---:|---|
| O1+O2 (RATE3 prop compiled) | 953.2 | 2,967.9 | 43,846 / 29,679 | compiled |
| O1+O2 + F8 window_load (RATE3 headline, contents-only) | 966.2 | 2,998.2 | 44,447 / 29,982 | compiled |
| **O1+O2+O3(k2)** | **1,011.5** | **3,119.4** | 46,529 / 31,194 | compiled die-wide, benched |
| O1+O2+O3(k2) + F8 | 1,026.2 | 3,152.9 | 47,206 / 31,529 | |
| **O1+O2+O3(gu k2 + down k3)** | **1,040.4** | **3,193.4** | | compiled die-wide (s0 + s3), benched |
| O1+O2+O3(gu k2 + down k3) + F8 | 1,056.0 | 3,228.5 | | |
| O1+O2+O3(k3) | 1,072.8 | 3,275.6 | | PROJECTION: gu k3 not legal on 6-frame slices |
| O1+O2+O3(k3) + F8 | 1,089.4 | 3,312.6 | | PROJECTION |

## 7. Not covered / open
- The benches are single-position (np 0), as every release calendar bench; MTP positions reuse the same chain slots per
  position (<= 6 words a round, <= 3 segment trees per parity bank: inside NCH 16 / NSEG 8), not run in RTL here.
- BF ops' RET words are not in the RET-bus check (k = 1, unchanged; their calendars are the WQBP / FSEQ ones).
- gu k3 on 12-row phases: a wider-window option (stretched gu stream, with its own PV cadence + floor) or a gu
  ownership change that leaves <= 11 rows a frame; neither is contents-trivial in this lane.
