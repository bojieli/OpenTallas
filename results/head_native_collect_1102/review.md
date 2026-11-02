# HEAD native wave and inherited terminal collection

The existing l48z batch94510 has three completed PASS-COND geometry results, a live mesh_e producer, and a stale central collection ledger. The raw geometry exit1 of the three completed items is handled by their existing scoped exceptions; all three unit result.json files say verdict PASS/geom PASS-COND/AP_RC0. No new placement or redesign is needed for them. The images in this packet were personally viewed and independently reviewed by geometry.

| Current wave item | Actual data geometry | Existing scope / next action |
|---|---|---|
| hd_st_n3_transit | p90pin28.75/max137.07; r2r381.29/0; native M2–M7 adj.25,50 budget GRT0 | Adopted-slot aspect plus standing fill/empty exceptions; normal KIT result collection/enqueue |
| hd_st_n3_turn | p90pin27.66/max134.67; r2r379.62/0; same native GRT0 | Same existing exception scope; normal collection/enqueue |
| hd_spn_eshim_tx | p90pin89.75/max90.60; r2r363.69/0; same native GRT0 | Existing GEOM104/103 four-shim limits90/180/371 explicitly allow native link_o across95um strip; normal collection/enqueue |
| hd_mesh_e | Existing batch unit kw-s81hea-hdmeshe-1-94510 remains active | Preserve producer and resolved Y8.64 source/checkpoint join; no duplicate PLACE |

Runtime is Intel2 `/srv/opentallas-scratch2/claude/codex-head-wave-1131/kit-wave/s81_head/l48z/items/<item>/geom`. Current grants are in Intel2 `/home/ubuntu/coord/autopilot/kit_wave.json`, dies.s81_head.geom_exceptions[0..2]; standing fill/empty handling is geom_verdict in kit_wave.py. All three have zero clock cells: real CTS/clock-leaf/latency/source/PG/intake qualification remains required. No new waiver, full CLOCK-route, timing, DRT or source equivalence credit follows from these geometry results. No broad tick, direct ledger mutation, route launch or foreign cancellation was performed.

## Inherited routed results

`terminal_summary.json` preserves exact paths, actual signoff numbers/reasons and LEC residuals.

| Existing candidate | Terminal result | Concrete successor vehicle |
|---|---|---|
| n4_D_p2 | TT+146.30/FF+7.58; slew9TT/54FF; DRC0/PG0; archived native EQ reset4 | Better residual than B_p2; worst FF u_cland_d1_i/_10418_/B334.06 versus320. Preserve existing live n4 ECO pilot before any new repair. Pilot source is l48x wave kit, a distinct lineage from D_p2. |
| n4_B_p2 | TT+145.26/FF+7.79; slew39/83; DRC0/PG0; archived EQ reset4 | Preserve alternate; no duplicate ECO. |
| host_n A_D | TT+11.19/FF−1.48, one bit18 u_ft_bu_s2→u_ft_bu_s3; slew0; DRC3 | Native forwarded-clock disconnect must be repaired under an explicit clock/source scope before release; preserve small hold/DRC residuals. |
| host_n A_B_p2 | TT−6.33/2 endpoints, FF−.04; slew26/5; DRC3 | Worse physical alternate; same forwarded-clock failure. |
| spn_band | TT−191.82/5, FF−23.07/201; slew4729/3903 | Worst setup u_rrl_55→u_cland_rst_ad_i through16 BUFx6f repeaters, FF worst landing x_i y39→bin_x_i q551. Preserve this failed broad routed variant; follow finite band/clock closure below. |
| tileIO | TT−1089.30/1023, FF−45.57/482; slew1790/984, cap37,18 unconstrained and unexpanded child ETM | Port-buffer correction improved old−2027 failure but actual worst remains u_core.c_rb[31]→kh_gt. This is the remaining internal combinational-placement problem; do not alias it to old numeric names or solve it by input-contract relaxation. Existing tileA geometry successor below remains separate. |

