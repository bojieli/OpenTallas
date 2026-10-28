DIE-KV-12 2026-10-28 (successor of DIE-KV-11 2f9c38570e; COORD 08:43 duty ruling + 08:49 DIE-KV-11 ruling).
Runs: intel1:/srv/opentallas-scratch2/claude/die-kv-12-1028.  die_trial = DIE-QC-11 1465eff51c (--clock-cell inv/inv2), git
archive in qc11/ (not on main yet; no fork).  Plan hm_r26q9c, feed = DIE-KV-11 retree feed, tap pads = DIE-KV-5 pad_it2.
CHECKED-own unless marked; nothing is NUMBER-CHECKed independently.

(1) INVERTER CLOCK TREE
  Reproduction: kit_buf (QC-11 die_trial, buf) == DIE-KV-11 kit_rt byte for byte (tree.json, ctree.v, grt.tcl).
  Same feed/regions/leaf 200, five forms (kit2.sh / chain2.sh), combo GRT0 incl clock (mk_combo_kv ADJ .75/M7 0, 50 it) TT+FF:
    form        rep  cells   stages med/max  slew viol TT/FF  fall-rise TT med [min,max]  duty TT        duty FF        outside 45-55 TT/FF
    buf (KV-11) 250  10712   158/230         0/0              671 [51,1059]               0.564..1.832   0.547..1.602   1920/1919
    inv         250  11077   158/231         0/22             -22.5 [-64,19]              0.419..0.525   0.457..0.603   177/312
    inv2        250  17786   194/277         5/16             -9.0 [-44,33]               0.445..0.542   0.469..0.641   7/522
    inv         200  12653   168/261         0/0              -32.6 [-64,-0.3]            0.419..0.500   0.441..0.516   425/17
    inv2        200  18362   200/307         0/0              -17.3 [-48,17]              0.440..0.521   0.483..0.578   83/104
    inv  <-     150  15184   228/343         0/0              -7.2 [-23,13]               0.471..0.516   0.481..0.545   0/0
  (duty = (T/2 + k_spice*(fall-rise))/T, k 1.0485/1.0552; polarity checked structurally on ctree.v: 0 odd-parity taps in all forms)
  => inv at rep 150 um (CKINVDCx16, 15,048 inverters + 136 BUFx24 tap pads) is the only form with every tap inside 45-55 % at
     both corners and no slew violation.  rep 250 inverter legs after the site slide reach 340-460 um and CKINVDCx16 (weaker than
     BUFx24) violates the 320 ps slew limit at FF; the shorter spacing also cuts the per-stage residual (sign flips TT vs FF).
  inv r150: combo GRT0 TT and FF overflow 0 on every layer, usage 2.37 % (grt_inv_r150_*_congestion.txt), slew/cap clean.
     Insertion TT 649..14154 ps (BUF 698..14606), FF 571..12435.  Render clock_tree_inv_r150.png VIEWED: 1920 taps / 5970 repeaters, one
     H-tree per region fed from the centre trunk row (y ~13 mm), every region reached, no red seam-pair marker; the colour bar of
     this die_trial render is degenerate (+-0.1 ps), so arrivals are read from the GRT duty files, not the image.
  MIN-PULSE-WIDTH on the die netlist with real register clock pins (mk_mpw.py / mpw.sh): kit sta/die_top.v stand-ins
     (1,206,768 DFFHQNx1 CLK pins behind OT_CLAT) with every partition clock pin on ITS OWN built tap (1920/1920 wired), the
     inverter tree inlined flat, combo GRT SDF annotated (clock cells + interconnects re-pointed to the OT_CLAT pins), both edges
     propagated (create_clock + set_propagated_clock), spice calibration as clock derate x1.0485/x1.0552, OpenSTA
     report_check_types -min_pulse_width:
       inv r150 TT: 0 violators, worst phy_WS_7/f0/CLK high 392.53 ps vs 28.08 required, slack 364.45
       inv r150 FF: 0 violators, worst hg_EN_0/f2673/CLK low 379.44 ps vs 23.19 required, slack 356.24
       inv r200 TT/FF (control): 0 violators, worst high 349.41 / 367.28 (= the duty readout 349.4 / 367.3 at the same taps)
     (_mx = early = late = the combo max delay; the raw SDF min::max split gives the same worst on r200.)
