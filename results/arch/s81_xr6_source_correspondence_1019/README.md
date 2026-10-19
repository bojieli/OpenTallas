# XR6 source correspondence and exact HB1 diagnostic proposal

MODEL AND PROPOSAL ONLY. No RTL, mapped synthesis, simulation, OpenROAD,
floorplan, helper, physical gate, compiler programme or frozen QF input changed.
ROOT has selected the five genuinely independent 1024-bit local holding states
as FF-admissible. They remain full width, with independent lifetime/context and
parallel reads; no artificial SRAM replacement or upper-payload truncation.

## Complete HB0 correspondence

The immutable native input is the XR6 HB0 source `7ef9383db`, SHA
`b10a2c142dbf31e465f382b7f6cd3c6b354cd90be536ae015d159bcfe9f1bee6`,
ODB `078ca172072d4158e7ae2e53b07fad9c2756932f211b79534efe7856794532ba`.
The `dbd7bc06c` model adds **421 FF and 136 combinational cells**, not just
the old 408 FF lower bound. This packet maps all **349 copied original FF**
and **18 copied original combinational gates** to their source state or
classifier boundary. `correspondence.json.gz` includes all **27,637 expanded
terminal assignments**, exact incoming D/RESETN/SETN owners, sequential
ancestor sets, and the complete 63-gate combinational classifier input cone.
No additional input capture FF is required by this HB0 graph construction;
its final raw input maximum remains nine logical pins.

The native census contains the endpoint set of every BUF/INV output. Each
terminal has exactly one nontransparent source owner. Therefore every INV
record containing that terminal belongs to its unique upstream transparent
chain; counting those records modulo two recovers the branch polarity relative
to the source output pin. The checker verifies unique ownership before doing
this calculation. There are no unknown HB-like transparent masters in this
input. This preserves native QN/output and reset pin semantics; it does not
guess polarity from a source variable's spelling. Master functions, input pin
names and these polarities remain explicit in the exported classifier cone.

| Source state | Added FF | Useful consumer boundary |
|---|---:|---|
| `rwe_c` | 165 | Individual `ud[k]` packet-word capture enables |
| `un_c` | 90 | OLD `ud[k]` chunk selection into `sw_d` half-words |
| `pkw_c` | 32 | Packet assembly word captures from `lo_sel` |
| `ev_c` | 30 | ENG triple storage, copy agreement and collector faults |
| Four local reset regions | 28 | Same-age reset of assigned state/input/output groups |
| `rwr_c` | 25 | CTL override of individual output words |
| `eoh` / `poh` | 15 / 5 | ENG kind-major/leaf-major and norm leaf order |
| `pv` | 10 | Partial storage, collection starts and overlap faults |
| `cis_c` | 9 | Individual `ci_r` word selectors |
| `lov_c` | 5 | Input `lo_sel0` word qualification |
| `tg1_c` / `erun` | 3 / 3 | Epsilon/scale captures and ENG active control |
| Second face reset FF | 1 | Additional same-edge landing output, outside XR RTL |

The 136 added combinational cells consist of retained copies of the real
E/W mask/source-priority classifier, E/V kind classifiers, RD leaf destination
enables, and send/CI next-state controls. All 18 original gate IDs and their
incoming owner/polarity ledgers are enumerated. They are useful source decision
cones feeding assigned consumer groups; they are not a license to duplicate
the arithmetic or every sequential header ancestor.

## Same-edge proof obligations and first use

For each resettable copied state, reset value, asynchronous clear signal and
polarity, clock edge, and D Boolean function must match the original. Under a
reset-established equal-state relation, same-function D and same asynchronous
events imply equal outputs by induction after every edge. Feedback must use
equal-state copies and retain the exported per-pin polarity. The ledger gives
a constructive endpoint partition at 32 pins per source copy, including
feedback, async clears, ties and the added consumers of upstream copies.
This is a graph proof obligation, not an executed RTL equivalence proof.

The second face landing has no asynchronous reset: two copies sample the
existing first face FF at the same edge. They become equal after that edge;
independent arbitrary power-up values are not assumed equal. A bench must
prove first-use suppression during cold start and occupied reset, including
an assertion between clocks, every relevant release offset and no warmup mask.
The inherited outer landing is two ordinary rising-edge FFs, followed by two
async synchronizer FFs and one local relay edge. Do not replace it with an
asynchronously asserted raw-input tree or remove a landing edge.

