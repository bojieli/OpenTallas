# GRP private hard interface model — HOLD before RTL

The current selected sources support removing genuinely unused interface pins.
The safe change is narrower than deleting all 35 historical aliases: **the EST
alias is live and must remain functional.** This packet changes no RTL, kit,
constraint, schedule, native view or job. It is not permission to build.

## Exact selected evidence

GEN7 source commit `4db0974030714ac3f3745ccadd6c0a234dfeb3c4`; GEN8 diagnostic
source commit `5f2ce19bc57cc98c941aad2362d4c7a855498171`. Both source snapshots
select `rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv`,
SHA256 `df66545140a103b45170c9132cf19e521945c61c8fc649e836df4bb9c49e6e97`.
The committed module snapshots and consumer ledger pin exact bodies and shapes.
GEN7 `port_bind.json` explicitly selects this file and reports unread y__tep /
y__tok for both module types, plus unread o_dn for GRP_H. Exact generated graphs
agree for all 28 GRP and four GRP_H instances, across all four stacks.

GEN7 graph is the actual `port_bind_v2/die_bound.v` on ep5. GEN8 is a snapshot
of `case_kv/die.v` during the live v3 PREP on ep6. **GEN8 final bound/native
consumer proof is pending**; a PREP graph does not qualify a completed bind.
`consumer_ledger.json` records graph SHA256s, every selected group connection,
and all 128 downstream EST consumer instances per graph. `derive.py` reproduces
the ledger from the frozen source and graphs, without EDA or source mutation.
Frozen pickup inputs remain in `/home/ubuntu/artifacts/grp-private-model-1019`.

The initial inspection of `_mu_ba_ds.sv` used the split physical interface and
was rejected as the selected source: its o_pc is 33+95 bits, while the selected
merged interface is 128 bits. Its SHA70b83778 must not be cited as selected.

## Proposed private interface

Keep public modules and pinned historical evidence byte-identical. A future
opt-in private module pair can perform only these source deletions initially:

| Module | Deletion | Exact consumer/source basis |
|---|---|---|
| Both | y__tok[17:0], y__tep[15:0] | Neither output connected at any selected instance |
| Both | x__tok[17:0], x__tep[15:0] | Each occurs only in declaration and deleted alias equation |
| Both | x__est[12:1] | The sole source read is x__est[0:0] |
| GRP_H only | o_dn[270:0] | Unconnected at all four selected H instances |
| GRP_H only | i_ctl[270:194] | Used only in deleted o_dn permutation; all other reads <=193 |

This removes **80 pins per GRP and 428 per GRP_H**, or **3,952 pins** across
28+4 instances. GRP remains 1,697 nonclock/nonreset input bits and 3,047 output
bits; GRP_H remains 1,475 and 2,776. Constants and unconnected replacement pins
are not part of this proposal. Remove only the corresponding named parent
connections; retain their producer nets and every other consumer. Trim EST to
an explicit scalar private input. Trim H i_ctl to 194 useful bits, preserving
the exact low-bit indices and ordering. H o_dn disappears rather than becoming
a tied or ignored hard pin. Generator port schemas, source selector, pin maps,
parent instantiation, bind width checks and model exports must change together.

**Retain y__est__0_1.** Each of 32 instances drives four actual PC consumers,
which feed `u_pc.emb_boot_ready`. It is not an unread legacy output. The module
source makes this a direct combinational path from EST bit0. Deleting or tying
it would alter live boot admission. Registering it at both private faces would
cost at least two FF and +2 core edges, conditional on the actual source clock,
reset and downstream first-use contract. A parent boundary repartition is an
alternative only after exact producer/consumer physical ownership is proved.
Neither timing choice is selected or priced into a release here.

Deletion alone has zero state, MAC, memory-port bandwidth or cycle delta for
both SU and MU, because no retained RHS depends on the removed bits. It removes
3952 physical ABI pins; it is not a 3952-FF saving. No numerical throughput gain,
area saving or token-rate improvement is asserted without synthesis/composition.

## Compose the safe source before physical work

The retired physical kit source `7e6cbb465` used a different `_ds` body, with
local reset landing and extra hop wrappers. The actual selected `_mu_ba` source
has direct rst_n/hrst_n leaf connections and lacks those wrappers. The prior
235/230 unsafe-root census, 140/127 FF-copy lower bounds, 550 comb-copy lower
bounds and four-deep 271/126-bit delay inventory are exact facts about that
retired physical source, **not a census of this selected source**. Reusing its
placed FF counts, fanout limits, area, phase or native evidence is prohibited.

A complete private physical successor must first compose selected source
semantics with the following explicit model obligations. Unknowns remain NULL
in `model.json`; no invented SU/MU calendar or memory same-age guarantee is used.