(2) VPORT_RT BOUND 95 (COORD 08:49 conditions)
  (i) tb_kvba_vport phase D: one landed rsp word arrives with vflag 0 (K word on the V face); the reference must fault on it
      (kv_flag_fault_after = 1 edge) and the successor must match it edge for edge.  vport95_bench.txt (Verilator 5.050):
      controls D{0,15} x R{1,31,63,66,70,74,95} at RB 95: 14/14 PASS; mutants 1-8 at R 74 and R 95: 16/16 caught, incl. MUT 3
      (K/V flag ignored) errors 1497-1498 (was PASS = not caught in DIE-KV-11); RB 63 R 17 control PASS, MUT 3 caught.
  (ii) cost: the bound is a tap range, not latency.  SLM = DQ + RT + 1 = 79 -> 111 (+32 slot stages x 2 bits = 64 FF per
      qkd_pv16_vport_b); 32 kit instances (u_vport_E/W) -> +2,048 FF ~ 0.0006 mm2 (DFFHQNx1 0.29 um2; die 299.5 mm2);
      added latency 0 cycles (cfg_age selects the actual RT); tok/s cost of the bound 0.  The RT20 round trip itself (66-74
      vs 45-51 on bind4) is the TOK-KV-RT20 estimate -0.71 % (4022.2 vs 4051.0 tok/s, UNCHECKED), < 5 % -> no OWNER question.
  Applied: tools/qwen_kv_die/kv_bootage.py BOUNDS VPORT_RT 95 (+ test, PASS); tools/die_plan/regen_constants.py VPORT_RT status
      bound 31 -> 95 (shared, ROOT-MERGE; test_regen_constants 15 PASS).  The native-mission model (die_bound_native_mission.v,
      vport_* RT(31)) and the kit RTL RT(63) follow on the next regen / pair image (step 5).
(3) PLAN-vs-GATE on the phy edge columns: no local K tune.  Recorded in phy_edge_crossings.txt: the 8 DIE-KV-11 crossings
  (L689_5, L699_2 TT; L678_3..7, L699_4 FF; margin_lo 44.5..91.0) and on the inverter tree 1 (FF L678_0 hroot_WN->phy_WN_7
  87.0).  FLOW-GEN-1 1953bebd0 (gate times a partition-named port on its own pair) is not on main yet.  INFO run of its
  die_sta_related (git archive fg1/) on the inverter phase bind: CA TT 0 fail (min 106.2), FF 0 fail (min 113.7; L678_0 87.0 ->
  113.7) = the plan; its start-skew count reads 0/0 (that build predates START-TREE-1 start rows), so start-skew is from the
  START-TREE-1 gate.  Final rerun once FLOW-GEN-1 lands on main.
(4) START-TREE on the inverter tree (START-TREE-1 91c2e9fec3 --start-tree clock, K with OCV, ca.sh):
  phase: D4/D8 3414/181, start depth 33, plan sim 0 window violations (min 106.5/117.8); gate (main die_sta_related, region
     key, HB4): start-skew fail 0/189 TT and FF; CA TT 0 fail (min 105.2), FF 1 fail (L678_0, 87.0, phy column class).
  --start-clean width: plan FAIL 143 crossings (no D4/D8 window: path ambiguity up to 12 cycles), tree edges clean 103/157,
     fall-edge edges 44, start depth 52, D8 945 -> no bind (st_width_plan_summary.json).  Width is NOT usable on the inverter
     tree; phase gives the target 0 start-skew fails.
(5) NOT DONE (next): W-lane/PV pads from a new bind (retree feed + inverter tree + RT 95), pair image from the new seams, token
  sim against 4051.0 tok/s.  The tap pads (pad_it2, 32 taps / 136 BUFx24) were planned on the BUF tree and should be re-derived
  on the inverter arrivals in the plan event.
