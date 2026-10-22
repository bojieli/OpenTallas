H16Z structural timing successor (qualification pending)

Actual H16YB route failed TT -183.92 ps / FF -23.25 ps with DRC0. H16X3 holds exact next-state calendar validation predicates on their original write edges; no programme, issue or fault latency is added. Existing single clock region is retained. Spatial clock distribution replaces the prior skewed CTS topology; actual measured clock spread and hold closure are owed. Same345.6x302.4outline, actualR0 SRAM placements and pin faces retained.

Exact sourcec0ad783cd bounded34case/1085edge old/new proof and three causal mutants PASS54cf2eb78. Native generation gold2unit2858291 rc0 yielded7114FF,32835genericcells; physical generic maximum22levels (issue fault and count-based configuration fault remain the deepest). Pre-gate mapped census PASS dce372414:31602roots/max32/0roleerrors, dynamic resetcontacts1382 on104roots/max16, rst_n5loads. Fullhead img0 PASS123/123 and imghPASS131/131; all28outputs differential24853/27988edges. BMUT3 causallyFAIL129/131. Exact frozen46file fixture+manifest and source witnesses are tracked under results/arch/qw_h16_direct_qual_1021. Physical clock/reach/placement/timing remain owed. The source native generator load cap is16; mapped audit must still prove all roots including reset <=32. Existing bound_head_netlist retains every combinational operator and creates exact kept primitive copies; no storage/subfunction cut. Source 2xprogramSRAM macros retained. Actual reach/placement and pin checks are still required; the outline alone does not prove the405um reach bound. No gate started or approved.

Pre-gate safety checklist

1. Pins PASS: inherited recipe2 input/output landing registers and two-stage reset landing; unchanged edge contract, actual native5-load reset input.
2. Reach: same345.6x302.4plan and original macro positions; spatial clock segments<=150um. Actual data reach check remains part of physical gate.
3. Fanout PASS: mapped31602roots/max32,0roleerrors; resetmax16.
4. Depth fixed: original rows-to-seal cone replaced by held exact next-state checks. Native generic max22levels; actual cell delay/timing remains gate-owned.
5. Storage PASS: eight actual SRAM macro clock endpoints retained; no new delay line or indexed data store.
6. Floorplan: inherited R0 macro lattice/pin faces and full cell bands; actual fill/pin access/geometry measured by gate.
7. Clock fixed: one region, explicit symmetric spatial tree; measured TT/FF spread and hold still owed. IO holdmargin0.03ns.
8. Schedule PASS:34cases/1085edges source differential, fullhead all28outputs and123/131imagechecks; no added programme/issue/output edge.

Static source scan sees the generated work-relative tt_ctlm_prog_h16z_qualification.py as absent. It is produced by prepare_bench.py inside the bench work tree from the tracked46-file frozen archive, with all SHA checks; no external source is required.
