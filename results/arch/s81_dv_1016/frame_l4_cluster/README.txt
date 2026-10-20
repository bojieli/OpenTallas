S81-DIE7/FRAME 10-18: frame cluster views for col_h9_l4 (58 inst in bind9) / col_h10_l4 (32) / col_h9_MX_l4 (32).
Verdict: GATED. No kit submitted. Hardening the whole frame is FEASIBLE in size, but four inputs are missing (below).

1. Existing flow. There is no frame-cluster flow or kit for col_h* in any lane or branch: no ref_tile spec,
   tools/die_cluster or s81bf_col / qfd_slab kit. The frames were die-level stand-ins (dv_diecase CENSUS 'frame').
   The closest precedents:
   - tools/ref_tile cluster kits with hard children (specs_qcluster qfd_c_b16_dv*: 2.45 x 5.23 mm, 48 children,
     peak_ram 192 GB);
   - the PARENTS-LANDED generator tools/landed_parent/lp.py (claude/parents-landed-1018 + 1e9dd9dc8 non-ANSI,
     not merged).

2. Size (frame_regions.py; LEF sizes from origin/main views):
   - col_h9_l4: 436 children (49 masters, 105 ot_rom_4096x72_m8), 56,973 signal nets, 0 glue cells (wires only).
     Frame 1,436.832 x 2,695.68 um = 3.87 mm2; child area 1.94 mm2 (util 0.50).
   - col_h10_l4: 486 children, 63,405 nets, 1,436.832 x 2,985.12 = 4.29 mm2; util 0.47.
   - One clock root clk drives 431 child clock pins over 2.8-3.1 mm (c26l placement); cr / cr_s go to the cfifo only.
   => Both frames are smaller than the Qwen cluster precedent, so they are routable on epyc4/epyc5.
   The alternative composition (frame children placed at die level) would put 90x56,973 + 32x63,405 = 7.16 M nets and
   54,792 hard instances into die GRT; SPEC.md rejects the flat 10 M-net GRT. A frame cluster hardened once per
   master (col_h9_MX = the col_h9 view placed MX) is the right composition.

3. Clocking (landed-regions standard): one tree over 2.8-3.1 mm is not allowed. Plan: 3 regions per frame, cut at
   the min-cut slot boundaries (regions.json):
     col_h9   cuts y 750 / 1850 um: 1,405 + 1,488 bits (x_chain 1,107 / 1,103, return_tree 133 / 385, cfg 93, reset 66)
     col_h10  cuts y 1050 / 2075 um: 1,531 + 1,551 bits
   -> 2,893 / 3,082 landed bits = 14.5k / 15.4k landing flops per frame (D 4: ring + read register), about 1.9 M
      flops die-wide (negligible area); +3 edges per landing, so the deepest region adds +6 edges each way
      (x and return).
   frame_return_plan.py must re-derive the return calendar, and dv_price must charge the edges.
   lp.py cannot land the frame as it stands: child resets come from the frame's own reset tree
   (crs4 rst -> dsfd_rstg), not from the parent rst_n (lp.py assumes reset_pins on rst_n). The frame needs
   per-region reset runs. This is an RTL change to the frame_l4 emitter (frame_lp), not a kit.

4. Missing inputs (gate only after all four):
   a. dsfd_cfifo_crs4: no view (sub-lane CRS4, branch claude/s81-die7-crs4-1018 not pushed yet).
   b. bf_col member conflict: the frame RTL binds dsfd_bf_col = compact199 ot_v41_bf_col (450.144 x 198.72, CLOSED,
      native owed; c26l frame 1,135 um wide). The p4 plan width 1,436.832 and frame_contract expect the S-ELEM
      dsfd_bf_col_cl (604.8), which has no view (lane16_cl gate FAIL, no job). Decision needed: compact199 (shrink the
      plan's frame width back to ~1,140) or S-ELEM (re-emit the frame, then floorplan).
   c. qxpq element: the RTL binds the non-RSTP element. The CLOSED view is dsrom-qelem-qs5f-efs-7fb23b7ff
      (TT +98.72 / FF +12.04). frame_contract wants RSTP=1, whose job dsrom-qelem-qs5f-rstp-f9192e143-tc-hm10-cl-2bded98f0
      is in ECO (10-18 06:36).
   d. A p4 frame floorplan: only the c26l placement exists, and it fits neither the p4 width nor the new members
      (crs4, +12 r1-skew relays, xo stations).
   Children with a closed view but no native PASS: dsfd_rly_66_EN, dsfd_rly_536_EN, dsfd_rly_66_SW (native owed),
   dsfd_rly_266_EW and dsfd_rly_66_EW (native FAIL on the OLD absolute rule; re-judge them with --relative-to).
   All other 41 masters are CLOSED + native PASS.

5. Benches: tools/s81_dv/frame_bench.sh L4=1. The PASS and xlane fail witnesses for all three masters are committed in
   results/arch/s81_dv_1016/landing/frame_l4_bench/b2,b3. Nothing is missing for the _l4 RTL.
   A landed frame_lp needs its own lockstep bench (lp.py style) plus an unland mutant.
