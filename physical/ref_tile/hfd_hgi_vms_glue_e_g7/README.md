# hfd_hgi_vms_glue_e_g7 (VM hub glue, HBM d4g, H.STA.BLK.16.1) -- g7

Owner LEAD3-HBM/L2H-PGVM-G7 10-19, branch claude/vm-glue-g7-1019. RTL rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_lt.sv +
hfd_hgi_vms_glue_tiles.sv (gen_vms_glue_tiles.py, g7 part), kit spec tools/hbm_die_v16/vms_glue_kit_specs.py (VARIANTS g7).
Lockstep bench tools/hbm_die_v16/run_vms_glue_g7_benches.sh (g6 cases + mutants g7 / g7e, Verilator 5.050), witnesses
results/rtl/vm_glue_1018/bench_g7/.

## Why g7 (cause of the g6 r2 CTS hold-repair GATE_STALL)
Measured on the g6 r2 SW gate (results/rtl/vm_glue_1018/census_g7_why): 114,320 flops, of which 71,218 have their D driven
straight by another flop (synthesis census) and 70,083 sit on PURE flop -> flop hops after placement; 29,495 of those hops
are <= 50 um and 43,814 <= 100 um.  With 25 ps hold uncertainty + the 30 ps repair margin every zero-wire pure hop is a
hold endpoint: 46,076 endpoints inside the margin, ~40k buffers inserted two per iteration until the 14,400 s cap.  It
was not clock skew (OT_SPINE leaf spread 28.4 ps) and not logic depth.  The pure hops came from
(a) the tile reach relays (pin flop + 2 relays per port): GPL placed them where HPWL is flat, i.e. next to each other --
    bk_xq_s0 p50 49 um, bk_xq_s1 71 um, then ONE hop of 386-564 um into the pin flop; the relays gave neither reach nor
    hold margin;
(b) duplicated landings: the mirror egress had six pure stages (tile pin + 2 relays, stop A / M / B) for ~1 mm; the hub
    re-landed the bank returns (br) after the tile chain;
(c) in-place alignment delays: the ring-stop lane data waits two edges in its band (a_l -> ln_m -> ln) while the header
    decode crosses <= ~700 um, and the hub request copies (qr_g1 -> qr_g) wait for the registered bank select.

## g7 changes
- relay lattice (kit hook tools/hbm_die_v16/vms_relay_lattice.tcl, PRE_GLOBAL_PLACE before the pin flops; release
  vms_relay_lattice_release.tcl at PRE_DETAIL_PLACE): every relay of a tile port chain, the stop's eg landings a_eg / eg_m
  and the hub <-> stop core relays (pi / ri / cco / rce) are FIRM on their planned point through global placement: a chain
  of d stages between pin P and anchor A has d hops and relay j sits at j / d of P -> A (anchors: lane band b for xq / xq2 /
  eg of bank b, the header band for xq_done / xq2_done / mirror_busy / ring_fault, the hub island at the tile centre for
  pq / pr / status and the client ports; each bit keeps its bus position, spread 0.35).  Dry run on the g6 SW netlist:
  31,285 relays, max legalisation move 4.5 um.  Longest hop ~360 um (b0 xq: 1,065 um in 3 hops).
- eg tile depth 1 (DEPTH eg 1): the stop's own a_eg / eg_m landings are the eg reach relays -> eg -2 edges, -4,416 flops.
- hub bank-return landing br removed (the pr chain's last relay feeds the face-group stage 1) -> pr -1 edge, -2,128 flops.
- SW flops 114,320 -> ~107,800 (under the 110,000 textbook REFUSE line); E / NW ~81,000.

## SAFE-DESIGN checklist (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | pins + reset landing | PASS (as g6): every port is a pin flop (+ reach relays); rst_n -> one face flop rst_l0 -> ot_vms_rst_forest (second landing per group, 2 sync, <= 24 kept leaves) |
| 2 | reach <= 405 um | FIXED structurally: relays on the planned lattice (above), longest planned hop ~360 um; the g6 relays had one 386-564 um hop per chain. CHECK at the gate: placed hop census (tools/hbm_die_v16/vms_glue_hop_census.tcl) |
| 3 | fanout <= 32 | PASS (g6 census 0 mapped roots > 32); g7 only removes registers (br, eg relays): the pr relay drives exactly the loads br drove |
| 4 | depth | unchanged (g6 SW 456.8 ps) |
| 5 | storage / delay lines | FIXED: the six-stage eg delay line is three planned reach hops; the hub br re-landing is gone. WAIVED with reason: the 2-edge in-band lane alignment (a_l -> ln_m -> ln) stays two flop stages -- a 2-slot ring buffer has the same hold need (its enable loop is a zero-wire Q -> mux -> D at the same 25 + 30 ps), an SRAM for 2 x 2,224 b x 2 edges would take 18 macros; g7d (fallback kit) inserts its hold delay deterministically. Hub slot store as g6 (<= 1 kb per client, 10 same-edge writers) |
| 6 | floorplan | WAIVED pin-bound (as g4-g6): ring face 8,898 b needs >= 1,483 um at 6 / um; 648 x 1555.2, no macros, one std-cell band, ~4 % util |
| 7 | clock | spine centre-fed beside the ring-stop register mass (g6 measured leaf spread 28.4 ps); io_hold_margin 0.03 (>= 0.025); flat tile: no hard children; regional roots NOT used -- the hold cause is the pure-hop count, not skew. Next structural step if this gate fails: hub as a hardened child (~31k SW flops, its own root) |
| 8 | schedule | static; g7 edge deltas vs g6 handed to H-D4G: mirror egress eg -2, bank return pr -1 (client round trip -1); everything else unchanged |
