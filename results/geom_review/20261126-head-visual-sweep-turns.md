# HEAD placement review of canary Turn A and W10 N3 Turn

## Turn A canary placement

**Pass for placement geometry.** Viewed the exact layout and density images from the historical Intel2 canary run. Five runs from 20:15 to 23:30 share the same detailed-placement ODB, SHA eaccf620519ef3762c90, so one image pair covers them. The narrow slot contains no hard macro wall. The input pin band runs along the west edge, and the lower half has two sparse diagonal register lanes. The density plot shows isolated rows and no severe continuous hotspot. The native placement review flags a 320.2 µm fanout spread, under the 405 µm reach reference. The already-routed historical run reported TT setup +322.86 ps and FF hold −60.30 ps on 568 parent-boundary endpoints, with zero internal FF violations. Its parent qualification remains NEEDS_PARENT. This review records no new sign-off.

Images on Intel2 at /srv/opentallas-scratch2/claude/flow-canary/runs/s81_head_368393d77_1125_233033_806232/gen/hd_turn_a/run/layout_review/place/layout.png and density.png in that directory.

## W10 N3 Turn

**Issues. Route held.** Viewed the exact placement image from the W10 Intel1 kit. The two ring bands sit near the north and east input faces and most of the large soft slot is empty. The main local clock still appears as a long direct leg before the stock tap split, including a 1205.38 µm path to a north ring register. The separate forwarded-output scan identifies 1145 µm from clk_t9 to fclk_out_u1_o and 425 µm from clk_t13 to fclk_out_d1_o. Actual placed output launches occupy the east and north edge bands. A scoped source candidate uses the nearer existing same-phase taps and consistently assigns data and FSTART/ready/fault registers to those taps. Physical confirmation requires a reviewed admitted CTS-only probe.

The event census counts 10 to 9 declared reset seeds. At the coordinate it flags, W9's u_rrl_19/rst_n_t19 and W10's u_rrl_34/rst_n_t21 both provide a depth-five gated reset at [604.8, 587.52] µm to u_ft_d1_s3. The W10 plan's clk_t21 contributes this location to the emitted reset tree. Its physical placement reports 159 firm reset flops, no missing members and longest hop 381.2 µm.

Image on Intel1 at /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w10_1125/items/hd_st_n3_turn/geom/auto_geom.png. Exact clock-origin readback at /srv/opentallas-scratch2/claude/head-allfix/n3_turn_review_1126/n3_turn_clock_roots.tsv, unit oth-ubuntu-3464174-1795684443.

### Scoped N3 Turn repair reviewed

**Pass for the forwarded-clock plan change and a placement-only probe.** Viewed the plan overlay for 4758c78a2c38 with all 1,034 exact W10 output launches. Both proposed taps sit beside the intended edge bands. The u1 clock export is 48.320 µm from clk_t4 and the d1 export is 47.232 µm from clk_t20. Their longest tap-to-launch estimates are 147.105 and 150.055 µm respectively. The same-phase fix adds zero cycles. The generated wrapper differs in only the two forwarded-clock aliases and scoped PRE reports zero findings.

An in-memory replay of the stock tap hook on the exact W10 placement assigned all 518 u1 launches to clk_t4, all 516 d1 launches to clk_t20 and preserved functional clock ancestry for all 11,462 sequential pins. The stock local-read tap split reduced maximum pre-CTS legs to 116.879 µm north and 110.273 µm east. Each tap is under the 1,200-sink cap. The replay emitted no changed ODB. Actual revised placement and CTS timing must still be reviewed.

The candidate overlay is on E12 at /srv/opentallas-scratch2/claude/head-allfix/w10cut/n3_turn_fwd_local_1126/n3_turn_fwd_plan_review.png. Its scoped plan, source delta and fixed tap environment are in the same directory. The Stock tap replay receipt is on Intel1 at /srv/opentallas-scratch2/claude/head-allfix/n3_turn_review_1126/hook_model/n3_turn_clock_roots.tsv, unit oth-ubuntu-3624932-1795684784. All ten FT consumers retain reset depth five between W9 and W10 and the four raw exports retain ages 2/3/2/4.
