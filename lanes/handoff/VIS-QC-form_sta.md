# VISQC-STA-1: btab SRAM column relief for the QC st_a family (DRAFT, VIS-QC, 11-22 23:3x PST)

## Cause, seen on the renders and in the plan
- All 11 st_a types (622.08 x 1339.2) carry 4 btab SRAMs, g_btb[0..3] (ot_sram_1r1w_128x256, 94.8 x 41.1 um, 4.32-um halo).
  The V3 btab_column row (FAM-QC-HCST-R2) stacked them in one column at x 449.28 with a 51.84-um pitch, which leaves 10.78-um gaps.
- (a) The place failures are deterministic. The V3 column put one g_btb across the fixed E-face CLAND band u_cland_x_st_b_i
  {520.56, 713.01, 604.80, 721.65}. 3_3 GPL then stops with "OT_CLAND band ... overlaps hard placement blockage"; the blocking piece
  is the carved halo of the SRAM at x 544.1-546.2.
  This hit 5 V3 kits: sle_st_a_v1 cl67389ecd / cl18eece69 / cled3c1d7b, sle_st_a_v2 pvd2ec7769 and slw_st_a_v2 clf4365a62.
- (b) The congestion is a wall. With the 4.32-um halos, each 10.78-um gap keeps only 2.14 um, so the column reads as one solid
  macro, x 445-548 by about 205 um tall. Next to it is the E-face landing stack: x_ctl_fw (553-600, 467-575), b_tw_data (562-607,
  276-463) and b_hw_ctl_hc0 (562-609, 17-276). That leaves an 8.86-um slit (5 um after the halo).
  - Every N-S bus in the east 170 um has to squeeze past this wall: ft_x_fw_ctl_o, b_tw_data_i, x_fe_o and ft_b_hw_ctl_hc0_o.
  - cl9f076a5c proof kit: GRT overflow V 1145 in one row at the bottom of the column (y 480-500, x 450-555).
  - pvf82a6c28 (older sites): 17.8k overflow in the 19-um slit between u_r0 and g_btb[2], with DRT at 35.7k.
- V4 L0 (FABLE-FIX-QC-V4 l0b, bandmove.py) clears (a) only. It lifts the hit SRAM to y 725.76 with a 1.08-um gap rule, so the
  10.78-um gaps and the 8.86-um slit stay.
  On clf4365a62 it makes things worse: g_btb[3]/[1] end up with a 2.14-um gap, so the halos overlap.
  V4 therefore fixes the place failure but NOT the wall. The V4 rows do not address (b).

## The form (one row for all 11 types, 0 cycles, move only)
- The 4 g_btb stay in one column with a pitch of 71.3 um, which gives 30.24-um routing channels between SRAMs, about 13 halo-free
  tracks of width.
- Clearance of at least 30.24 um to every other hard core, landing macros included, and at least 8.64 um to every CLAND band.
- Among the legal positions, the tool picks the one with the least centre displacement.
- Result, the same on 10 types:
  - g_btb sites x 449.28 (clf4365a62: 466.56), y 660.96 / 732.26 / 803.57 / 874.87, so the column spans y 661-916.
  - The column sits east of u_r2 (45-um channel) and 74 um from the E edge.
  - The x_st_b_i band (713-722) falls inside the channel between the 1st and 2nd SRAM, with 11 um of clearance on each side.
  - The whole E corridor from y 17 to 655 is left free of SRAMs, so the landing stack keeps a 30+ um approach channel.
- Station seats inside the new halos: 4-7 per type (pvf/cl9f: 4/7). Re-site them with the btab_column.py RowAllocator re-siter
  (nearest legal, same cell).
- Cost:
  - The mean SRAM displacement is 79-243 um north.
  - b_tw_data_i and x_ctl_fw to btab legs get longer by about 200 um, so G0 must re-check 405-um placed-hop reach.
    +1 station/cycle on those legs is pre-approved if G0 flags them.
- Fallback STA-1b if reach costs more than 1 cycle: CH 21.6 / clearance 21.6 at x 436.32, with displacement 16-124 um.
  It re-sites 65-727 seats (the pv30dda31f variants are the worst), so it is the second choice.

## Files (epyc8 /srv/opentallas-scratch2/claude/VIS-QC/)
- btab_relieve.py (run with cwd = a launch tree, e.g. fable-fix-qc-v4/W/launch): PLAN_IN OUT REPORT [CH CLR BCLR].
- sta/plan_l0b_sta1.json = V4 l0b/plan.json + STA-1. The report is sta/sta1_report.json.
- STA-1b: sta/plan_l0b_sta1_21.6_21.6.json.
- Before/after plan render: scratchpad visqc/sta_fp.png (top row = V4 L0, bottom row = STA-1; cl9f076a5c, pvf82a6c28, pv88773f93,
  clf4365a62).

## Fast probe (not launched; the owner lane runs it)
1. On the STA-1 plan, re-site the seats that fall inside the new halos with FAM-QC-HCST-R3-btab_column.py logic (RowAllocator).
2. Static checks: plan_gate_pre --baseline-plan l0b/plan.json, then static G0 (chain.sh, FABLE-FIX-QC-V4 pattern on epyc10/intel1;
   epyc8 is at 99% disk).
3. Strict bind + LATCHECK, since the hard cores move.
4. Placed probe = place + quick GRT on slw_st_a_v2__cl9f076a5c, which is the measured V1145 baseline. Re-render with vq_render2.py.
   PASS = no overflow row at the btab column edge and no GPL CLAND error.
   Second probe: sle_st_a_v1__cl67389ecd, which carries the place-fail class.
5. Then one sealed --goal route kit and one OT_PROBE_THROUGH=1 kit on cl9f076a5c.
- Owners: FAM-QC-HCST-R3 (btab_column author) and FAM-QC-SLWSLE-R1 (the cl9f076a5c kits); die plan = OPUS-FIX-QC-V4-R2 (V5).
