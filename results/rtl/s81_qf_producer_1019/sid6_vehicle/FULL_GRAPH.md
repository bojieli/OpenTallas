# Complete bounded producer graph: source seams and registered ownership

This ledger precedes another build. It pins exact historical sources in
full_graph_sources.json and the actual selected die connections in
selected_return_cone_inventory.json. Every endpoint date depends on its
regional reset and forwarded-clock epoch; those native dates remain NULL.
The512-row arithmetic model and markers are components, not a selected
calendar or source/token qualification.

The declared input boundary is genuine original q_norm.scale:1280 FP32 words,
not quantized g_d. Conversion is an open scope choice. No fixture g_d, frame
return or final Q payload may silently replace it. Original weights/scales,
rank0 rows3072..3583 and BF16 scoreboard data retain their pinned hashes.

| Stage | Exact state/interface and registered boundary | Reset/ownership and open obligation |
|---|---|---|
|Raw qnorm state|1280 FP32 words; candidate existing leaf2 VP rows608..927 (320 rows)|Candidate reservation only; no installed programme. Actual SRAM commits must precede reads.|
|Control entry|XR CTL body160b, target5 static128b row write/mask; target0 masked-leaf VP command; target2 XS is_d; target3 CAP cfg_d|XR has input/control/output registers and reset relay. Its configured body/header must preserve real sid/leaf/mask; no new adapter identity.|
|Control/CW to VP|Actual slice u_dn D=DL4 carries c/sw/cw and other sidebands together|All5 leaves equal4 stages, clock ck_cl3S. No command/CW stage omitted.|
|VP state/command|VP pin flops capture c/sw/cw; actual two512x128 SRAM banks. OP_QB9 forwards through VP s_v/s_d to VS|SRAM writes on next active edge from pin-captured CW; read-before-write returns old data on collision. c/sw/cw/extension/HSTORE write collisions fault.|
|Candidate genuine quantizer path|VP→VS QB reads8 pairs=64 FP32; VS u_v/u_i/u (8 FP32/256b) and um mode→VQ|Existing QB produces8 subbeats; VS duration19 is prior measured component bound, not new full-path latency. VQ mode/index lifetime must extend through fragment completion.|
|VQ AQ_XMEM2|Pin-captured u/mode;4 subbeats assemble32 FP32; actual AQ12x outputs FP8 q256/e10 perblock; two blocks form532b XQ|Uses existing128x256 SRAM ring,12-cycle replay control,18-cycle AQ. Two blocks and exact rounding must equal original quant_fp8. No invented truncation or fixture quantizer output.|
|VQ packet|Real header v/kind1/hops1/src sid6/global beat idx, payload e1/q1/e0/q0;4 fragments276b|Leaf k2 gives real stagger; VQ run40 cycles and dynamic mode registers cannot be overwritten while packet remains live.|
|Leaf to centre|u_up DL4 carries xf_v/xf_s/xf together|No shortcut VQ→XS. Actual4-stage glue stays in graph.|
|RSTOP own assembly|Pin captures5 leaf fragments, selects exactly one source, four-fragment assembly, registered g0 delivery|Actual src/idx/kind preserved, no sid-to-geographic shortcut. Simultaneous injection/fragment collisions fault.|
|XS gather storage|g_v/fam/idx/data pin flops; q family1024b source slot carries only532 meaningful bits; actual3x8 SRAM banks plus exponent/arrival tables|Each of20 beats arrives once; global beat=64 elements. Source bank/parity identity, duplicate/missing and two-source faults remain live.|
|XS control and output|is_d pin→OFF+2 fixed delay→calendar reader/XS controller→actual buffer reads→dsfd_pq_lx→registered xw_d1101b|No return count in XS. Calibrated g→earliest word5 is not a complete per-word selected schedule. Fixed RETIRE cannot substitute for source completion.|
|Slice X-chain heads|mk reset marker is2-stage registered; xw4={upper536,valid copy,mk,lower565,mk}; all4 copies pass DX6 relay|Clock outputs ck_xc are branches of ck_cl3S. Keep both valid/marker copies, all1104 bits, all6 stages.|
|Actual frame inputs|L01/R01 come from head copies0/1 through selected per-lane gates/stations. L02/R02 MX frames use direct copies2/3 at LK1. MX xo/xok source actual L03/R03 paths at LK2|MX is col_h9_l4 wrapper with genuine registered276b x-chain forwarders; each lane has its own xk. Preserve exact station/gate/reset names from selected die, not six independent generic inputs.|
|Frame landing/compute|Per-lane cfifo_crs4 ot_s81_land D4/K lane strap; cr reset synchronizer2 and cr_s sync2; xa/xb/cc/x2 registered. Existing cfg sequencers/real FP8 element ROM/return tree produce partials|All six clk/cr/cr_s names ck_cl3S; forwarded phase/reset dates still NULL. Body, row flags, pos and golden lo/k/n stay unchanged; input marker only masks bubbles.|
|Frame return port|Actual cfifo: ri_q on cr, rr/status on cr_s, rd70={rr,rr.valid,rsync_s}|Keep status/err/data/tag/valid together. Historical single-phase flags1 came from that op go_tag. Actual cfg sequencer counts GO modulo4; runtime row flags0..3 are legal and differ from configured idle/SENT. All15 epochs must prove actual tags and CAP CFG lifetimes; see runtime_tag_model.|
|Selected return routes|L02/R02 direct; L01/R01 one SN half-cycle station; L03/R03 two NS half-cycle stations; routed paths all landingK2|Actual ICGx4 source-reset enable, RSREG1 reset release, inverted forwarded clocks, landing write/read epochs. Native G/R0 unresolved.|
|Slice return entry|Packed lanes0..5 are L01,L02,L03,R01,R02,R03; lanes6/7 literal zero; u_rt DR6 before CAP|R01 is lane3/CAP W tree. Preserve actual packing and all6 relay stages.|
|CAP|CAP tree pin register, actual fixed-slot nodes, finish partial store/re-entry, decode/rounding, CW output registers|64 slots keyed by(pos,row16,nseg); no foreign-key overlap, F5/F6/F8/F11 freedom, config stable through old partials and D2 consumers. Three hardened leaves do not add an extra seam edge.|
|Capture destination|CW output→u_dn DL4→VP CW pin flop→actual SRAM write|Conditional structural commit=CW visible edge+6 (4 relay+1 pin+1 macro). This equation is an assumption to measure in the composed bench, not a receipt. Both bank/word masks and original BF16 data must match.|
|Later source uses|QR input/coeff reservation and output544..559; RDOUT/gather/Q512 consumer remain subsequent dependencies|No QR/gather/whole-token claim from capture success. Uniform NP4 II4 and original deadline remain unchanged.|

