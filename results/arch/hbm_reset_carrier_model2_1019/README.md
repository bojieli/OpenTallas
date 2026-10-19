# GEN2d dedicated HBM reset corridor: source-bound continuation

MODEL ONLY. No RTL, whole forest retry, synthesis, route, helper activation or release claim.

The four original forest searches remain real CPU work, not terminal failures: ep4 PIDs53500/53510 had122min CPU and939315/939327 had101min CPU at pickup. They still reject the same (12761.158,19794.988)um hop. Local postchains612089/1075179 wait. All preserved. The successive rejected root choices are progress through a search inventory, not successful graph construction.

## Clock source recovered

The nearest HBM data station being5718.492um away does not imply the nearest real HBM clock source is that far away. GEN2c has11087 real HBM clock buffers. The nearest source candidate is native `dkh_P2/Y`, BUFx12f_ASAP7_75t_R, origin(11234.7,20124.72). Its exact source graph traces207 noninverting buffer instances to `ckg_pll_hbm`, the net emitted from `hb_ckgen/pll_hbm`. `clock_graph.json` records every instance/pin/net; its Y presently drives one clock-buffer input. That is not a complete native capacitive/fanout audit or permission to tap an unqualified tree.

Selected reset-carrier clock pin(12748.842,19794.988) is1843.874um Manhattan from the source CELL ORIGIN. Actual Y-pin offset is still required, although the complete .972x.270um pad is bounded by the allocator's1.62x.27um reservation. Direct PLL-pin distance5755.576um is not the right incremental spur price. HBM period1024ps; current regional topology's model insertion9958.2ps is not propagated timing or a phase guarantee.

## A simultaneous local corridor, with existing clock cells included

Hard-only geometry first yielded six distinct32.4um-square homes/6298.56um2. A negative occupancy check found six pre-existing STREAM clock cells across four of those homes. That candidate is rejected. This explains why the old919 overlapping hard-only candidate homes cannot establish legal fit.

The second bounded path reserves ALL76233 existing stream/serial/HBM clock sites, each using the source allocator's conservative1.62x.27um envelope, as well as all actual hard-block outlines. It reserves seven complete mutually distinct32.4um-square rectangles:

| Slot | Lower-left x,y um | Prior-output to input span um |
|---|---|---:|
| 0 |11218.8,19838.8|285.494|
| 1 |11408.8,19778.8|217.588|
| 2 |11688.8,19778.8|247.780|
| 3 |11958.8,19778.8|237.780|
| 4 |12288.8,19778.8|297.780|
| 5 |12618.8,19778.8|297.780|
| 6 |12748.8,19778.8|97.780|

Total reserved outline7348.32um2, max297.780um. First span starts at source cell origin; others use the existing reset hop's actual LEF input/output pins as explicit candidate face anchors. A new forwarded CLOCK OUTPUT does not exist on that master: these are proposed pin positions, not fabricated native pins. Recompute spans from any new master's actual clock contacts. Existing data macros/relays and all source clock cells remain fixed. The native allocator reserves .972-wide pads inside1.62-wide sites, so this reservation is conservative for the two clock cell types.

The seven slots establish a bounded candidate clock spur; they do NOT establish the full reset forest. Reservations made inside the still-running speculative forest, other new domain forests, PG mesh/channels and final source pin contacts are absent. The failing reset point is a planner output coordinate, not a committed instance/net binding. No honest total reset-edge count can be inferred from the local path. All partial outcomes are preserved in separate JSON files.

## Required source model before a prototype

Use one kept clock-forwarding buffer per reserved spur slot, plus native clock pin landing/drive sized from actual load. Six intermediate slots can be clock-only; the final slot carries the two-stage face reset landing. Count seven forwarders, two reset FFs, at least eighteen PG terminal bindings (seven buffers plus two FFs, before ties) and their wire/contact area before synthesis; actual stdcell, tie, clock cap and PG mesh cost remain NULL. The7348.32um2 is reserved outline, not cell area. No SRAM/compute/data throughput is added. Signal payload one reset bit; steady-state useful bytes/cycle0; token latency delta0 only after a proven startup schedule. Per-hop wire channel demand is one clock plus reset where present, with PG reservation still open.

The existing `hbfd_rrl_hop` is an async-clear FF with D=1, not a data pipeline. It releases on the first clock edge after its input is high. Therefore simply declaring seven added stages, or assuming arbitrary forwarded clocks add one edge each, is wrong. For predecessor i and successor j, a fixed one-edge release needs, at BOTH corners,

`removal_j <= CQ_i(min)+wire_reset(min)-(C_j-C_i)(max)`

`CQ_i(max)+wire_reset(max)-(C_j-C_i)(min) <=1024-recovery_j`.

Include actual min/max clock phases, edge identities, uncertainty and clock-to-reset arcs. Where same-edge propagation or aperture collision cannot be excluded, use an explicit half-cycle source/landing contract and price it; a buffer tree does not create a half-cycle phase by declaration. No serial/stream clock or station is borrowed. Existing `set_false_path -from hb_ckgen/por_*` is not a recovery/removal proof.

Async assertion must still reach every clear pin with clocks stopped. Price the full chain's worst assertion propagation and min clear pulse at every node; deassert cannot hide an undersized POR pulse. Reassertion while releases are in flight and no-zero-init startup remain required. The new face pair adds two actual registered release stages, or +1 stage if replacing a proven one-stage leaf;1024ps per full added HBM edge. Compare common source-relative leaf ages and hand the maximum plus face stages to compiler POR scheduling. Neither branch substitution nor a full-domain age currently exists in this packet. With810 HBM reset sink pins, cap32 requires at least26 leaf drivers even before geographic partitioning; historicalfanout2048 is rejected, and internal branches also need cap32 through BUF/INV-transparent native census.

## Checklist and next decision

Pins/face2 stages MODEL; reach local geometric candidate PASS with proposed clock pins/native source Y OPEN; retained fanout<=32 OPEN; recovery/removal/depth OPEN; no runtime storage; full outline/PG/all-forest reservation OPEN; actual TT/FF phase/spread/neighbour refs OPEN; compiler startup ages OPEN. No READY/SAFE label.

The next bounded action is a source-only joint reservation/binding model that snapshots the failed attempt's reserved tiles, incorporates these existing clock cells, supplies a real clock_out abstract and per-corner phase contract, and binds the failed reset predecessor/target. If that graph cannot reserve this seven-slot spur, regrant/repack its intersecting lane rows; do not increase root-try counts or restart a forest. ROOT reviews this packet before any source prototype.

Fleet: unpinned ot-run, exact data-local ep4 units3667807(probe),3669617(hard-only path),3670315(clock ancestry),3671402(clock-reserved path), all exit0. Original four CPU searches untouched. Scripts read immutable source paths; no helper/source mutation.