- Register every remaining live boundary bit at its actual clock/face, retaining
  existing internal registers where they are real boundary endpoints. The raw
  remaining ABI is 4744 bits (GRP) / 4251 (H), not an FF-increment estimate. Each
  source-to-consumer field needs domain, edge, first-use and fault sensitivity.
  Keep payload/control/epoch/valid cohorts together; one edge on only a subset
  cannot be accepted. Registered EST is part of the boot path, not a token mask.
- Two-stage face reset landing must preserve actual async assertion and sampled
  release. No inherited assumed three-edge release from the other `_ds` source.
  Price leaf synchronizers, stopped clocks, warm/POR retention, every replicated
  D/CLK/reset/set load, and useful-copy ancestor fixed point to <=32 through
  buffers/inverters, including inputs, comb, ties and macro roots.
- Retain real boot CDC and storage semantics. The selected source instantiates
  five boot transports; the inspected exact boot component uses a 16x73 FIFO
  per transport. This is actual exceptional boot traffic, not a new normal-token
  credit protocol. Four landing macro banks in the retired kit fail immutable
  full-face contact density (410/409 on41.064um). Do not transplant those views.
  Coordinate truthful macro/pin/access/timing roles with the common S81 SRAM
  owner. Whole-face average is insufficient when local contacts are overpacked;
  PG/OBS/via/access, collision, lifetime, reset and actual read/capture edges
  must pass. Any new >=3-edge delay becomes a real ring/SRAM, not flop chains.
- Derive native synthesis area and stage-depth before choosing an outline at
  40–60% fill, with actual full-face <=6/um access. Raw ABI perimeter alone gives
  square side lower bounds 197.667um /177.125um at six pins/um, excluding reset,
  clocks, PG and distribution constraints. Those bounds do not select a layout.
  Macro origins remain on43.2um. Use a connected full-width standard-cell region,
  real clock mass and regional crossings where needed. Every individual logical
  driver→endpoint wire must be <=405um; summed stage wire is a timing diagnostic.
- Compiler integration must price every actual added edge at SU and MU static
  phases, update boot first-use, requests/responses and per-layer fault STATUS /
  retirement/admission observations. Token deltas remain NULL until composed;
  never hide a missed age through backpressure, masks or later expected outputs.

Checklist: unused pin consumer evidence PASS for exact GEN7; GEN8 PREP evidence
PASS with final bind pending. Registered live pins/reset/fanout/depth/storage/
physical timing/clock/schedule all HOLD. No new placement, route, gate, review,
submission, native receipt, full-token PASS or source adoption follows here.

Next owner: ROOT reviews the deletion scope, then a fresh source-composition
owner derives the actual private boundary/reset/storage microarchitecture and
its SU/MU field calendar before any physical build. Final GEN8 consumer audit
can run when the existing v3 chain emits a bound die; do not duplicate that job.

## Concrete next source scope

1. A fresh source owner may propose two distinct modules, provisionally
   `qkd_kvs_grp_private0` and `qkd_kvs_grp_h_private0`, emitted from the selected
   merged MU+boot-age source. The private0 operation is precisely the deletion
   table above and scalar EST/194-bit H control typing. It must preserve every
   retained equation and leaf parameter/body. Public/default source stays byte
   identical. A structural source comparison, exact original component oracle
   with only the now-unobservable outputs removed, and causal retained-output
   mutants qualify this source step; a gate is not part of it.
2. In `tools/qwen_kv_die/kv_static_die.py`, make the private mapping a separate
   opt-in with default unchanged; update KIND_MASTER/master selection, emitted
   port dictionaries/packing and named parent connection removal together.
   The selected source selector must retain MU and boot-age specialization.
   Recompute `kit_delays` / downstream `programme_to_groups` prices after the
   later registered design, not by inheriting the retired KITS flags. The
   generator's KITS defaults add GRP_LEG/GRP_FT/GRP_LCAL_RLY/GRP_RST behavior;
   treating those as identical selected-source RTL would silently change ages.
3. A second explicit source plan is required for useful live input/output
   registers, true per-face reset, kept <=32 reset/control/data copies, and
   memory/ring replacement. Start with exact source fields `i_ctl[193:0]`
   (boot payload+seal, landing/programme triggers), `i_pc0..3` (actual return
   data/metadata+fault/idle), `kreq/vreq`, `rsp/krsp`, `o_pc0..3`, `o_ctl`,
   GRP-only `i_up/o_dn`, and scalar EST. Record each field's source/consumer
   edge and clock. In particular o_ctl mixes drain/fault/boot observations and
   forwarded upper-group status; partial retiming invalidates retirement.
   Registering a raw packed bus without this ledger is not approved.
4. Deliver source/cycle/copy/storage model back to LEAD-KV/ROOT; only after ROOT
   reviews the complete composed model can synthesis/placement/gate begin.
   No owner needs to wait for an obsolete job: the final GEN8 consumer check
   depends on the already-live v3 chain, while source-only work above is local
   read/analysis plus fleet minimum-component proof when separately authorized.
