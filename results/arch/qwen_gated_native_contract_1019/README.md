# Source-bound gated landing contract MODEL

The source/edge model passes; physical admission refuses. There is no compiled
parent phase, production reset-origin manifest, native Liberty bound or routed
clock-family receipt. No SDC, gate hook, RTL default, native source or live job
was changed. The eight typed clock descriptors in `contract.json` deliberately
have null edge bindings. Their 1536 observed scenario/bank rows preserve actual
edge indices; they cannot select a physical phase.

The immutable source is `6b61a90c1`, the native family implementation basis is
main `59835e962`, and the existing typed emitter proposal is `c05484c11`.
The latter is copied for review under `source/land_generated_clocks.py`; it is
not installed into the gate. It already requires compiler inputs, source,
mapped ICG/Liberty identity, exact root waveform, reset origins and first use.
It does not independently prove its enable-witness producer. This packet
describes the source-side obligation and the remaining production join.

`fleet_final.log` records unpinned ot-run unit `oth-ubuntu-2453012-1792432450`
on ot-epyc6, with exact c054 typed-certificate API validation. `fleet.log`
retains the first model pass. `typed_import_packaging_fail.log` preserves the
intermediate import-cache directory packaging error, corrected by hashing
files only. Four final contract tests pass, including rejection of wrong generated
edges, missing bank coverage and a test-enable source mutation. The original
384-scenario / 199008-check functional witness is reused, not rerun or
reclassified as timing. Source hashes and witness SHA are checked before the
model is evaluated. All 8 K values, 8 sampled root phases, three age bands and
both sampled reset orders are retained. This is finite behavioral coverage;
arbitrary production reset/abort sequences are not implied.

Reproduce the model with `python3 tools/qwen_split/gated_native_contract.py
results/arch/qwen_gated_native_contract_1019 --out /tmp/contract.json` and the
tests with `python3 tools/qwen_split/test_gated_native_contract.py`, on the
fleet. The final immutable run directory is
`/srv/opentallas-scratch/claude/qw-gated-native-contract-final2-1019`.

## Actual clock and enable semantics

Each bank is `ICGx1_ASAP7_75t_R` with CLK/ENA/GCLK and SE tied 0. Simulation is
a latch transparent while CLK is low followed by AND. Every capture is a
rising GCLK edge. Write enables are `meta_we && wslot[b]`; read enables are
`warm && ready1 && readsel[b]`. They produce one half-T pulse per 4T in the
qualified steady state. FIRST1 additionally registers source enable in en_q
and uses a ninth ICG; FIRST0 receives its already-forwarded source clock.
There is no admitted scan/test bypass mode. A changed SE or native master
requires a new source/native contract.

Writes rotate one-hot from the source epoch; reads rotate one-hot from rc-K.
The bank edge's phase therefore depends on the actual reset origins and K.
The observed `{1+2p,2+2p,9+2p}` declaration is valid only for its admitted
epoch, with p measured relative to its own actual source. A reset can restart
the modulo-4 phase. Neither a single arbitrary declaration nor E_case can
cover every restart. Every legal runtime phase must be analyzed, or immutable
compiler/reset-source evidence must establish a narrower set.

The write data b0..b3 and complemented read shadows r0..r3 are unreset. Two
receiver face flops rs0/rs1 release on receiver edges. Source en_q and meta_we
release on actual source edges; four writes set full_w. ready0/ready1 then
qualify the receiver after both rs1 and full_w, while warm qualifies the
K-relative read epoch. Per-region reset_face clears output selection only
with receiver reset; sel_q and output are ordinary receiver captures.

Source-only abort clears full_w through meta_we and removes read_run, but can
leave an old selection/output for a receiver edge. Sticky fault resets only
with receiver rs1. Receiver-only reset retains write storage. Thus production
must supply no-use/drain/restart and reset ownership evidence; this source
does not promise immediate zero output or fault recovery for either-side
abort. No diagnostic flag is used as a scheduling credit or stall.

## Timing admission and ages

Keep setup/hold uncertainty 60/25 ps and cross-root reserves 150/100 ps.
Current direct D4/E2 at T=833.333 ps has ideal setup
`T - (60+150+.75T) = -1.667 ps` before C2Q/setup/wire. At the 770 ps build
period it is -17.5 ps. An unchanged CTLM route cannot repair that budget.

