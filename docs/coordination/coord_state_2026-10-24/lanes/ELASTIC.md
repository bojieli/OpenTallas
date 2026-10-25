# ELASTIC (lane file)
Branch claude/elastic-1024 (worktree localhost:~/wt/elastic, removed after merge). No server runs (analysis + 15 s yosys cal on localhost).
## Status: DONE 2026-10-24 07:42 PDT — verdict REJECT (analytical, AGENTS.md step 1); merged main 8e69517bf2 (record only, 0 code/default change)
Record: results/arch/elastic_seam_1024/ (README verdict, analyze.py -> sizing.json, cal/ yosys ASAP7 SS area cal)
## Results
- Vehicles: P5 bound_r8 (875,012 pad flops recomputed; binder 870,428), P6 main (248,360).
- Longest lanes c_*_bf_00__rsf (7 hops, 514 b, 17/18 cyc) carry 0 pad; 98.6% (P5) / 98.7% (P6) of pad flops on <=6-cycle lanes
  waiting for a slow partner (P5: tw_we/kind 3 b at depth 17 vs tw_data 1024 b at 2 -> pad 15 x12 slices; P6: replica spread, e.g. hw ctl->hc1/hc2 +2).
- Cal: pad stage 0.3353 um2/bit, elastic FIFO entry 0.523-0.538 um2/bit (1.6x). Full-duty elastic/pad = 2.9x (P5), 5.2x (P6), 0 lanes win.
  Elastic on the 12 rsf lanes alone = +0.116 mm2 for 0 pad saved. Pad ceiling = 0.011% die (P6).
- Token latency gain 0 cycles (pad = arrival of slowest joined/locked partner); valid-gated issue would need rework of all static
  consumer leaves + joins; calendar collectives cannot stall. Rate gain <= 0% (1% = 2,291 cyc/token at 5,237 tok/s).
- Task 3 (RTL seam, exactness, 833 ps SS/FF P&R): NOT RUN — no winning lane set.
## Shared with QC-TOK
- Pads come from plan bus splits (P5) and replica depth spread (P6): fix plan-side (ride-along / equal replica hops, as r8b did for tw).
- Unpriced residual idea: rate-aware "sparse landing" for low-duty buses (needs duty measurement + consumer don't-care proof; ceiling <=0.011% die).
## OWNER?
(none)
