# R25GP area and wiring budget (hbm-phys [budget] findings, 2026-10-10 ~07:40 PT; estimates unless marked)
Working files: /tmp/claude-1000/r25gp_budget/ (plan, netlist dumps, channel model). The die GRT is still running on ot-epyc1tb (iteration 1 of 10 at the time).

## Die
- **Outline:** current main R25GP is 31,734 x 25,283 um = 802.33 mm2. The 798.5 mm2 figure is the older R25G hub height.
- **Placed:** 493.6 mm2 (61%). Whitespace 308.7 mm2; the spine column has 6.0 mm2 of free gaps.
- **Reticle 26 x 33 mm:** growth room is only +717 um in y and +1,266 um in x.

## Per item (added mm2)
1. Wide VM lanes: ~0.75 per-client, or ~0.39 shared (estimate; VM edge synth running on EPYC2).
2. ATT on striped KV: ~0.1.
3. Multi-position HC: ~0.03.
4. Row-gather engine: 0.064 (synth: 3,982 + 5,374 um2 cells plus 14 SRAM macros of 3,894 um2).
5. Pipelined ALL_GATHER: ~0.03.
6. CP burst fetch: <0.01, plus 20 die wires.
7. FP8 x-path / QDQ: QDQ's 23.2k um2 of cells fits its slot (synth); decoders ~0.02.
8. su tile: 0. The tile is 187.056 x 164.16 um, and 192 tiles fill 75.8% of the existing quarter.
9. VM8 halves: ~0.002 (+258 um2 clock buffers per half, measured).
10. Clock gating: ~0.001.

**Total ~+1.1 mm2: no area squeeze.**

## Wiring (the real constraint)
- **Per-client VM lanes:** each of the 6 clients with its own 32R+32W lanes is ~97.6k wires. That puts the VM pins at 108-112% and the west spine channel past the VM at ~132%.
- **Over the ~55-60% target today:**
  - SM row channel ~122%;
  - SW SM-group east edge ~82%.
- **Hub south edge:** ~54%.

## Verdict: a cheap floorplan change is forced
- **Shared lane groups:** one SU->SFU->HC chained group plus one spine-client group. The VM RTL 34c89274a already has one read group and one write group. Result: VM pins ~48%, channel ~47%.
- **Spine reorder:** VM adjacent to CP; quant moves into the free 423 um gap. No die growth.
- **ATT records:** run them on the existing attention tiles, which already have the striped KV lines. Not an ATT unit inside CP: that would put ~26.8k wires through the already-over SM row channel.

## Right-sized successor (owner Option A: attention 32, SU 512, SFU half, index 36)
- **Frees ~120.4 mm2:** attention 85.6, SU 15.6, SFU 8.8, index 10.5.
- **Adds ~0.7 mm2.**
- **Placed ~374 mm2 = ~47%** of the outline. Use the freed area to widen the SM row and hub/VM channels to <= ~55%.
