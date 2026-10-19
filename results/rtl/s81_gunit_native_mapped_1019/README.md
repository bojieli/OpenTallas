# Exact GUNIT wm2 native mapped audit — diagnostic FAIL

Frozen gate source `d9ef2759827a`, archive prefix `4ee475a24758`, gate
`dsdv_gunit_l5-20261019-121901` on ot-epyc7. No source, gate or original
artifact was changed; no synthesis or physical build was launched. Read-only
native extraction ran through admitted ot-run unit `oth-ubuntu-7641-1792439805`,
followed by read-only name/master reconciliation `oth-ubuntu-13182-1792439935`.
Both ended exit 0. Exact hashes are in source_hashes/proof_hashes/reconcile_hashes.

## Complete native logical-pin fanout

`1_synth.odb` has 326,664 native instances: 35,772 FF, 220,401 combinational,
70,342 BUF/INV, 137 ties and 12 SRAM macros. All connected native ITerm and
BTerm directions are read from OpenDB, not guessed from Verilog master names.
BUF/INV traversal ends at actual unique `(instance,pin)` or output-port endpoints.
No endpoint cap, top-N truncation, macro-port bundling, constant-role exemption,
or reset exemption applies. Clock terminals are inventoried separately.

258,042 nontransparent driver roots include 964 input bits, 35,772 FF outputs,
220,401 combinational outputs, 137 ties and 768 SRAM output pins. **579 fail >32**:
153 FF, 424 combinational and 2 ties; **577 functional roots fail**. Maximum
loads are FF101, combinational62, input12, macro1, tie3249. There are zero
unconnected logical pins, unknown directions, undriven signal nets or multiple
drivers. Every failing root includes its complete endpoint list in census.json.gz.
The full all-root/endpoints JSON (88 MB) remains on the fleet beside native_pins.tsv.
Ties require physical repair; they are not waived into a functional PASS.

Worst FF is the actual multiplier kept stage `u_mul...u_k5.g_r.r[96]` with
101 logical pins. Sinkhorn shift-selector FFs reach72 and positive-add exponent
logic reaches62. Regional reset FF9 and FF12 still drive39 and38 logical pins.
Thus kept-copy syntax survives physically but does not establish <=32 closure.
All64 `g_pin_copy` FFs survive; largest copied groups and every FF name are
preserved in summary/census. Native clock pins: 35,464 DFFHQN +308 DFFASRHQN,
24 clock pins on12 dual-clock SRAMs and one input clock, total35,797.
No additional sequential master family is hidden by a DFF-only role filter:
these are the exhaustive native clock-bearing masters. Clock reach/insertion
and arbitrary-initialization convergence are not qualified by this count.

## Reconciled native versus textbook counts

Original textbook reports417,545 cells/39,166 FF on exact `1_2_yosys.v`.
The actual ORFS `1_synth.log` explicitly performs `eliminate_dead_logic`, removing
90,881 unused instances/nets before writing `1_synth.odb`. Independent full
name/master join finds all326,664 native cells in the mapped Verilog, zero
native-only cells, zero master mismatches and exactly90,881 Verilog-only cells.
These include3,388 DFFHQN and6 DFFASRHQN:39,166−3,394=35,772 FF.
This is an artifact-stage difference proved by both the log and complete join.
The source netlist and ODB hashes remain unchanged after extraction.

Native standard-cell area40,015.15992 um² plus12 macro area6,643.074816 um²
is46,658.234736 um². Native FF area10,458.05904 um². The prior whole-model
23,096 FF reference understates this exact physical graph by12,676 FF;
source revisions must be reconciled before using the old clock/slot price.
Native area uses actual LEF master dimensions, not the different Liberty-area
metric. The12 macros are each32x64/553.589568 um²,24,576 physical bits total.

## Remaining SAFE and schedule obligations

1. Pin registration: original textbook in→reg3 levels and reg→out0; actual
   pin/first-sequential arc/native TT+FF check still needed. No broad waiver.
2. Reach: original textbook estimates134.3 um but is not placed native proof.
3. Fanout: FAIL579 roots as above; full fixed-point useful-copy model required.
4. Depth: original648.5 ps/20 levels fails the600 ps guideline; thresholds
   hf_report256/hf_max3000 conceal functional fanout failures and are not approval.
5. Storage:12 real banks confirmed. This d9 source lacks843 lifetime guard;
   cold config/admission, selected-history/collision and bank escape remain open.
   Distributed arithmetic FF groups are counted, not assumed replaceable SRAM.
6. Floorplan: no CTS/final geometry or12-bank contact escape qualified here.
   Old README206/32 intrinsic-contact argument is withdrawn; actual103contacts
   per17.304 um W/E face=5.95238/um aggregate, clustered escape remains open.
7. Clock/reset: native load inventory only, no spread/neighbor contract claim.
   Actual retained reset assertion/release and warm-reset ownership need proof.
8. Schedule: separate f03 measured1015N/1013S (+40) is different source ancestry;
   dependency packet3f043f8b7 proves differing L5/tail/Sinkhorn hashes. No age or
   full-token qualification transfers to d9 or to a renamed guarded package.

Original gate continues untouched. No REVIEW, submission, adoption or source
integration authorization is included. Fresh guarded-package owner received
this exact census as source-model evidence and must prove its own graph.

Fleet evidence: `/srv/opentallas-scratch/claude/s81-gunit-mapped-audit-1019`.