For comparison only, pricing a genuine native bank age A and overwrite gap H
leaves ideal bounds `A*T-210` and `H*T-125`. This does not authorize replacing
the current direct contract. The actual all-K samples include 64 bank-cases
with A=.25T, hence even this candidate setup budget is -1.667 ps. Minimum
candidate ideal hold is 604.167 ps at H=.875T. These bounds omit all physical
and Liberty costs and are never slack or closure. Other positive ideal cases
remain unqualified. Parent phase authority stays null; no phase is chosen
to fit a budget.

The original fixed startup model remains: receiver landed release is raw
release +2 edges; take the first receiver edge strictly after the fourth
physical bank write, complete the two receiver ready captures and K warm-up,
then price two receiver edges to first usable output. FIRST1 source enable
adds one write-epoch edge. Restart must repeat that fixed reservation and
bind absolute edge origins. No numerical production prologue is invented.

The landing adds one receiver capture versus the older read-mux form. It has
total receiver age 4 in the functional B4 prototype. `9a92ac53f` demonstrates
that a bank command enters an immutable child's internal wq/aq/dq capture;
that capture cannot be removed. Bankcmd may consequently add four external
edges, with TX+7/RX+6, LU66/LS391 and +2834 token cycles as an unadopted MODEL.
The prior TX+6/RX+6, LU65/LS390 and +2616 estimate remains historical MODEL.
Replaceable q_pin/rf/rx_flit soft captures may permit +3, but no composed
four-crossing vehicle or production token measurement exists here.

## Sizing, native ownership and structural comparison

Per W180 tile: 4x180 write bits, 4x180 read-shadow bits, 180 output bits,
12 local select/reset regions, 1737 mapped FFs and 9 ICG latches =1746 state
bits. The prior mapped area is 616.2237 um2, modeled outline39.096 square,
core utilization .514, raw receiver reset2 and collapsed nonclock loads<=31.
These are inherited synthesis/floorplan findings, not new native timing.
There are two parent clock roots and eight generated bank families; the ninth
FIRST1 gate is source-derived and also needs native ownership. Each bank
owns W payload+3 epoch FFs, so measured data-bank sinks are183 at W180.
Receiver-root control/output and source-root control are separate owned sinks.
Top inputs187 bits, outputs183 bits (180 payload, fault, two real tie outputs).
At full width ingress/egress180 bits per source/receiver edge, MAC rate0.
Each tile sustains one word per parent edge after fixed prologue. Four W180
tiles cover a600-bit boundary with120 padding bits, fourfold control/clock
cost, and no demonstrated power gain. No dynamic indexed >2kb array appears
inside one tile; the total state remains below2kb. The outline diagonal is
55.29um, a geometry bound only; actual placed full-cone reach is unproved.

Complete CTLM core/HR hardening still has two roots and needs a real relative
phase contract. The D4 write/read separation costs4344 seam pins (3808 data,
224 valid,312 epoch), or10.056 pins/um on a432um face. M4 pitch.192 needs
834um before other pins, hence864um lattice face; the three core ROM homes
also do not fit the current SRAM lattice. Complete destination-leaf pairs
reduce that seam to514 plus438 external core inputs but do not establish
their two-root phase. The genuine bank-edge route removes neither these
geometry costs nor its source-bound phase/enable proof. No full CTLM CTS retry
is warranted until ROOT selects a physically admissible structural model.

## SAFE checklist before any future gate

| Item | State | Required evidence |
|---|---|---|
| Inputs/outputs/reset | SOURCE ONLY | actual pin capture, source reset, abort/restart first-use bind |
| <=405um reach | MODEL ONLY | actual source-owned placement and every cone/pin stage |
| <=32 useful loads | PRIOR SYNTH ONLY | fresh native census incl upstream enables/reset |
| <=600ps/depth | OPEN | all native data/select/status/reset and ICG gating checks |
| SRAM/holding | SOURCE MODEL | one tile1746state, four finite banks; no deep holding chain |
| Geometry/PG/access | OPEN | ROOT PNG/checklist, fullfaces/rows/PG/contact and40-60% actual fill |
| Clock spread <=80 | OPEN | exact native Liberty/master, family census, routed TT/FF references |
| Static schedule | MODEL ONLY | compiler edge/reset/K/first-use/throughput+capture cost adoption |

No permission for a gate, physical phase, masks, data exceptions or adoption
is inferred from any passing source/model check.
