# East LEP unit_i0 forwarded START write control

The retained East LEP E10 placement for plan 4e2880994fc9 has forwarded START setup of −70.58 ps into lap slot 2 and −62.528 ps into data slot 1 bit 5. Both paths carry the write decision through cells near y1145–1189 µm, although the 192 fixed data write flops, four lap flops and six writer counter flops sit at y844–847 µm.

Plan b88417e8e9187d28cd672eab4389adf52bc2cf03d18360f1225d7d7688489993 composes the prior RX, guard and DATA work with one per-type, per-bus opt-in for hd_lep0N unit_i0. Four kept combinational decoders drive the original data and lap writers on the same edge. The counter, written flags, feedback muxes and read-side placement are preserved. The source-mapped ring has 369 flops in either case, and the new four leaves each map to two primitives. Lockstep passed 384 sampled edges in each of two guard configurations. A wrong-slot decoder was caught on cycle 3. Scoped binding adds only the one ring parameter and reports zero added cycles.

I viewed the exact source plan overlay. The new decoder fence is (998, 882)–(1034, 899) µm and clears all 404 hard macro, clock reservation, existing landing band and RX fence rectangles. The image and reproducer are in epyc7:/srv/opentallas-scratch2/claude/head-east-r2/cfg_rx_predict/unit_i0_write_proof. The retained CTS paths locate the original fault. The successor still needs actual detailed-placement review and native timing before any route.

The exact A2 variant RTL is 84387f350c3f. The stock default-off RTL and binder source were sent to the canonical merge gate on epyc7 as claude/codex-head-east-unit-fstart-1126@309e3c1df74b34a31e94e71facb2088b8a338db6. HEAD owns the whole East candidate source gate, packaging, and new placement.
