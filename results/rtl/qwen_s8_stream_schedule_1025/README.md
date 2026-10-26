# Bound S8 stream occupancy uses the actual4-edge hop

`Sched.keys` still reserved every x-stream hop as2 edges after the bound-slice successor changed the stream-tile pass latency to4. Its collision checker therefore accepted a calendar that lost4 of24 SiLU activation words on the last4 slices and faulted the stream ports.

The occupancy now uses `D.ST_HOP` (slice2=2 unchanged; s8=4, already measured and used by output-edge checks). On the existing fixed-SU-start12-slice binary with the same L0SiLU fixture, the old2-edge occupancy FAILS1/2 with20/24words and faults on slices8..11. The fixed4-edge occupancy PASSES2/2, all24words bit-exact at their compiled edge,1536/1536ISA-gold words, all-slice status clean and0collisions. Span935->939 is+4 schedule edges per layer, no new hardware cycle.

The old run is the effective wrong-hop negative control. A separately attempted `xslot` invocation also passes because that mutant is not applied in the SiLU scheduling branch; it is not credited as a caught negative control. The first staging attempt imported the old compiler through helper symlinks and therefore reproduced the old failure; private physical copies plus a runtime import check resolved that setup problem.

Runs: intel2 `/srv/opentallas-scratch2/claude/codex-qc-tokens/stream/{clean,clean_v2,mutant_v2}`, via ot-run3GiB/1thread, reusing the existing binary. This functional compiler repair is independent of the CROM operand-age RTL repair.
