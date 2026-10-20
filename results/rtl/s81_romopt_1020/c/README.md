# S81-ROMOPT-C 10-20: O3, k segment classes per element (ROM contents + compiler only)

Owner 10-20 ~08:45: O3 = multi-slot segment classes per element (k2, then k3), contents + compiler only, proven
conflict-free by the static checker incl. the MU calendar; STOP if it needs any physical / RTL change.
Branch claude/s81-romopt-c-1020 (from claude/s81-romopt-1020 @7f845e6e0). Flag `OT_XS_KSLOT=k` (default 1 = every
record byte-identical, proven below); ops `OT_XS_KSLOT_OPS` (default `ffn.experts_gu,ffn.down`). All runs use the
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
`xs_kslot_check die` (`compile/kchk_k2_s0`): E1-E5, F1-F3, frame RET bus (156 gu / 219 down words a layer on distinct
edges), layer RET disjointness and MU RET (users mod period): PASS on all four layers, 0 collisions AR and MTP.
Negative controls (all FAULT as required): `xs_kslot_check selftest` 9/9 (same-edge / 1-edge classes, k + 1 slots,
repeated class, tree fault, RET-bus collision, MU RET collision; disjoint control passes), xs_field_calendar selftest
23/23 (default and k2) (`compile/selftest`); die L0 (`compile/kchk_k2_neg_*`): gu P144 and down P126 -> compile fault
`period_ge_measured_floor`; injected layer RET overlap -> `LAYER_RET_bus_ops_overlap` (gu / down); injected MU shift
(user 1 = user 0) -> `MU_RET_bus_collision` + `MU_field_windows` (7 collisions).

## 5. Token (tools/toksim_s81_compose.py via `compose_c.py`, on the O1+O2 release compile = RATE3 prop2_s0)

Only experts_gu and down change (their k2 spans + the unchanged CAP adders); every other op is asserted equal to k1.

| scenario | AR tok/s | MTP tok/s | MU aggregate AR / MTP |
|---|---:|---:|---:|
| O1+O2 (RATE3 prop compiled) | 953.2 | 2,967.9 | 43,846 / 29,679 |
| O1+O2 + F8 window_load (RATE3 headline, contents-only) | 966.2 | 2,998.2 | 44,447 / 29,982 |
| **O1+O2+O3(k2)** | **1,011.5** | **3,119.4** | 46,529 / 31,194 |
| **O1+O2+O3(k2) + F8** | **1,026.2** | **3,152.9** | 47,206 / 31,529 |

## 6. k3 (in progress at this commit; see the lane log / next commit)

k3 = 14 rows a phase (gu 6 phases, down 7). The legalisation is a search problem (no fixed formula): found fault-free
layouts for gu col_h9 nsr5, col_h10 nsr5 and col_h10 nsr6; gu col_h9 nsr6 and every down shape (their five classes sit
at beats 56/57/59/60/62, so classes 0/1 and 2/3 cannot share an element) were still at 1-9 tree faults after 10 rounds of
16-32 annealing workers. Under way: longer searches, and the stretched-stream variant (`OT_XS_KSLOT_STRETCH`: down
rounds 8 -> 10 beats, gu 10 -> 15, contents only, costs stream beats in P_k3).