Use age from the source input capture at K: classification and `rwe_c` are
K+1; the selected complete packet/context writes at K+2; first qualified
unpacker output is K+3. A final OLD pair and a NEW complete 1024-bit packet
write may occur at the same edge. The old `ur/un/ul` supplies that OLD output;
new pair zero is qualified one edge later. Clone assignment changes no edge,
no RD/CTL collision fault date, and no invalid output data behavior. Packet
data stays unreset. CTL output priority and early-overwrite faults remain.
`pkw_c/cis_c/un_c` must retain their actual next-state equations; replacing
them with an extra pipeline of the current control would introduce an edge.
Collector copy/shift order, source-reset release coincidence across regions,
and all dated fault outputs must be compared against this exact XR6 anchor.

## Concrete private source and retention plan, still ungranted

Use a distinct `ot_s81sl_xr6_retained_1019` top and helper namespace, with
parameters `HB`, `W=1104`, `V=276`, and the existing XR6 `FOREG` behavior.
Public XR, reset helper and flow source remain byte-identical. First target
is HB0 so its mapped result can be compared to this exact reference. HB1 is
not enabled by borrowing HB0 counts.

The bounded source grant would contain one private XR source file, one private
reset/retention helper file, one generation/ledger checker, and one differential
bench plus its runner. The source file retains the existing complete dataflow
and all five packet states. It replaces only the listed control decisions and
their consumer references. Per-consumer-group modules own their useful word
write/read/select functions; scalar FF copies carry `keep`, while separate
retained decision modules carry `keep_hierarchy` and explicit kept cell/wire
boundaries. Use the existing keep-reg canonicalization hook unchanged.
Equal-D wires alone are insufficient: Yosys can merge their drivers. Retaining
only the leaf FFs is insufficient: ABC can recreate the broad upstream decode.

The generator must bind every private instance/output to the exported source
owner and consumer pins, not assume a fixed RTL word width implies 32 loads.
Enabled data FFs and muxes consume multiple select pins per data bit. The exact
421/136/175.48488um2 and TT/FF clock increments 194.892316/211.845850fF remain
the **native graph capacity model**, not a promised RTL area ceiling. Source
module boundaries, polarity restoration gates, buffering, placement and CTS
may cost more. Recompute the full native fixed point from the actual mapped
successor before any physical permission; do not tune the old route.

The private reset helper must represent **16/9/4/3** region outputs and the
second face landing's two equal-D copies without adding an edge. A private
explicit outer wrapper must own that additional landing output; changing the
shared `ot_pin_regs.tcl` or silently re-running its generic two-stage wrapper
would risk double landing. The source grant must therefore name wrapper/reset
ownership explicitly before implementation. No shared-helper patch is part
of this proposal. The ordinary source-level async assertion/release proof and
physical recovery/removal remain open.

## Production HB1 is a separate source and needs a bounded inventory

QF confirms production `ceaed19c4`, XR SHA
`cc31c2d1607af9e0ac41357d3afaf19e6665b4f94ce4911e2dcaf078ec1167c3`.
`hb1_historical_source.txt` is that exact file; `hb1_to_xr6_source.diff.gz`
preserves the complete difference. The production source has no `FOREG`,
no XR5 `lov_c/rwe_c/rwr_c/tg1_c/pkw_c/cis_c/un_c/eoh/poh`, and no XR6
registered `fa/fb/fc` fault terms. Thus it differs in fault visibility as well
as retained selectors. Replaying an XR6 gate cannot qualify it.

At source declaration level, HB1 enables **1104 `bb` plus 1104 `bo_r` bits**
that HB0 eliminates. XR6 declares **492** added copy/control FF bits relative
to production (40+160+40+2+32+35+160+15+5+3). These source counts do not predict
mapped state: optimization, constants, aliases and pin-register preservation
must be counted in the real vehicle. In particular, the HB1 output gate
`pk_go && s_dir[3]` controls a real wide registered `bo`, and the incoming
band's valid/payload arbitration participates in all destination lifetimes.
There is no known HB1 mapped census in the QF packet, and no matching archived
HB1 gate was found in the bounded existing agidock128 XR gate directory list.
This is a bounded reuse search, not a claim that every fleet archive was searched.

The proposed diagnostic is **one unchanged-source HB1 inventory**, not a new
variant, physical gate or storage change:

