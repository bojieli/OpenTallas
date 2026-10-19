# D2D SAFE6 source model — not a qualification

SAFE5 is functionally promising but its actual post-CTS native topology is unsafe. Both geometries have the same 268 violations. This packet maps the 74 combinational roots back to real sequential/port operands and classifies all 194 register roots before any successor RTL or synthesis. Baseline source 99cbdd49d; independent native packet ba3c19864. No route retry is proposed.

## Exact causes

| Family | Roots | Actual worst loads | Required source change |
|---|---:|---:|---|
| SRAM bypass selects | 40 | 56 | 12-bit slices, not 28: at most 24 mapped selector pins; 12 rather than 5 copies per age/bank, +56 FF. Same unconditional D capture, no hold-feedback clone. |
| Calendar pointer one-hot | 64 | 34 | Split data read into 16-bit halves with explicitly distinct same-edge state. Include increment/hold/self-feedback pins in the bound. Additional 64 FF. |
| Calendar segment-base one-hot | 64 | 33 | Split first-record read into 16-bit halves, +64 FF. State is configuration loaded; arbitrary initial copies cannot be assumed equal. Prove each half loaded before use on the actual configuration/start program, or retain original state and choose another decomposition. |
| Result-valid copies | 10 | 46 | Seven-bit result groups, 22 rather than 10 copies: +12 FF. Includes both result capture and live-result bypass cones; original 15-bit sizing ignored both uses. |
| Low configuration data bits | 10 | 33 | Separate segment/base decode and table row groups. Reserve another 64 same-edge input FF; cap actual input drivers after duplication. |
| Other FF | 6 | 194 | Epoch copies 194/84, segment controls 71/68, write counter 45/34 require actual private-cone ownership. Reserve 24 FF provisionally, not a complete fix. |
| Calendar row writes | 64 comb | 64 | Two 16-bit write halves; kept useful Boolean row-qualification per half. Root count includes hold-mux pins. Do not add buffer/identity boundaries. |
| STATUS slot decode | 1 comb | 491 | Regionally replicated actual registered event valid/port feeding private slot decodes for eight-bit payload chunks. Must capture original event D at the same edge, not delay the slot or fan out the original slot to 69 copies. |
| STATUS epoch/reset | 1 comb | 150 | Independent final-stage reset release copies and private epoch masking, each at the same E2 release and assertion phase. Include RESETN as actual loads; preserve all clear events. |
| Calendar programming controls | 2 comb | 76/70 | Separate genuine cfg_we AND not-running AND region/segment predicate; cap upstream cfg-address and running roots after decomposition. |
| Written-map update | 2 comb | 64 | Private 16-bit written-map chunks, preserve clear-wins-write collision truth table. |
| Calendar live controls | 4 comb | 47/44/39/36 | Separate actual halt/start/fire/rep predicates per state group; keep full truth function and priority, no useful-logic exemption. |

The FF reservation is 284, so at least 11,786 soft clock pins versus 11,502 baseline. This is neither mapped cost nor a closed whole design: extra private event state and regional reset cost are still unspecified. No area, power, stage depth, or safe all-root claim follows from the reservation.

## Geometry, storage, schedule

Keep the 345.6 by 216 um parent-slot request provisionally. Four existing 57.912 by 45.672 macros sit at (43.2,43.2), (259.2,43.2), (43.2,129.6), (259.2,129.6), with 10.8 um pin-face halo. One full-width 40.728 um cell band at y88.872..129.6 has 14,075.5968 um² gross area before legal row quantization; original 5,941.3 um² soft cells occupy 42.21% of that before new source cost/physical cells. Entire-outline fill is low because the N face needs 1,674 pins, S1,218/W798/E106. Preserve full-face <=6/um contacts; at .192 um pitch their spans are 321.408/233.856/153.216/20.352 um. Exact clock/reset cutouts and PG pin access still need actual allocation.

The outline diagonal is 407.55 um, so the outline alone does not prove <=405 um reach. Require a complete source-node-to-placement stage ledger and constrained pin-register placement before any gate. Parent slot/pin rebinding is not granted by this model. Existing GRT0/spread69.9/64ps describe SAFE5 only.

Four 64x137 macros retain all 35,072 bits and real read/write/bypass semantics. Each calendar is 1,024 runtime bits, 2,048 total; no larger state bank is invented or partitioned to evade the SRAM rule. Changes target zero extra edges and unchanged compiled TXDP, all three phases, epoch, reset release, and first-valid ownership. Added token cycles target zero, not yet measured. The 35-layer pair and token schedules stay fixed.

## Build readiness

HOLD source build until concrete event-copy D equations, reset-copy/assertion graph, unreset configuration first-use proof, source-wide recursive fanout bounds, mapped-cell area reservation, and actual parent slot registration are supplied. No uninitialized held-state copy may rely on matching initial values. Useful Boolean helpers must have two independent live operands, preserve the actual equation, and be counted through to native mapped pins. No masks, data MCP, lowered clocks, modified golds, or timing exceptions.

Then run exact 200k lockstep, actual 35-layer pair, and existing causal mutants with Verilator5.050 on the fleet. Inspect all ultimate mapped drivers including FF/comb/top-input/reset/macro/tie, transparently traversing BUF/INV and without row caps. Only source proof plus native census and updated priced model can justify a physical gate request to ROOT.

## Bounded SF6U result (source only)

Parent authorized only the unconditional bypass/result copy prototype. New separate master `qfd_d2d_static_ovl_sf6u` leaves all old source bytes unchanged. Canonical ORFS synthesis produced actual source-mapped ODBs: baseline 11,487 FF /5,883.93396um² soft versus prototype11,555 FF/5,911.86924um²: +68FF/+27.93528um², four macros unchanged. The 15 extra post-CTS baseline FF belong to later physical stages and are not mixed into this comparison.

All40bypass unsafe roots close:96copies max24actual native pins. All10resultvalid unsafe roots close:22copies max22. Eight private AND roots each drive12real D pins. Remaining same-stage violations are148FF+74comb+2ties=224, compared198+74+2=274; no whole-safe claim or gate authority. Exact50 target violations removed at source, not through netlist surgery.

Original200kcycle lockstep PASS retains7174slots/9730FDItx/3742RX/99epochs/2910results/15334hits/498seg1starts/2resets. Existing mutants fail causally at176 and2328 respectively. Added observation-only coverage run correctly fails because original staticprogramme sees h1 truthmask1011 (h01111); this is preserved separately. An actual full64x137 leaf with all64words warmfilled and legal randomized addresses/reads/writes passes5996numeric comparisons, both usefulAND input masks1111. No assertion/gold/stimulus weakened. Full35layerpair PASS: C2K63/K2C62/roundtrip1840, unchanged compiled cycles and bit-exact Q/RESULT/KVN. Both fullpair mutants fail causally: C0+1 at cycle790 and wrong bypass age at815/numerical KVN839. Their old runner expectedPASS line deliberately reports UNEXPECTED/exit1; these are committed negative witnesses, not successful positive runs. This pair uses the existing PHY5 functional model and is not production clock/PG/timing qualification. Upstream cost is explicit: existing STATUSslot root grows491→511loads from22rather than10held-result capture groups; it remains unsafe. Raw top input max10→22. Tie max1181 remains and needs physical distribution.