Marker04 includes the exact D6 return-entry relay and measures conditional
logical CAP pin sample ages7/10/11 for direct/one-station/two-station paths.
Unpinned job3695842 exited0. Earlier1/4/5 receipts measure route-to-slice-entry
sampling: their CAP label is withdrawn, receipts remain immutable. These are
logical G=R0 markers, not actual selected/native timing dates.

ROOT option, not implementation: use real VP→VS QB→VQ→RSTOP rather than change
the declared raw-qnorm boundary. One existing leaf2 can hold320 source rows,
then20 commands a0=608+16b,n8,um_q1,um_b0,um_i=b,j0=0 can process64 values per
beat. This uses40960 additional reserved bits in an existing VP SRAM,320 real
target5 writes and20 QB commands; new gates/FF/macros/clock loads are0. Existing
VQ SRAM/ring/mode and RSTOP need no physical addition. The source scratch does
not overlap QR input16..47, output544..559 or projection addresses. No free
lifetime is assumed: QB/VQ mode/run and packet assembly must drain before the
next group;20 groups and40-cycle VQ run occupancy must be priced on the real
calendar, with no guessed total edge date. The existing lower_vs programme
only emits QB for z_quant; this qnorm source programme is absent. ROOT must
choose this bounded dependency or an explicit different input boundary.

Clean run directories must refuse an existing path; fingerprints include all
selected sources, fixture hashes, controls/straps and tool version. Useful
objects and failed witnesses are retained under their immutable source sets.
No old object is relabeled after a source change. The next build stays HOLD
until input-boundary scope and this complete graph are reviewed; no additional
six-frame simulation was launched while this inventory was written.
