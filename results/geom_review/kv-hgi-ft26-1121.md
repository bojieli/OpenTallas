# KV HGI v8 feedthrough geometry review

D26 candidate base a9f605cb1acf, private proof epyc7 `/srv/opentallas-scratch2/claude/fable-fix-kv-hgi/ft26_middle_0`. The two-panel image `kv-hgi-ft26-1121.png` was inspected. The placed control image `epyc7:/srv/opentallas-scratch2/claude/fable-visual-0030/out/kv_hgi_v8/B_cong_paths.png` was also inspected.

At y=1030 the 86.4 μm west inter-core street carries 3,099 street-only crossing nets. The largest three named groups are ft4 station 0 (1,027), ft26 forwarded s1 (544), and ft26 station 1 (466). The ectl_Q east face also has a local hotspot, but its 1,560 payload pins go to local input-bank flops (other ends x 75–98 μm at p10–p90), away from the main inter-core hotspot. Widening its pin face alone leaves the stacked feedthroughs in place.

The proof moves only the exact ft26 bank sites. Its middle vertical leg runs at x≈648 μm, between the second and third core columns. The old x≈293 μm street still carries ft4. The one crossing in the west-west-to-middle transfer is in the open transverse neighborhood near y≈630, and the upper east-going leg runs above the head grid. All 5 relocated 1,057-bit banks have legal row sites with the other ft banks reserved. The largest paired-bit hop is 363.1 μm against the existing 405 μm FT budget. Pins, bus bit order, six-stage depth, latency, hard cores, clock taps, and PG topology are inherited from D26.

Verdict: PASS for a single comparative build. Inspect the generated kit, then route only that proof to measure GRT congestion and timing. Inter-core capacity and access around the local ectl_Q face remain measurable risks. No release from this review alone.
