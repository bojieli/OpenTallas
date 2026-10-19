# SYSFACE semantic depth and publication model

**MODEL ONLY. Smallest concrete source step: an opt-in, age-neutral balanced context RX fault/predicate implementation, followed by exact same-edge publication ownership.** No RTL, source helper, macro view, source calendar or implementation job changes occur here. The measured bc2l failure in a0ab17388 remains unchanged: TT −57.924 ps, 833.5 ps / 28 native levels, one 39-load OR root, 29,314 unbound native PG terminals and 96 nm local macro contacts. No timing delta is inferred from Boolean depth or added registers.

## Actual semantic cone

The frozen generated source d8b39bd8 and cold original Yosys graph from **ff05d759bd0370d41fa671b755233e91670f7fe0** identify `core/f2940` as `u_record.u_context.fault`, an asynchronously cleared sticky error bit in `qfd_host_native_context_rx`. Its original D/Q are bits 5300/5301. Boundary100193 is `rx_payload[142]`; that bit belongs to the **reserved-zero field [511:142]**, not a decoded payload/result bit. Exact path and source attributes are in `cone_path.json`.

The 27 generic gates are nine reserved-field OR levels, an inversion, five serial structure conjunctions, an inversion, five bad-receive ORs (including sticky fault), and six fault priority OR/mux levels. Native mapping reports 28 levels / 833.5 ps. The original source is preserved in `input/`; every actual native sink of the failing OR is retained in `publication_partition.json`.

The cold manifest explicitly states `production_origin_bound:false`, MU/OVL/SRAM_CAL/CTX_ACCEPTED/COLD_PREFIX=1, AW12, offsets2000/20000. These diagnostic offsets and the old generic control-safe packet do **not** establish correspondence to the real command profile referenced by77fc3afbc. Bind the actual production producer/calendar and first uses before integration. The old ff05 source, daemon85fcc1f9 plus six overlays, and current-main helpers remain separate identities.

## Candidate A: same-edge source semantics

For context `fault`, the actual source is a monotonic sticky OR of six causes: prior fault; BEGIN while active; rx_v/slot mismatch; receiving an invalid record; changed retained image while active; and a bad head context in stages1..36. Remove the redundant prior-fault operand from the receive-only bad condition, because prior fault is already the sticky outer term. Flatten the nine structure-invalid predicates, four image-invalid predicates, and three rx_v/native_active/BEGIN predicates into one balanced sixteen-input bad-receive tree. Balance the final six causes. Leave acceptance/epoch invalidation priority, every state reset and every public edge intact.

This has **zero new state, clock/reset loads or schedule edges**. The specified joins require fifteen two-input ORs for bad-receive, one slot AND and five two-input ORs for final fault, excluding existing predicate generation and other cause gates. The reserved-bit path model is nine reduction levels + four receive-tree levels + one slot gate + three outer levels = **17 abstract levels**. Other comparator/frontier paths still require modeling. These are exact operations for the proposed expression, not the post-optimization area delta or native depth. The 73,728 finite checks exhaust the thirteen source-level Boolean guards and sixteen-predicate regrouping. Four-state simulation equivalence, all output priorities, native timing and final source/clock/fanout remain unproved.

Separately, model **one new actual OR publication** of `n13474 | n5301` to split the existing39 native sinks20/19. Preserve the already present g11452 publication and its one actual load. Proposed partitions are explicit actual endpoint lists, with sticky-path g5330 retained in partition0. Upstream native loads become g11450:2→3 and fault FF:5→6; zero state/clock/reset/cycle changes. A same-sized OR2x6 master has actual placed area0.17496 um², so that is the conditional bare-cell reservation; the implementation's actual delta is unknown. New publication adds two PG terminals and requires actual binding. Equation duplication alone is not ownership or fanout proof. Changed balanced predicates can change the entire mapped partition, so final native census remains mandatory.

## Candidate B: fully priced conditional pipeline fallback

Retiming only `structure_ok` or just rx_record while leaving image/calendar/head controls live compares different transactions. A conservative one-edge fallback captures **all677 actual context RX input bits** each cycle: record548; slot/rx_v/BEGIN/ready/cap5; program epoch16/digest64; head valid1/stage6/token18/position18; native_active1. A single private context stream is retained; this is not four-user storage.

