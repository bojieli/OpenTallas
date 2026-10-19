# qfd_d2d_static_safe3 — MU D2D structural candidate

Same RTL, overlap ports, static TXDP0x0a010308 and475.2x280.8um outline as immutable mu1 gate0542eaaa0 (WARN0fail, TT setup+93.7ps/hold+32.6ps, TT/FF pinspread48.9/44.0ps, GRT overflow0). Signoff policy is TT setup and FF hold; SS is sensitivity only. This candidate changes physical pin allocation and same-edge reset-state replication, with zero added transport/reset edges.

The actual mu1 ODB has3668 functional scalar pins: N1674,S1170,W758,E66. Every face is reallocated at minimum0.192um pitch (5.208pins/um) using legal actual routing tracks and the canonical exact-pin helper. N clock remains237.516; E reset capture pins remain unchanged. This replaces the old literal S/W0.096um clusters and N0.144um rounding. The source pin inventory and every scalar grant are in pin_inventory.json. Die GEN must bind the new pin locations and re-derive any seam hops; the source RTL does not add stages.

The physical reset hook copies only existing sequential cells under u_reset_regions/u_por_region, with identical master,D,clock,async controls and preserved buffer/inverter paths. It recursively limits upstream fanout too. Actual mu1 ODB test gives8 additional reset flops,16 copied flop/buffer equations independently checked, and maximum32 ultimate buffer-tree terminal loads. No new pipeline stages or altered reset release edges. The proof and all3668 exact scalar grants pass in bench_witness/reset_and_exact_grants.log. Independent actual-pitch/PG-via bbox audits passed; full and filtered witnesses are committed in bench_witness.

Safe-design checklist:

1. Pins: same RTL PR1 input/output flops; existing two-stage reset captures remain at E pins. PASS inherited behavior; candidate gate must check new physical anchors.
2. Reach: same outline/macros and local registered boundaries; candidate placement must check reach. No transport edge added by the source change.
3. Fanout: same-edge reset replicas <=32 terminal loads, independently checked on actual source ODB. PASS transformation proof; candidate netlist must emit the same inventory.
4. Depth: source RTL unchanged; mu1 reg-reg TT setup+93.7ps, estimated483.4ps depth. Candidate timing pending.
5. Storage: four64x512 SRAM slot stores. The existing1-bit TXD delays <=10 bits keep their inherited documented waiver.
6. Geometry: all macro origins on43.2um lattice;44.712um column and30.216um row channels; aspect1.69; totalfill45.5%, low std-density9.1% is pin/macro limited. All external scalar grants >=0.192um pitch. Raw SRAM faces have793W/792E M4 pins over77.784um (~10.2/um), so literal<=6 raw macro-face rule FAIL. Per ROOT, a candidate gate may run while actual PG/via channel escape budget and pin-access/DRC evidence are prepared; final review waits for that evidence. No automatic waiver.
7. Clock: N clock entry unchanged at SRAM column channel beside register band; hold margin30ps. Prior TT/FF spread48.9/44.0ps; candidate CTS still required.
8. Schedule: static calendar, no credits/backpressure; no RTL or transport edge change. Candidate pin shifts must be rebound/repriced in die GEN if seam hops change.

No REVIEW.json or submission. The gate is evidence collection, with raw macro escape qualification still pending.


Safe3 corrects the preservation/CTS contract. Safe2 source657f5cb35 failed before CTS (immutable evidence83fa480e0): whole-cell dont_touch prevented disconnecting a copied CLK pin. Safe3 creates state copies after synthesis, permits real clock/data repair, and persists exact state-master/input equations. Read-only postCTS/GRT/DRT audits require all state copies retained, every input equation unchanged (transparent buffer/inverter changes normalized), and all reset-stage buffer-tree terminal loads<=32. This supplies actual preservation evidence rather than blocking timing repair. Physical clock disconnection/reconnection testPASS; deliberate D<-CLK corruption is detected; restorePASS. Actual external pin pitch/PG-via overlap audit also PASS on all3668 pins, including an independent full-PG scan. Rawmacroescape qualification remains pending; no REVIEW/submit.
