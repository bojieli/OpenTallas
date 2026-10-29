The public `ot_hbm_idx_topk_link_static` master now uses the bounded stable
compaction tree inside its unchanged core interface. The registered shell,
eight SRAM banks, 171 ingest slots and 16-beat II8 output calendar are preserved.
Added boot/data cycles: zero. Arithmetic and record order are unchanged.

The pre-build model is `../topk_tree_model.py`. This reuses the tree measured
on 2026-10-26 (130,905 mapped cells, eight SRAMs); the serial implementation has
repeatedly exhausted 40/64 GB or spent >23 hours in EXTRACT_FA. Bounded subtree
shifts replace serial 32-bit-index writes into 4,608 bits. Only seven residual
records persist. The carry payload is masked by reset/clear of fill.

`run_current.sh REPOSITORY FRESH_OUTPUT` compares the current public core
against the original serial core in `serial_reference.sv`: four production
calendar frames, 2,048 records, 256 flits and 1,232 cycle samples; all 20 index
bits are exercised. It also checks halveswap, wrong-tag and dropped-slot mutants,
proves the N=8 stable compaction mechanism symbolically, and checks the sequential
residual-carry mechanism by induction from reset with arbitrary data/masks/clear/ingest.
No current physical kit or timing qualification is implied.

Historical tree kit result (preserved): intel2
`path-hbm-cores/topk_tree/kits_r2/ot_hbm_idx_topk_link_static_36b3f0c7a4d0/lec/lec.json`
is NOT EQUIVALENT: 22,589 proved / 40 differs / 616 undecided. All 40 differing
points depend on removed `u_fcore.u_core.tx[1057]`: lane 1's constant-one sequence
bit, aliased with constant-one tag bits. These output payload bits are not reset
and retain power-up X until the first read. This diagnosis does not waive that
failed kit; regenerated kit LEC must close before any route/signoff claim.

Current-source result 2026-10-28: `results/hbm_topk_1028/receipt.json` and logs.
Full lockstep PASS, mutants caught with 2112/320/2669 errors; carry invariant
inductively proven and dropped-mask control caught; fixed low sequence bits
proved for every rank/gbase/group/lane with wrong-constant control caught.
The nine tag bits are literal 1s; the two low sequence bits equal lane modulo
four. Those fixed fields now use wires; variable data/sequence/rank remain
unreset flops. This removes the source of the historical 40-bit X chain without
resetting datapath, adding cycles or assuming gate outputs constant.
The kit recipe includes the helper dependency. A NEW kit LEC remains required.