## HOST: actual physical disconnect, first bad CTS boundary

Both A_D/A_B_p2 post-route LECs are UNPROVEN only at po:fclk_out_bu_o and po:fclk_out_h_rx_ft_o; failing[] is empty. Their cones contain gate_x92/x93 and matched clk_t8. These are distinct from historical E2 payload residuals.

Read-only native audits under normal4GB2T admission prove both final BUFx24 A pins are NULL, Y nets connected to the correct CLOCK output ports, and clk_t8 BTerm/net exists. Raw6_final.v and6_final_lec.v both omit the A pins. This is a real physical disconnect; no serialization/model waiver is appropriate.

Original host_b2t 3_place has no exported buffers. The first saved original4_1_cts already contains them with A=NULL; every retained A_D4_1_cts/4_cts/5_1_grt/5_2_route/final also has NULL A. Source log24–28 reports explicit landing_exports A→clk_t8 connections, followed by CTS with repair_clock_nets at32. Missing-path warnings for the two outputs appear703–704, before cts_post.tcl765. Exact operation within CTS is not proved without an intermediate snapshot, but PRD and the post-CTS hooks are excluded as the initial boundary.

`host_clock/` contains all native receipts and audit scripts plus the retained log excerpt. Native units1310838(final),1336421(boundary),1352477(baseline) all exited0 as diagnostics; they confer no physical PASS. Next bounded vehicle is an explicit post-PRE_CTS connectivity snapshot/CTS probe and a continuity guard, with ROOT scope before a physical repair. No new native proof, reconnect, placement, route, source edit or invalid-output mask was made. Flow was notified and owns no duplicate audit or serialization patch.

## Spine band API failure handled; capacity/clock holds retained

The original band32 attempt failed missing orfs_hold_mm.py. Its retry1131 supplied that helper but failed on the first FIRM instance setLocation (ODB-0359), before CTS. Both failures remain preserved.

An owned correction temporarily marks each selected instance PLACED before the same location update and restores FIRM. It reads the same retained preshift ODB, moves exactly2941 FFs by+34.56um (128 rows/four PG periods), and runs DPL/check_placement only. Native PLACE/legalization passed, maximum other-cell displacement5.3um. New actual pinmax139.83 closes the old174.39 FSTART reach; p90pin27.86/r2r390.28/0. The included new image was personally and independently viewed.

The new raw column proxy is1.168 at x90,y1982.5; old.606/GRT0 evidence cannot transfer. Nearest-tap load1993 is a count, not a distance; nearest reach254.54um, zero clock cells, unbuilt own-leaf1670.32. Thus no CTS release. Geometry supports ROOT considering one raw NO-BIRTH full CLOCK+SIGNAL GRT50 capacity diagnostic after PG0/guards, retaining clock-load/source/CTS/timing holds. No GRT/CTS/route was launched. Current owned runtime EPYC2 `codex-head-spn-bandfix-1102`, unit1334981; outer exit1 records these raw geometry holds, not a failed legal move. Sole previous own Intel1 waiter was officially canceled NOTRUN with no native outputs; no foreign or admitted job was canceled.

## TileA exact one-buffer proposal

Existing tileA native legal/pin-buffer steps passed; actual GRT0, r2r397.93/0, p90pin29.27/max144.32. Its actual image is included and was viewed. The outline NA is a missing --outline argument (measured708.48x1036.8). The real leaf gate is224.883um: BUFx16f u_rrl_118/wire11650 at(360.18,138.645)→u_rrl_118/q at(450.873,4.455).

`leaf_move_preview.json` is offline only: moving that one buffer−8.64umY gives216.243um leaf and130.788um upstream leg (was122.148), with zero overlaps against dumped cells/macros. This is a proposed same-graph/grid-compatible clock placement correction, not an actual legal/timing pass. It requires ROOT scope, native legal/PG checks, actual LOOK and clock qualification before routing. No native TileA mutation or STA was performed.
