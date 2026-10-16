HBM takeover checkpoint, 2026-10-15 21:16 PT

The 660 mm2 compact die remains the primary plan. The 449 mm2 SM-column proposal is planning only: its assumed 1,036.8 x 2,750 um SM rectangle is unsupported by the current repack. Repack requires 3,697.92 x 2,505.6 um (rp1) or 3,697.92 x 2,782.08 um (rp2). Neither the 1,292 um band-adjacent row nor the 420 um shrink used to request an SFU strip is granted by the current physical evidence. Preserve all 32 SMs and actual workloads.

Latest genuine routed-view region: PHY + 128 PCs, pcrow_c_die_clock (main e30a0484c), GRT overflow 0, TT setup +132.77 ps, FF hold +41.19 ps, 1,508 repeaters, TT insertion 16.8–17.0 ns, within-quadrant spread 20–28 ps. This region is not the full die.

The latest completed larger chain is E1 /srv/opentallas-scratch/claude/hdie-1705/diecase_b, exit 0, 196 macro instances, 198,546 globally routed nets, GRT overflow 0. Its controller, service group and SM views are SYNTH ETMs with clock entries recapped to 2 fF, without tile CTS. It is a connectivity/routing diagnostic and does not provide full-die native timing qualification. Run manifest identifies the view limitations. SS is sensitivity only; the saved chain provides TT setup and FF hold.

| Corner and master pair | Failing endpoints | Worst slack ps | Classification and next action |
| --- | ---: | ---: | --- |
| TT group → SM | 36,834 | -237,369.42 | Long unrelayed SM_HBM links plus unphysical SYNTH boundary timing; obtain real source-bound leaf views and relay the actual pin-to-pin graph. |
| TT group → controller | 6,528 | -86,465.09 | SYNTH request decode/boundary paths plus distance; split issuer/feed/controller native leaves before judging reach. |
| TT group → group | 128 | -29,116.43 | Group internal/round-trip path on unqualified ETM; classify actual hard-leaf endpoints. |
| TT controller → group | 18,667 | -11,464.30 | Native response boundary and clock-tree difference; preserve source split and measure hardened entry timing. |
| TT controller → PHY | 37,441 | -1,904.39 | Output boundary/clock phase; future real controller view must satisfy compensated native entry budget. |
| TT PHY → controller | 0 | +203.46 | Diagnostic path passes; no closure inheritance. |
| FF controller → group | 186 | -185.95 | Clock insertion/hold; actual related entries and hardened output/capture required. |
| FF controller → PHY | 1,733 | -108.80 | Clock insertion/hold; no timing exception or threshold change. |

Diecase_b propagated stream clock skew reaches +1,959.88 ps setup and -2,125.67 ps hold; HBM skew +353.93/-838.72 ps. SYNTH view boundaries and die clock delivery must be separated before using these values to order RTL changes. No identical full chain was relaunched.

Native child adoption:

- DMA bank geo1 is CLOSED TT +331.49 / FF +21.55 ps, DRC 0, native launch 181.2 / capture 138.3 ps, spread 17.4 ps. The 140.4 x 87.48 um source-bound bank is the standard for all 32 banks; actual hierarchy is L[b].u_bank.
- Reset-release rel4 is CLOSED TT +238.38 / FF +29.92 ps, DRC 0, native launch 170.8 / capture 111.4 ps. Actual hfd_ckgen has one u_rel, not four stale u_rel0..3 children. The granted parent now places u_rel west of the PLL's W-edge pins, separated by 21.6 um, within its existing 259.2 x 220.32 um outline. Parent pins already include all por_* releases.
- The DMA controller registered stk strap is requested but absent from the actual source, which still specializes STK/QID. STK0's closed controller does not qualify the other three constants. No per-stack routes were submitted.

The native_child_refresh_2116.py update pins the source, LEF, TT, FF and insertion hashes of all 33 adopted child instances, checks actual outlines, and preserves parent ports/outline/latency. Independent validation checked all hashes and nonoverlapping child rectangles. Parent packing, all incident seams, related clock delivery, detailed route, full native execution and full-die TT/FF remain OPEN. Compiler fixed-cycle execution, real on-chip RTL/mapped memories and off-die-only unpredictable elasticity remain binding.

Physical strap parent integration (opt-in source c6d11286d): the actual hfd_hgi_vms_static_SW/SE/NW/NE masters now support STRAP_BANKS=1. Their real ot_vms_slice_static children instantiate wires-only packed-port adapters and the actual hfd_vms_bank_strap_q0..3 physical wrappers. Historical default STRAP_BANKS=0 is retained pending native physical qualification. No wrapper is a pin-only alias. The existing group-major parent ports are exercised through real hub/ring/bank parent wiring.

E1 parent gate ran through ot-run (4 GB, 2 threads) at /srv/opentallas-scratch/codex/hbm-strap-parent-2116. Four actual parent positives pass 4,096 DMA writes and 21,504 exact wide-group reads, 8 sectors/edge, response at edge +6 and DMA commit +3. Twelve wrong-bank/wrong-slice/missing-bank-clock mutants fail real assertions. Each quadrant has eight actual physical-bank wrappers and 24 real mapped SRAM functional models. Expected answers come only from declared stimulus and SRAM readback assertions. The packet/hub/ring paths are instantiated but idle; they are outside this integration gate. This gate establishes source integration and fixed DMA/wide-read cycles only.

The die accepts the existing PG-clear, exact-track strap pins and the 32 declared bid/sid constant values through vm_strap_grants_2116.json. Every source and pin template is pinned; production source binding and placement remain OPEN. Importantly, the NW/NE planning bank boxes are only 339.12 um tall versus the actual 365.04 um leaf: all sixteen north banks have a 25.92 um height deficit. The grant deliberately gives no fake die origin. A future parent packing can exploit the wide pair envelope or issue a truthful resize; the current four strap routes remain untouched. The 270 x 270 M6 proposal has not been adopted.
