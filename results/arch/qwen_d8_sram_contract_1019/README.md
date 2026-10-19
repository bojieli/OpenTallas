# D8 SRAM source contract: historical nine-lane inventory

MODEL ONLY. The existing production source remains D4 with three K pins and modulo8 calendar. No RTL, default substitution, synthesis, gate, native timing or token qualification is introduced. This packet refines fd363bb2c using the actual 109-lane ledger pinned7cda48173 and historical die0d4c9808f. The exact snapshot digest and source/port/root/chain evidence are embedded in model.json. These are historical bindings, not an assertion that today's production GEN has adopted them.

All nine offending lanes preserve their complete original bus bit ordering, including any embedded controls. The proposed storage record appends four write-epoch bits and one written-valid bit above that bus. Semantic subfields and cross-bus control lifetime are not certified; additional fields would change the count and require regeneration. Reset, clocks and K are independent functional ports, never payload omissions. No bus field is dropped because it looks unused.

| Historical bus | Full payload | Proposed record | Minimum32x64 banks |
| --- | ---: | ---: | ---: |
| dvs_W5.ag_wo -> tt_ctlm.ag5 | 10 | 15 | 1 |
| dvs_W5.dd_wo -> native59.dd_i | 548 | 553 | 9 |
| dvs_W5.ss_wo -> tt_ctlm.ss5 | 107 | 112 | 2 |
| io_collective.cmd_free -> sys_face.io_cmd_free | 1 | 6 | 1 |
| io_collective.fault -> sys_face.io_fault | 1 | 6 | 1 |
| io_collective.shared_fault -> sys_face.io_shared_fault | 1 | 6 | 1 |
| native59.dr_o -> dvs_W5.dr_wi | 520 | 525 | 9 |
| tt_ctlm.cmd -> dvs_W5.cmd_wi | 116 | 121 | 2 |
| tt_ctlm.hr -> dvs_W5.hr_wi | 453 | 458 | 8 |

Thus no offending lane is actually W600. Each candidate record fits640bits, but ten-bank binding remains refused until complete semantic/control/epoch/reset contracts are certified. Nine independent rings need34 macros, not ten shared macros: roots and differing stream epochs prevent silent banking together. This is69632 physical bits and18822.045312um2 macro area before soft cells, pin registers, channels, PG or clock trees. All68 macro clock ports are functional. A hypothetical ten-bank coupon's20 individual clock port paths are explicitly listed, without selecting that coupon for production. Tiny scalar rings are included in this inventory; their appropriate implementation remains subject to the delay-line rule and ROOT review.

The exact selected MODEL primitive is ot_sram_1r1w2c_32x64_m1 introduced e26d92503, 31.992x17.304um, 103 signal contacts per W/E face,5.95238 contacts/um. All behavioural, blackbox, LEF, JSON and TT/FF/SS Liberty hashes plus compiler/calibration hashes are pinned. There are no repair spares or SRAM ECC in this primitive. Existing academic fault-free SRAM policy applies. Primitive external escape evidence does not qualify an array, PG hook, clock route or parent slot. Geometry must use43.2um macro origins and legal full-face access; the two-row universal5x2 coupon is not an approved placement.

The macro reads synchronously on rclk and holds rd_out when r_ce_in=0. Its write and read use separate always blocks. **Same-address simultaneous read/write is forbidden, not a defined cross-clock OLD read.** Any required OLD value must be guaranteed by a noncollision schedule or a separately priced forwarding mechanism. OT_MEM_NO_INIT must be used for arbitrary-array validation; neither array nor rd_out may be assumed zero. Written validity inside uninitialized memory cannot self-authenticate: the model reserves eight asynchronously invalidated external row-valid bits per ring, with source-bound release/lifetime/CDC proof still missing.

