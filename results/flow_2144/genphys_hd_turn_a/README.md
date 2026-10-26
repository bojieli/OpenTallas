# hd_turn_a: generic MCMM GRT rejected

Actual same-checkpoint A/B, GRT only, source0c87522f27fa; candidate flow20b6f41993f65d4b79f7627c090d9737345cf589. Both copies read4_cts SHA25676035acc835e28545531caeab97d19e32bfc7512a924dc8f040b0021decb102f. Geometry reviewed before launch (floorplan.png, density.png; review record in results/geom_review/codex_genphys_mcmm_ab_2144). Independent post-GRT measurements use native TT/FF libraries and their own virtual-clock references250/202.5ps, clock833ps, uncertainty60/25ps unchanged.

| Arm | TT setup ps | FF hold ps | Hold buffers | Initial GRT overflow |
|---|---:|---:|---:|---:|
| FF-only BC/bc | -31.28 | +4.82 | 1801 | 0 |
| MCMM BC/tc+bc | +25.74 | -44.57 | 6 | 0 |
| Separate TT-only setup stage | +25.74 | -44.57 | 0 | 0 |

MCMM did not fix hold: repair WNS stayed-86.961ps through1000iterations and inserted only6buffers. This is the TT hold value in a shared FF virtual-clock frame (native TT hold-39.46 minus47.5ps corner-reference difference). FF-only repair progressed, reached its configured5ps repair margin, and ended with native FF hold+4.82. Changing the corner set trades away49.39ps FF hold for57.02ps TT setup by leaving input-relay holds unrepaired; it is rejected as a generic flow default.

The original reference remains physically failed. FF-only hold padding produces TT setup-31.28; the unpadded reference gives TT setup+25.74 and FF hold-44.57. Actual path census: TT worst t_i[381] to u_ft_t_s0/q[381], FF worst t_i[0] to u_ft_t_s0/q[0]; reset recovery/removal and outputs pass. The frozen FT contract (t_i max699.72ps/min-40ps) and clock distribution need a structural correction. The global worst values refer to different bits, so they alone do not prove an infeasible per-bit window. Pin-register insertion also fails, TT216.86/FF173.49 vs250/202.5 with20ps gate tolerance. No clock, uncertainty or IO contract was relaxed.

The fresh sequential proof runs TT-only setup with vclk250, then FF-only hold in a new OpenROAD process with vclk202.5, and checks native TT/FF after each. TT-only setup required no change; the separate FF stage remains live on intel2, unit oth-ubuntu-2802334-1792990665, scratch2/claude/codex-genphys-ab-2144/seq_ff, at this commit. Its final receipt will be appended, without changing these A/B failures.

No RTL or cycle change. No DRT, adoption, sign-off or die gate claim. Scripts are diagnostic replays against isolated copies; they do not install shared defaults. run.sh and run_seq.sh must be launched through ot-run with the staged self-contained scratch input copies. Existing sources and failed outputs are preserved.
