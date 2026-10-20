# HOST6 ORDER retained-copy source packet

The release needs an SRAM successor to the historical closed
`qkd_hr_core_order-r4-d9e4f6a44`. At that exact source revision,
`qkd_host_ingest_map` contains `reg[293:0]q[0:7]` (2352 bits), and
`qkd_host_boot_dispatch_debt` contains `reg[289:0]q[0:7]` (2320 bits).
Both are runtime-indexed flop FIFOs above the binding 2 kb storage threshold.
Historical CLOSED status does not establish compliance with that later rule.

S2 (`3f9ee8d57`) fixes those queues with six real 32x128 SRAMs. Its s2f/g
gates have zero global-route overflow but fail the 80 ps clock spread limit.
More fundamentally, their actual native all-driver census reaches 1184 loads
on an OR2 output. Earlier FF-only standalone counts of 32 do not qualify it.

This packet repairs all primitive drivers using the existing Codex
`kv_grp_safe5.py` fixed-point retained-copy construction. The generator is
copied as `tools/qwen_kv_die/host_order_native32.py`; no shared helper changes
are included. It starts from immutable **pre-placement** S2 mapped source,
preserves every primitive type and pin function, resolves BUF/INV polarity,
replicates backward to a fixed point, and refuses duplicated SRAMs or
overloaded input ports. Kept primitive wrappers prevent synthesis merging.
The new top `qkd_hr_core_order_n32` is opt-in; no existing top or default changes.

The input source is `original.v.gz`, SHA256 of decompressed bytes
`06317cc8f8ef150c5f6ad9c908672e299815fcc59148721a1e2ce70e59969b7c`.
It was collected from ot-epyc9's source-bound s2f gate, directory
`/srv/opentallas-scratch/claude/ref_gate/qkd_hr_core_order_s2f-20261019-221645/routes/gate/work/orfs/results/asap7/opentallas_qkd_hr_core_order_asap7_ref_gate/base`.
The six calibrated SRAM companion views are imported byte-for-byte from S2.

Measured evidence on the fleet:

- 67,371 original non-buffer primitives become 67,693 primitives: 34
  combinational originals and two FF originals need copies. The two FFs are
  dispatch `hd[0]`/`hd[1]`, each with two copies. All six SRAMs remain singletons.
- Fresh kept-source synthesis in pinned `openroad/orfs:asap7lock`, Yosys
  0.67, produces `resynth.v.gz`, decompressed SHA256
  `7cf885588dc477cfe1cd9796898165ca42564ddcdec4406163d698e8f199c62b`.
- Native census checks 69,134 drivers, including combinational/reset drivers:
  maximum 32, zero violations, 18,231 FFs, six SRAMs. See `native32.json`.
- Native reset proof on that exact re-synthesis: exactly two stages, 12 first
  FFs, 288 final FFs, root 12 loads, first maximum 24, final maximum 30.
  Clock and physical QN polarity are checked by `balanced_reset_proof`.
- Primitive and every input/output pin correspondence PASS for all 67,693
  retained primitive copies; SRAM identity is included. See
  `correspondence_resynth.json`. This is conditional on corresponding state.
- Verilator **5.050** mapped-source lockstep PASS: 12,000 cycles, 11,984
  complete-output comparisons, repeated reset pulses, independently randomized
  initial state, SRAM initialization disabled. Actual candidate-source mutants
  invert hb[0] and chain_f[32]; both fail at cycle 17. Witness logs are committed.
  Combinational models come from pinned ASAP7 RVT TT Liberty; sequential models
  use the committed canonical sequential coupon, including actual QN polarity.

This transformation adds no edge or cycle and leaves SRAM capacity and
interface unchanged. Existing S2 FIFO protocol/capacity/prefetch/RAW proofs
remain the source mechanism evidence; this packet specifically measures the
primitive-copy change. The existing S2 analytical model and schedule remain
the starting budget; a changed physical outline still needs measured admission.

Qualification remains OPEN. The independent copied-state cold-reset SAT proof
is running. Its first attempt correctly refused unknown SRAM cells because
all original outputs were exposed; the second exposes only the copied-state
obligation, with no `opt_merge`, fixed initial state or `ignore_unknown_cells`.
No layout gate, REVIEW, submit, release binding or closure claim is made.

The gate runtime needs an exact source-bound native reset-profile interface:
the source already contains the two reset edges. `reset_landing:true` would
insert two extra edges, while `false` discards the balanced profile needed for
the 12 first-stage loads. There is no flag override or generic skip. ROOT owns
that helper decision and currently holds new gates during daemon drain.

The physical successor must change the failed geometry: all face registers
beside one full-width cell band, balanced face density, and clock beside that
band, or regional hardened children with landed crossings. Actual spread must
be <=80 ps TT/FF. Sink count 18,235 and insertion alone are guidance, not failure.
Two independently named structural kits will be gated only after source proof,
source-bound native profile support, measured reach and checklist qualification.
