# Opt-in ranged native hard-child seam API

`native_seams.validate(...)` dispatches v1 unchanged or new `opentallas.native_hard_child_seam.v2`. v2 feeds the existing face-shell `--face-pass` contract and strict mixed INTERNAL_CORE endpoint census. It does not modify timing, endpoint reach gates or ordinary external-face checks. The request module is the exact selected view module.

Each `contexts` entry is one parent partition type, one hash-bound actual elaborated parent JSON, and the full reciprocal hard-child endpoint family. Use these keys:

```
{
 "schema":"opentallas.native_hard_child_seam.v2", "module":"EXACT_SELECTED_VIEW_MASTER",
 "contexts":[{
  "parent_partition_type":"q_hub_nw",
  "netlist":{"path":"native/selected_parent.json","sha256":"SHA256_OF_DECOMPRESSED_JSON_BYTES","top":"EXACT_ELABORATED_PARENT_MODULE"},
  "endpoints":[{
   "inst":"EXACT_PLAN_AND_NETLIST_CELL", "module":"EXACT_HARD_MASTER", "pins_sha256":"PLAN_PIN_TABLE_HASH",
   "clock_port":"hbm_clk", "reset_port":"hbm_rst_n",
   "buses":{"w_k_addr":[{"own_lsb":0,"width":120,"peer_inst":"EXACT_Q0_CELL","peer_module":"EXACT_Q0_MASTER","peer_port":"w_k_addr","peer_lsb":0}]}
  }]
 }]
}
```

The example is intentionally incomplete and rejects: OUT w_k_addr must declare Q0..Q3 covering480bits; v/rdy16 and wdata4096 similarly. Each Kshare endpoint declares the exact reverse segment. Scalar or vector bit0 uses own_lsb0, width1. Ranges are ascending bit order only, no reordering implied. Every selected bus must be completely and disjointly covered, and every matching selected-view replica in the plan must be present. Same-master peers are resolved only by exact instance, never guessed.

Actual selected parent netlist requirements: Yosys JSON with named hard children retained as blackbox modules, cells named exactly as `plan.partition_types[parent].hard_cores[].inst`, cell type exact hard master, `port_directions` and `connections`, matching abstract module ports. Preserve ALL other cells/connections and top ports; do not extract only requested nets, since external exposure and third loads must be rejected. Netlist path relative to plan directory, `.gz` supported with decompressed-byte hash. HBM owns generating this from the selected real native source/profile and recording that dependency; a synthetic netlist is only a unit fixture.

For every bit the validator checks actual own/peer connection equality, opposite direction, exactly two endpoint uses, no constants/topport/thirdload, exact shared scalar clock and reset connections. Pin identities bind the exact current plan. Context receipt includes the full reciprocal family and parent netlist hashes; strict INTERNAL_CORE validates receipt shape before its normal sequential-endpoint census.

Clock/reset connection equality is not a functional reset-depth or protocol proof. Native protocol proof, reset phase, placement reach and full-clock TT/FF parent STA remain required. Zero added face-wrapper cycles are not a claim of zero native latency. No physical profile, RTL provider, plan or recipe is activated by this API commit. In particular parked half-cycle OUT e13d and actual Kshare blind-face bad10 remain unadopted.

Minimal tests: one32bit producer to four8bit identical-master peers, reverse ready, forward valid; both producer and allfour receiver selections pass. Eighteen negative mutations and two damaged-receipt controls reject. Existing v1 tests pass.
