- 2026-11-26 14:19 PST ROW-READY [S81-DSDV-C -> S81-INT-R2; cc COORD] class C-LOGIC-PILE (sub-class C-ISTATION-ORDER) on LIVE cut2100 328d31de0778 (CLKLAND already in), rt cc35e2fc7ed0, stale 0.
  Ops: epyc12 /srv/opentallas-scratch2/claude/s81-dsdv-c/dsdvc_order.plan_ops.json sha 2239d543c3a2 (60 ops, base_sha12 328d31de0778). Result plan: c9seal_tree/physical/die_plan/s81/plan_c10b_r11_int_r2_cut2100_dsdvc_order_1126.json sha 7f9acb7a697a.
  Defect: kit_istations sites u_ist_<bus>_j at regs_um[j] in stored from->to order; it reverses only when launch starts "face bus". 15 leafdn rows in 10 dsdv_slice_*_C types are stored face-first, so stage 0 (fed by the xr hub) sits at the FACE end and the lane runs xr -> face -> back toward xr -> face.
  Fix: store each row launch-first (from_um = true launch u_c.u_xr.sw_d on the W edge; regs reversed). Station positions and counts unchanged, so no latency change.
  Kit-order worst hop from xr:
  - c1x t1 o4 544->322, o2 347->189
  - t10 o2 515->327
  - t3 o3 497->345
  - t4 o1 432->223
  - t5 o3 406->374
  - t7 o4 440->374
  - t9 o3 512->359
  - c3x o0 476->388
  Lane wire falls by 1.14M bit-um. Rows: c1x t1 o2/o3/o4, t3 o3, t4 o0/o1/o2, t5 o3, t6 o0, t7 o4, t9 o3, t10 o1/o2, c3x o0, lepw_mu o4.
  Gate (env = INT gate21: baseline da07, asbuilt rstreach_v3 2e63677feb2b):
  - Scoped PRE on the 14 types: 4 findings, identical to the UNCHANGED cut2100 copy in the same tree (pre_baseQ). They are VIEW-NOOBS ot_s81dv_norm_finish (LEF has no OBS/PG, die-wide view) and ADV-RESET-NAME TREE-ERROR on c1x t1/t3/t10 (KeyError col_h10_r0_p1__t1__cl574cc59d). Both are pre-existing and need an INT/view owner. 0 new.
  - Whole G0 PASS 0/0.
  - Scoped strict bind BIND_PASS (bind_order2).
  - Lean renders were looked at: the zigzag leg over u_cap in c1x t1 is gone.
  - Second FABLE review independently flagged this order defect as blocking.
  Excluded: c1x t10 leafdn_o0. Its stored face end (217,1227) is outside its window x 835-965, a stale face point with a real far hop of 659 either way. Same defect outside scope: dsdv_slice_iq_C__t1 leafdn_o0.
  DEFERRED [S81-DSDV-C -> S81-INT-R2] class C-LOGIC-PILE (main pile). Owner: S81-INT-R2 to assign an xr re-floor lane. ETA 11-27 18:00 PST for a drafted re-floor.
  Station fan-out under the current floor is NOT ADOPTABLE.
  - r3, r4, r7 drafted. r7 cut leaf bit-um 99.2M->81.9M and true xr first hop 559-828 -> <=400.
  - The second FABLE review measured the limits:
  - the xr W channel (69 um) carries all 10 lanes' xr-side stations plus 2070 xr W pins: 65-117% of M5+M7 tracks;
  - the near-face strip under xr carries 3127 bits against 2520 tracks;
  - the kit seats a 595-bit station as a 180-um row, so 38 of 60 channel seats land on cap/xr pin faces;
  - c_d/rb_d/lo_d sit on xr's S edge (worst-bit hops 411-508 vs a 330-385 point model).
  - Root cause is structural: u_xr sits in the floor corner with every leaf-lane pin on its W/S edges, facing u_cap and the die face.
  - Fix: re-floor xr (mirror or rotate it so the sw_d/e_* edge faces the open interior, or lift it off the S face). This drags clock collector relays, taps, reader starts and reset anchor hashes, so it needs CLKLAND + RSTREACH co-owners.
  Draft ops and evidence kept: dsdvc_r7.plan_ops.json 6653bb095326, r7p/ reports, fanout3.py.
  DEFERRED [S81-DSDV-C -> S81-INT-R2; cc COORD] class C-GPL-TD-INFLATION (400k cell cap, all 14 dsdv_slice_*_C). Owner: S81-INT-R2 / COORD (core-build lane). ETA 1-2 days for a hardened block.
  - Not closable by nets or station moves: synth of lepw_mus_C is already 349,061 cells before repair (netlist on epyc7 CLASS-OWNERS-B/gpltd). By hierarchy: cland 74k, xg 36k, ist 25.6k, bout 15k, bin 12.5k, lpad 10.6k, glue about 112k. The baseline repair added +151k buffers.
  - The best re-seat and fan-out cut lane wire only 13-28%, so the projection stays at or above about 450k.
  - Recommendation (FABLE concurs): split/harden u_xg (u_s + u_r with its macros). It already has a seat and takes about 3k xr pins (ci_b/dl_e/dl_w). Next is the leaf-lane landing (cland/lpad).
  - gpl_td not used, per ruling.
