# hidx_sel_s3u_b (IDXSFU10 10-21) -- successor of hidx_sel_s3t_b (route NEEDS_RTL TT -155.24 / FF +16.44 / DRC 0)
Failure class: S2 compare+popcount depth plus a 180 ps threshold wire from the W-face pin flops (gt[2].q -> s2_ecnt[3]); the 49 violating D pins are the S2 popcount registers.
Fix: per-lane threshold copies (16 + 2 histogram, thr bit -> 18 loads); 5-bit tie equal count summed in S3 from s2_gtot (s2_ecnt register removed). Main kit also leaves thr unanchored (OT_OFLOP_PORT_RE), so GPL places the copies beside their lane compares.
Safe-design checklist: 1 pins registered (kept pin-flop copies), reset 2-stage relay PASS; 2 reach: tile 259x216, no leg > 405 um PASS;
3 fanout <= 32 (thr 18, census at gate); 4 depth: S2 popcount tail moved to S3, same edge; 5 storage in 3 SRAM macros PASS;
6 floorplan identical to s3t_b (GRT 0, util ~51%, x 23.76 off-lattice waiver kept); 7 clock spread s3t_b 37.9/37.3 PASS; 8 schedule unchanged (registered_s3, 0 edges).

- fresh resubmit (HBM-COLLECT10/IDX 10-21): hidx_sel_s3u_b-s3ub-7d6c18676 false NEEDS_RTL = daemon bench-host bug (bench_lint ran in trimmed ot-epyc5 run dir after retry moved route to ot-epyc6: "cd .../src: No such file"); RTL/kit/gate unchanged.