All145 receiver state-bit transitions must then use the delayed inputs. Ten kept valid publications, each controlling at most15 state transitions (reserve two native selector-pin loads per mux bit, at most30), suppress the initial bubble after reset. Exact added logical state is **687 FF / 687 clock pins**, including ten asynchronously reset valid copies and677 unreset payload bits. The modeled outer update guard contains145 bit muxes before optimization. Native x1 Liberty reservations are **201.204 um² bare FF** and **326.025262 fF clock input capacitance**; access-only clock charging at0.7 V is159.752378 fJ per cycle. Clock wires/CTS, polarity inverters, set ties, muxes, reset leaves, PG contacts and leakage are additional unknown costs. Two-PG-pin FF inventory adds1374 native PG terminals. No memory is needed for this single-stage677-bit snapshot; deeper queues must follow the storage rule.

| Obligation | Existing source ownership | Fallback change / prerequisite |
|---|---|---|
| Producer | Public rx_payload and record-port context_slot/rx_v | Capture the same source edge; actual producer/calendar binding still absent |
| Consumers | host_accept_v, host_epoch_valid/tag/gen/image and sticky fault | All context-visible effects move exactly one edge; downstream scheduling must change |
| Source ages | Record plus program/image/head/native activity on one source edge | All677 input bits delayed together; no mixed-age image comparison |
| BEGIN / epoch | record-port auth RX creates begin_v; context revokes epoch on BEGIN | Context invalidation moves one edge, while auth/commit join elsewhere does not automatically move |
| Reset | Actual context rst_rn[4], generated n14789; original reset priority | Payload remains unreset; valid copies reset from a qualified leaf; native phase/extra leaf fanout unproved |
| Valid | Context slot/rx_v equality, accepted pulse, host valid and sticky fault | First post-reset bubble must hold receiver state; exact ten-copy ownership checked after mapping |
| Fields | Full record, immutable program tuple, head tuple and activity | No header/identity field omitted; 677-bit inventory is in model.json |
| First use | Execution admission, INIT/head contexts and epoch visibility | Consumer calendar must wait one edge and forbid intervening stale-epoch use |
| Token cost | No production source calendar bound | Local +1 edge is exact; composed SU/MU/token delta is NULL |

No local pipeline is eligible until the BEGIN/admission interaction is explicitly bound: delaying revocation/fault could otherwise let execution consume an old host context. Snapshotting inputs establishes a possible retimed stream, not safe mixed-age integration.

## Deliberate band geometry correction

The exact nine R0 macro origins remain on43.2 um lattice: SRAM row y43.2 and ROM row y86.4. `macro_geometry.json` contains every translated native LEF OBS and pin rectangle; no master interchange or contact movement occurs. The actual spec halo is **5.4 um**, so an uninterrupted lower band can extend only **y2.16..37.8**, height35.64. The earlier illustrative y41.04 top crosses that halo. OBS boxes lie above the corrected band; local access, rails, rows and routing still need implementation proof.

Using final-GRT soft area reference7266 um² (16731 design−9465 macros), independently from placement's7091.1 um²:

| Outline | Usable lower band area | Reference occupancy | Outline change |
|---|---:|---:|---:|
|302.4×172.8 |10623.5712 um² |68.40% |0 |
|324×172.8 |11393.3952 um² |63.77% |+3732.48 um² /7.14% |
|345.6×172.8 |12163.2192 um² |59.74% |+7464.96 um² /14.29% |

Width345.6 is the only listed lattice-sized option near the55–60% band target for the current logic, before actual source changes. The687-FF fallback alone raises that reservation to61.39%, before mux/CTS. No physical grant follows. Moving logic into the band invalidates the current333.538 um measured reach. For width345.6, the full outline Manhattan diameter is518.4 um and arbitrary opposite boundary-to-band corners can be514.08 um, so scalar outline sizing cannot establish405 um. Require actual pin/consumer grouping, registered boundary placement, and relays where needed. A center-fed band root has a geometric far-corner distance325.62 um; no clock insertion/spread or neighboring-clock proof is inferred.

Native local contact pitch96 nm (10.417/um), macro OBS/PG continuity, all29,314 unbound PG terminals, TT setup and current production binding remain HOLD for every option. No new memory timing/minCQ or phase is inherited. Smallest concrete next source step is Candidate A in the parameterized context receiver, default off, with the real source/calendar contract and exact all-output causal bench prepared before a new implementation. Candidate B and physical outline selection stay conditional until that interface closes.

Run `python3 model.py` for finite extraction/checks only. Inputs, model, partitions and geometry are hashed in `SHA256SUMS`. No simulator, synthesis or OpenROAD was invoked.
