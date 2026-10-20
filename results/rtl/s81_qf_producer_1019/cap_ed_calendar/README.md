# TOK.DS.BENCH.1 calendar fix: E-column static delay (CAP-ED, D = 23)

Fault (757a340ff, unit 627409; FIRST_TREE_FAULT.md): the CAP root carries one word per edge, the six QF frames' rows never
merge, and the shared XS stream gives all frames the same segment dates. 9 pairs: 37 exit edges vs >= 44 real partials.

## Exact search (root_pack.py, complete DFS, no word cap; pools = c5ce8ddf1 finite_pair_gap_negatives/gap*_complete_generated_pool.json.gz)

| calendar | 6 frames, one root lane | 3 frames per column | 6 frames, E column +D |
|---|---|---|---|
| 12 pairs, gap 0 | NONE (469 nodes) | FOUND 22 words 1773..1802 | NONE D=1..22, FOUND D=23 (46 words 1773..1828), D=24..26 FOUND |
| gap 8 / 16 | NONE | NONE | - |
| gap 24 / 32 | NONE | FOUND (32 / 38 words) | - |

Shared-stream gaps add partials and do not open slots; widening the pool to 12 pairs alone is not enough. The column split is.

## Decision (LEAD2-S81/TOK)

RTL `ot_s81sl_cap_ed` (new leaf) delays the E tree's output word by exactly D = 23 edges before n6 (`ot_s81sl_cap #(.EDLY(23))`;
EDLY = 0 keeps the old netlist). n6 then receives W and E words on disjoint edges. Compiler: each frame picks one placement from its
12 physical Q pairs (packD_23.json `solution`: frame index 0..5 = L01, L02, L03, R01, R02, R03; `assign[pair_index]` = (super row,
seg, nseg)), stream unchanged (gap 0), and the global check is: union of all frames' exit edges (E frames +23) has no repeats.

Price: +23 edges on every E-column return word (latency only, once per epoch tail; epoch period 600 unchanged, no added stream
beats). Last frame exit 1804 -> 1828 (+24 edges on the epoch's last return). Schedule/token pricer owed (LEAD2-S81 INBOX).

## Bench (Verilator 5.050, ot-epyc4 unit oth-ubuntu-1281695-1792453432)

base DM=DX=23: `TB_CAP_ED PASS checks 204`; mutants DM=22 / DM=24: FAIL (290 / 291 errors) -- bench/*.run.log are the witnesses.
Lint of ot_s81sl_cap with EDLY 0 and 23: 0 errors (bench/lint_e*.log).

## SAFE checklist (ot_s81sl_cap_ed)

1 pins: input/output registers = the delay line's own pin regs; reset lands through ot_rst_relay (2 sync + 1 tree) -- PASS.
2 reach: a leaf beside u_rt's E face, no long single-cycle wire -- PASS (placement to be confirmed at gate).
3 fanout: <= 21 rows on the write enable decode; no high-fanout register -- PASS.
4 depth: 21:1 read mux, one stage -- PASS. 5 storage: 66 x 21 = 1,386 bits < 2 kb, register-file ring (no flop->flop hold chain) -- PASS.
6 floorplan / 7 clock: gate owed (new leaf; io_hold_margin 0.03, reset_landing 2). 8 schedule: static, D owned by the compiler -- PASS.

## Next (not done here)

1. Compiler: retained_xs_program.py `qa = q[:12]` with the packD_23 per-frame placements; serializer adaptation for 12 pair slots;
   regenerate the 15-epoch images. 2. Vehicle TB `ot_s81sl_cap #(.EDLY(23))` + the new leaf in source_files.f; rebuild fullsix
   (frontend ~930 s, build ~110 s) and rerun the coupled diagnostic (expect no F1 at child/n6; then CAP target3 programme / FIN).
3. Die: gate the new leaf (s81sl_cap_ed) and re-gate the cap parent.

## TOK2 correction (10-19 ~19:30): EDLY 23 alone does NOT close -- W lane 3 +16 with E +24
The CAP-ED23 fullsix rerun (ot-epyc4 tok2-capd/fullsix_capd23, unit oth-ubuntu-3860260) removed the n6 F1 but kept the W-tree
fault 0002 at 1801: the W tree carries FOUR frames (lanes 0..3 = L01 L02 L03 R01; R01 is W lane 3, FIRST_TREE_FAULT.md), and the
original packing assumed W = L frames, E = R frames. Exact repacking with the real columns and no twin symmetry
(root_pack_nosym.py): E-only delay NONE for D 0/23/24/30 (wD_23.json); lane-3 shift a x E shift b grid: FOUND first at a = 16,
b = 24 (s_16_24.json, 44 words 1773..1820). RTL: new leaf ot_s81sl_cap_ld (one 70-b lane, ot_hdc_delay_rf 70 x 14 = 980 b,
primed valid) on W lane 3 + ot_s81sl_cap_ed D 24: ot_s81sl_cap #(.EDLY(24), .WL3DLY(16)). Cost: +16 edges on R01 words, +24 on
R02/R03 words (latency only, 0 macros, ~2.6 kb RF total) vs the Codex pre-tree SRAM rings (5 macros, 327,680 b, +856 FF, up to
+320 edges, parent reset fanout 54 FAIL). Benches 5.050 (bench_l16e24/): ld D16 PASS 191 checks, D15/D17 FAIL; ed D24 PASS 204,
D23/D25 FAIL. Compiler: retained_xs_program.py --placements s_16_24.json --shifts '{"R01":16,"R02":24,"R03":24,...}'.
