# Compact GLUE physical event proposal

Status: one source and geometry proposal, personally viewed. Not adopted; no CAD launched. The completed baseline and coordinate-only B databases remain immutable. B improved selected relay distances but failed whole geometry and worsened channel demand.

The actual 28,564.946460 um² standard cells and six macro bodies totaling 26,297.987328 um² require core area at most 169,122.719628 um² to meet the METHODOLOGY minimum 20% fill of core area excluding macro bodies. This is a CORE bound; the outline includes a separate border. The existing six macro homes alone span 467,695.259712 um², so trimming the current frame while retaining all macro homes cannot meet that bound even with zero border.

The single proposed outline is 432 × 380.16 um with the actual 4.32 um core inset. Core area is 157,286.707200 um², aspect 1.136, and free-core fill 21.807%. Four D2D SRAM homes remain. The code SRAM and sys-face ROM move into the upper band using their actual body dimensions. Exact local M7 epoch/lrst pads and their first capture homes remain at measured 0.931/0.896 um reach. Any change in the parent origin or absolute package locations needs an explicit interface contract.

North, west and east interface bays reserve 39,564.288 um² against the current 32,047.918 um² CA reservation. This is an area allowance, not a per-bus bank, row, access or routing proof. All CA banks, real pin identities, widths, DEPTH4 contracts and parent-facing seams must be resolved in the physical event. No routing capacity or timing credit follows from this drawing.

## Protected source diagnosis

The current sys-face native reset chain is real: entry capture + five canonical RAW levels + two existing native relays = eight captures. Its source is u_rrl15/rst_n_t2 BOOT RAW, not gated start_t2; native relay clocks remain clk_d2d. Moving only existing rst_n__ot_rl0 to midpoint (306.531,805.005) would split actual source-to-rl1 distance into 367.821/367.821 um, bounded by 392.821 um with a 25 um site allowance. This is a source-aware coordinate candidate only. Actual occupied-site/blockage allocation, all protected fanouts, clock context and a full OpenDB census remain required before any separately approved diagnostic.

The fixed-frame START obstruction is different. The actual selected glue origin is EFALL=false, PAD0, PADW1, FWD_COPY0: p_start → s0 → s1 → FSTARTq, two register-to-register hops. The real inlet-to-farthest output distance is 1,838.144 um. Even allowing 150 um registration at each end and two 405 um hops permits only 1,110 um. Existing negative-edge sf and inactive s2/pd states cannot be counted as extra selected stages. All 32 actual FSTART flops also share the same depth-five BOOTRAW rst_n_t0 leaf. The current fixed interfaces cannot close this geometry through coordinate changes alone.

In the compact candidate, existing RAW and origin states can occupy the central macro-free region. The proposed center bounds are 397.44 um for the common RAW driver and 401.76 um for S1/S2 to every core point; a 1 um actual allocation error gives 402.76 um. These are point bounds, not native legality or routed timing. Preserve the exact reset DAG, depth, bootstrap/mission roles, selected origin mode and all existing cycles. A smaller geometry must not silently shorten the reset tree.

## Required coherent event

Repack the parent west-strip allocation and its neighbors, relocate the physical CA/D2D/clock/reset/START endpoints and corresponding parent seams, and regenerate actual matching global clock and START-provider geometry. The frozen 51,596-home d90 clock graph and retained A2 proofs cannot be relabeled for this new frame. All logical clocks, module parameters, memory contracts, pipeline cycles and pad-capture requirements remain unchanged by this proposal; implementing a physical event requires explicit impact and matching source/recipe/view evidence.

Clock capacity is a separate open obligation: 47,745 actual sinks imply at least 32 groups under a 1,500-sink planning cap, including at least 15 groups for the 21,782-sink D2D domain. These lower bounds neither require nor qualify 32 new global ports. Price the real local distribution and parent input load while preserving clock identities.

Unresolved: actual per-bus packing, native row allocation, parent seams, PG/access/channel capacity, clock distribution and nominal timing; 31 opaque paths and 212 conservative interior-stage margin cases remain explicit. There is no source/default/model adoption, route release, or CAD approval in this proposal.

Inputs: actual baseline placement in intel2 codex-qc-glue/place_spill/kit/run/results/asap7/dp_glue/base/3_place.odb; actual B diagnostic and its no-census-change evidence in commit 6124162b1; exact PRE-D13 d90 canonical event and event1131_fixed strict bind PASS. Source geometry was prepared locally under /srv/opentallas-scratch/claude/qc-native-plan-1131. No active source tree or running proof was modified.
