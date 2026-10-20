# INT8 same-age safe source prototype: physical HOLD

Distinct `ot_smh_int8_tile_safe` module; no parent or default selects it. Canonical
`ot_smh_int8_tile.sv` is byte-identical to 3aa5bb9be. No gate, route or submission.
The model preceded source/build; model.json retains the original minimum cost and
separately reports actual same-flow mapped costs.

128 kept same-edge pend copies select one actual four-bit nibble each. Original
22 input-valid copies now drive at most eight pend D pins. Exact two sampled
posedge reset stages remain: one first register and nine separate final copies,
each assigned at most 24 source reset pins. Core FFs retain asynchronous sensitivity
to their assigned landed reset. Assertion/release both need the original two
sampled edges; stopped-clock raw assertion does not claim asynchronous clearing.
Source reset sinks 209, observed mapped 202: do not confuse source and mapped counts.
The inherited registered input/output ages remain low +2 / high +3, one line per two edges.

Fleet Verilator 5.050: original 20,000-cycle profile PASS 19,985 checks, 6,596 lines,
13,187 beats. Pend/sign/tag mutants fail 6,592/13,187/6,589 comparisons respectively.
One-stage-short and three-stage reset mutants both fail the actual stage
comparison (14 ns / 16 ns); their committed witnesses guard the inherited age.
Explicit reset lockstep PASS 448 checks across 16 pulse phases and 16 stopped-clock
assert/release windows. Full converter truth PASS 1,034 checks, all 256 codes in
all 128 converter lanes. Witness logs are under bench/.

Actual isolated ASAP7 RVT TT mapping with the existing exact keep-register hook:
baseline 2,659 FF/1262.32182um2/17 unsafe roots/max87; candidate 2,782 FF/
1310.90238um2/0 unsafe roots/max24. Actual delta +123 FF (+115 ASR, +8 ordinary),
+48.58056um2 and+57.031273fF CLK load. These are an apples-to-apples isolated
mapping comparison; old original gate 2531 FF is a different recipe. Both complete
raw mapped JSONs and uncapped BUF/INV-transparent own census graphs are retained
compressed. All 1036 ordinary inputs terminate at FFs; all 1070 outputs have FF
roots. Independent strict native-role oracle is still required before SAFE claim.

The initial noncanonical mapping attempt failed ABC status8B. Preserved log and
library-read witness show concatenated libraries made ABC read only the first AO
library, missing INV/BUF/basic gates. The repaired map merges native cell blocks
into one library and invokes the exact existing keep-register hook, preserving
actual QN polarity/inverters and ASR RESETN/SETN. No synthetic library or async2sync.

Physical HOLD: 64 zero / 202 one constant endpoints still require real local tie
instances and native all-driver recount. No placement, PG, routed reach, full
stage TT delay, native clock spread, neighbor boundary, parent output-select
loads or source-specific final gate geometry has been qualified. The source-only
prototype neither adopts old failed kits nor certifies complete token throughput.