Source ownership is the actual final forwarded clock for wclk and receiving regional root for rclk, not an assumed common PLL edge. model.json retains each historical source/read root, G, R0, E, K, exact relay chain and source evidence. Existing declarations have residual E_sta6/7 outside D4<=3. D8 K must be four bits/mod16 and re-derived from actual reset/read pipeline epochs; widening an old modulo8 strap does not establish correctness. Actual native phases, source pulse/recovery, reset epochs, stopped-clock restart and consumer first-use remain NULL. The adjacent actual CTLM HR low73 source failure512/512 at n26/E19/K6/G1333/R01266 is preserved; it is not repaired by this model.

The source-origin distinction matters. The pinned5a266752c ot_qfd_gated_region source (copied verbatim here with hash) writes b[s]/ep[s] at W(s,j), captures ~b[s]/~ep[s] at the selected receiver-root rbank_clk[s] edge R(j), and only at the following receiver edge R(j)+1 selects that captured word into o. Its readsel is predecoded from the previous receiver edge and sel_q/expected/epoch move with the capture. Prior D8 min1.25T describes W->R read-bank capture, **not** W->final output. D8 itself remains an arithmetic extension of this D4 source.

| Edge | Existing gated D4 source | Candidate SRAM mechanism, not built |
| --- | --- | --- |
| W(s,j) | b[s]<=i and ep[s]<=wc | write full ordered record at address s |
| R(j) | selected r[s]<=~b[s], er[s]<=~ep[s]; capture sel/run/expected | synchronous macro read at SAME edge using stable preedge readsel index; capture matching run/expected |
| R(j)+1 | o selects prior r/sel_q; compare matching prior epoch | o captures prior macro rd_out; compare aligned epoch/valid |

Thus a registered SRAM read may replace the selected read-bank capture at the already-existing R edge, without moving that edge. This remains conditional: a single macro-read result replaces eight retained read banks only if each next output uses exactly the previous selected result, the read address and enable are valid beforeR, and macro output hold/metadata/reset/noncollision behavior matches. Complement representation in old r[s] must be accounted for, not double-inverted. There is no D8 source equivalence proof yet. Current legacy production ot_qfd_land instead directly muxes bank into o atR; it has no duplicate read-bank stage to replace, so a macro substitute there adds an output edge unless independently proved and priced.

Advancing any actual read by1T is a separate, unsafe proposal: prior model min1.25T becomes0.25T=208.333ps, less than unchanged60ps uncertainty+150ps reserve before TT macro setup28.256ps and wires. No edge is advanced to manufacture slack. For the same-edge candidate, each address lifetime starts atW(s,j), must includeR(j) after setup, and ends beforeW(s,j+8); the prior3.875T minimum read-to-overwrite gap is model arithmetic only. Exact phase, first-use, staleepoch, clocks stopping, mixed reset and every simultaneous-address exclusion remain unproven. TT macro CQ243.694/setup28.256/hold21.600ps and FF CQ196.092/setup24.695/hold19.672ps are project-model arcs, not in-context margin. A ROOT-reviewed W453/eight-bank mechanism must prove this exact table or explicitly charge an extra receiver edge.

The nine rings retain1757 output payload FFs plus a baseline162 soft bits for two4-bit counters, warm/fault and8 external valid flags per ring. This is a lower bound; output epoch/valid capture, pin wrappers, reset forest, fanout copies, enable/address pipeline and real fault-lifetime logic are NULL. All34 macros contribute TT clock capacitance635.5144fF across68 pins. A simultaneous array read/write edge is2031.926/3853.332fJ at TT; eight initialization writes cost30826.659fJ before soft control/clocks. Eight writes cost four additional source edges versus D4. They do not define absolute first use or token latency. Further init due real source/receiver reset mismatch must be charged.

Before any RTL: certify semantic complete fields and source publication for all selected lanes; fix the actual modulo16 read/write epoch ledger; derive first-use/cold/warm/abort/stopped-clock schedules; prove no collision with arbitrary memory; bind per-port TT/FF waveform/native phase; count every control and pin FF and PG/access route. Then ROOT can authorize one default-off minimal mechanism and its causal mutants. No full array, physical gate or main activation is ready. integrity.log verifies only bounded JSON arithmetic and exact committed view hashes.