1. Export only the two exact `ceaed19c4` source files (XR plus reset helper),
   verify their hashes from `diagnostic_manifest.json`, top `ot_s81sl_xr3`.
   Default wrapper fixes generic `HB=1,W=1104,V=276`; no defines or parameter
   overrides. No NP4/BF16 specialization, masked payloads, frozen bench edits,
   credits, clock gating or validity substitution.
2. Use the unchanged frozen keep/pin-reg canonicalization recipe whose hashes
   match the existing HB0 snapshot. Enable only existing two-stage reset
   landing (`OT_RST_LAND=1`, stages2); source pin regs are already present,
   so `OT_PIN_REGS=0`; `OT_KEEP_PIN_REGS=1`, `OT_KEEP_REGS=1`.
   Capture the generated wrapper text and its full ports/hash. This explicitly
   inventories a hardened outer reset boundary; it does not claim that QF's
   direct component instance has two extra reset edges.
3. In immutable ORFS image ID
   `sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`,
   use ASAP7 RVT NLDM **TC/TT** mapping, 770ps target, `ADDER_MAP_FILE=`;
   exact five TT libraries and matching TT/FF/SS reporting libraries, LEFs,
   platform config and latch/clockgate maps are hashed in the manifest.
   No multi-VT, MBFF fake libraries or SRAM/fakeram libraries are permitted.
   Single clock `clk`, setup uncertainty60ps/hold25ps; input/output166.667ps,
   output load80 library units, input transition150ps, max transition260ps,
   max fanout32 preserve the existing diagnostic constraints.
4. Run **only** the ORFS mapped-netlist target `1_2_yosys.v` (8 threads,
   unlimited synthesis duration). Save raw/normalized Verilog, JSON state
   identity/source attributes, canonical netlist, full synthesis log and
   constraints. A separate native OpenROAD read/link step reads the exact
   LEFs/libs and mapped Verilog, writes an **unplaced** ODB, and runs the
   complete BUF/INV-transparent all-root analyzer. Do not invoke the generic
   full `ref_route.sh`, `submit_exact`, floorplan, placement, resizer, CTS,
   global route, PG insertion or a gate daemon.
5. Emit every root/terminal/polarity; FF/master/area/clock-cap inventory;
   all top input/output register ancestry; reset D/SETN/RESETN and wrapper
   stage roles; all five packet/context/first-use roles; unconnected/multiple
   driver warnings and sequential ancestors of every unsafe combinational
   root. Any exporter/elaboration warning is retained, not waived. Use the
   actual census to price a separate HB1 source fixed point before repair.

Runner/admission proposal: stage a new immutable lane bundle under
`$OT_SCRATCH/claude/s81-xr-hb1-inventory-1019/`, not QF's source directory.
Verify selected-host container/platform hashes before execution; refuse any
existing output directory. Launch through unpinned
`ot-run --mem 16 --threads 8 --disk 20 --dir <new lane> -- bash inventory_run.sh`.
The runner performs only steps 1–5 and prints real ot-run start/exit markers.
The baseline HB0 mapping log measured **287.36MB Yosys peak / 19.06s**
(`hb0_synth_resource_witness.log`); its later native GRT graph has
95,868 cells / 16,789 FF. A 16GB admission reservation allows the separate
PDK/OpenROAD read/link and full endpoint-export processes; it is not a process
address-space or runtime cap. Record actual peak/RAM/scratch and adjust only
from measurements. At most one mapping and one sequential native analysis
run; reuse an existing object only if the entire source/helper/config/lib/image
manifest matches. No object from the b10 HB0 or logical QF build matches this
profile merely because the module name is similar.

Uniform QF BF16 proposal remains external compile-time wiring:
`q[16*i+:16]=bo[52+32*i+16+:16]` for all32 words, real expanded headers in
FP32 high halves, NP4, II4. It adds no generic XR hardware and proves no native
fanout/retention. All original live header/upper512 payload remain functional.

## Closure boundary and next decision

ROOT may authorize the single diagnostic inventory above independently of any
XR source repair. It has **not been launched**. The private retention source
also remains ungranted. Subsequent requirements are actual default/source and
cold/occupied-reset miter, four existing causal XR mutants, native all-root
retention/depth/pin checks, legal reach/outline/band/clock/neighbor/PG/access,
and exact compiler single/multi-user dates. An unplaced ODB can prove neither
reach405 nor PG, routed timing, pin spread, parent fit or token closure.
