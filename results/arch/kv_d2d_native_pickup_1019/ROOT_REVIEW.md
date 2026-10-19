# D2D safe terminal and native audit, 2026-10-19

Neither source is ready for submission or production binding. This packet is read-only evidence from exact staged snapshots at source start 353123a8d126467def3bd34fa3df362b81916ab8. The gate commit field is null because shipping used an exact-content snapshot; archive and file SHA identities are retained in gate_summary.json and compressed original receipts. No failed artifact was overwritten, no route rerun, no timing constraint changed, and no REVIEW.json written.

| Actual gate | Ordinary r7w_s1 | OVL ovl_s1 |
|---|---:|---:|
| Terminal verdict | FAIL | WARN |
| TT setup / FF hold ps | +64.940 / +33.360 | +10.506 / +34.402 |
| TT / FF boundary spread ps | 129.6 / 114.6 | 57.2 / 52.9 |
| TT / FF max insertion ps | 581.9 / 480.5 | 522.8 / 429.9 |
| Largest initial clock root | 11058 | 11076 |
| Actual GRT overflow | 0 | 0 |
| Actual measured synthesized std area um2 | 6173.1 | 6176.3 |
| Synth connected functional instances | 40694 | 40696 |
| CTS connected functional instances | 69921 | 69212 |

## Actual source failure that the gate coarse lint missed

The 1_synth.odb census counts every connected input ITerm, including reset and combinational driver outputs. It excludes POWER/GROUND before loading ITerms and never SWIG-enumerates all physical filler instances. Source reset outputs pass through INVx1 cells; they remain real broad reset branches. Both snapshots have six nonconstant, nonclock nets above 32 loads, all from u_reset_regions.g_p[1]: q[2]=158, q[5]=136, q[0]=73, q[1]=53, q[6]=53; q[4]=78 ordinary / 86 OVL. Clock ck is separately classified as a clock; constant nets 3140/1122 or 1130 are retained in raw evidence and are not functional control exceptions. No other nonconstant synth driver exceeds 32. Every immediate CTS nonclock net is <=32 after buffer insertion. That fact does not qualify the broad source reset partition or prove reset assertion/release depth. No marker-delay exception applies to these resets.

Next ordinary action: a source reset refinement plus structural boundary-clock regrouping/entry plan, modeled and source-proven before any new gate. Repeating the same ordinary source with CTS knobs is disallowed. Next OVL action: source reset refinement preserving data/clock edges, with all-domain reset-phase proof and a fresh actual mapped census. The existing WARN cannot be submitted as SAFE32.

## Actual native macro and geometry facts

Both 4_cts databases instantiate four actual ot_sram_1r1w_64x512_m1_r2c2 masters, each 171.288 x 77.784 um. Origins are (43.2,43.2), (259.2,43.2), (43.2,172.8), (259.2,172.8), R0, on the 43.2 um lattice. Actual x/y gaps are 44.712/51.816 um. Parent outline is 475.2 x 280.8 um, area 133436.16 um2; actual macro area 53293.9 um2, overall fill about 44.6%. PNGs were visually inspected: 2x2 macro arrangement, clock on east face beside the central horizontal channel, full-face external pin allocation. A floorplan PNG does not establish final standard-cell fences or native access.

Per actual macro, all 512 write data pins connect, 375 are tied constants, leaving exactly 137 live write bits; 137 of 512 read outputs have consumers. Both 6-bit addresses, write enable and clk connect. All 512 masks and repair-control/address pins are constants; this is storage padding/disabled repair, not a missing functional payload tie. VDD and VSS connect to matching PG nets, with 101 abstract rectangles each. Each signal pin has one abstract rectangle. Contact minimum area, same-net routed metal, PG continuity/IR, PG-via obstruction/escape and detailed-route DRC are NOT measured here. No native access waiver follows from 137 live columns or GRT0.

Actual SRAM clock input arrivals from original gate: ordinary TT 423.4..437.5 ps, FF356.8..371.5; OVL TT423.5..437.5, FF356.9..371.4. TT macro slew up to291.9/291.6ps, FF302.7/302.4ps. Gate child references explicitly say no reference: raw pin arrival, ref_ps0. No qualified native internal capture/launch/ETM clock reference is attached. This remains open for both tiles; the OVL boundary spread PASS does not close it.

## Source and parent contract

Both staged kit.env files select NTX3, TXDP50529302=0x03030416, SAFE_RC1, four actual SRAM blackboxes, PR data boundaries and two-stage por_n/rst_n landing. Actual top-port pin geometry reports are source-run artifacts; OVL 4879 signal/clock pins checked, zero inaccessible/outside/missing rectangles. The gated physical masters have 5045 ordinary/5055 OVL total outline pins including PG in the floorplan render. Source lists and per-file hashes are in gate_summary.json, not inferred from current main.

The coordinator reports actual GEN7 still binds historical .15 while current codec2 F2 requires .16. This packet provides no CLOSED child transport, regenerated parent LEF/native pin target map, actual parent compensation/landing clock match, ordinary .16 calendar-image composition, or OVL target11/AW12/cold-prefix proof. Those remain explicit parent obligations. /root/kv_ovl_closure owns the OVL calendar contract. Existing older CLOSED masters must remain intact; these parallel safe-kit candidates have not replaced them.

## Reproducibility

Native input paths are ot-agidock128:/srv/opentallas-scratch/claude/ref_gate/qkd_d2d_static_{r7w,ovl}_s1-20261019-082412/routes/gate/work/orfs/results/asap7/opentallas_qkd_d2d_static[_ovl]_asap7_ref_gate/base/{1_synth,4_cts}.odb. Actual mapped Verilog is adjacent 1_2_yosys.v; no final routed functional.v/6_final.odb exists in these gate runs. Each audit JSON pins its ODB SHA. audit_odb.py and pins.py use bounded signal-net indexing then findInst for macro lookups. Successful ot-run receipts audit_r2.log, audit_synth.log, audit_pins_r3.log show fleet exit0. Early invocation/geometry-API failures affected only audit scratch; no gate input changed and minimum area is explicitly null/unmeasured.
