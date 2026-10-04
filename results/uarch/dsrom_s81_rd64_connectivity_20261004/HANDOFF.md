# S81 strict-pruned RD64 source milestone

Owner scope: source connectivity only. Nash owns finite capture/admission before GO. This milestone retains active unilateral latency/fault stages; it does not implement the 4706-node active-only rewire.

## Integration sources

`tools/dsrom_s81_rd64_connectivity.py` emits unchanged legacy RD64 nodes (RD=64, RST=1, BYPASS=1) and unchanged roots (D=128, QD=128). `source_geometry_r2/return.sv` is module `ot_v41_return_rd64_pruned`; `sources.f` lists its dependencies. Generator writes the model before emitting RTL. Original return RTL is byte-identical to base55e2f0c09. This wrapper is opt-in by instantiation; existing field source remains untouched.

Connect actual pair output side m to leaf `2*physical_pair+m`; preserve tag `{position3,row16,lo5,k3,nseg5}`, data and error bit exactly. Metadata `active_leaves[]` maps physical pair/side to old padded seat/leaf. `nodes[]` gives exact child IDs, old source level/index/fault site and generated instance; `roots[]` maps input and unchanged VM port. Absent children have valid=0. Every retained node/root fault is ORed; enclosing field must also OR every actual pair fault. No READY and no producer credit exist.

Actual consumer chain remains `rtl/test/v41_runtime/w17_current_fastpp_c8_s82_rt.cpp` Field::propagate -> `rom_fr` (69 bits/root) -> `rtl/w17_runtime/hdc/v41x/ckvsel/ot_hdc_core_v41x.sv` g_rom -> `rtl/w17_runtime/v41die/ot_v41_spine.sv` row loop -> registered rom_we -> `rtl/w17_runtime/chip/ot_chip_v41x_tile.sv` VM write at following positive edge. These paths are in Arch's `/home/ubuntu/dsrom-system-rtl-20261003` worktree. Every r_v is accepted without return backpressure. The old S82 return_pair helper hardcodes2388 and is not the S81 mapping.

## Exact source/inventory difference

S81 geometry is NP2417/BF519/R128. Strict pruning retains4834 leaf inputs,5090 nodes (384 unilateral),128 roots; reference4096 seats contained8192 leaf inputs and8064 nodes. Exactly3358 inactive leaf inputs and2974 wholly inactive nodes disappear; no root disappears and no storage credit is taken for an empty side of a retained node.

Node declaration credit is8386bits (=2*64*65+66), so removed storage24939964bits; retained44831044bits. Existing FF50 reservation prices the removed declarations18.90848310624mm2 and retained storage33.98910431904mm2. These are source/model counts, not synthesis measurements. Golden norm/sibling/parent arithmetic and tags stay inside unchanged modules. Strict source matching assumes identical pre-edge active inputs/reset and valid=0 for old inactive leaves.

The owner7384706-node active-only screen omitted384 additional active unilateral stages. Retaining them adds3220224bits/2.44144502784mm2 to that screen. This debit must be composed by Arendt/Maxwell; it is not credited as inactive storage removal. No clock, rate, whole-token or loaded-fault qualification follows from these counts.

## Canonical binding pending

`source_geometry_r1` is the initial geometry record. `source_geometry_r2` adds explicit source/leaf/root integration hooks and generator hash. Both say inventory_bound=false: region bounds use floor(r*2417/128), and BF site identities/rank_die inventory are deliberately null. Arendt's canonical output was still generating (only matrix_map.jsonl.gz observed); no partial payload was consumed and no allocator was rerun.

When Arendt freezes inventory.json and stage_map.json, use the same generator with `--inventory PATH --stage-map PATH --matrix-map PATH --out NEW_OUTPUT`. It validates S81 inventory,519 unique BF site IDs, and exact region bounds, carries BF/rank_die identities and hashes the input files. The optional canonical map pin establishes file identity, not payload/numerical qualification. Do not label the current geometry emission a released-checkpoint-bound map.

## Actual evidence

`actual_connectivity_r1/result.json` and raw logs retain the already completed admitted AGIdock128 comparison: 5active pairs/2roots versus 8padded pairs/2roots,64rows, cycle289 functional completion,801 total cycles,448 identical asserted-fault cycles. Every valid output's row/position/FP32/BF16/error and every cycle's root-valid/fault matched, including deliberate overflow. This is a new wiring fixture using unchanged real legacy modules, not full S81 arithmetic/system qualification. Source manifest matches the stored fixtures. No procedural replay or physical sweep was launched to finish this milestone.
