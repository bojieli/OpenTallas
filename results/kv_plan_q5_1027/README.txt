KV-PLAN-DELTA-3  hm_r26q5  (claude/kv-plan-q5-1027, 2026-10-27, base hm_r26q4 b5aefbd6)
Real-copy plan dir intel2:/srv/opentallas-scratch2/claude/kv-plan-q5-1027/pd (0 symlinks; plan.sha256, cores_q5.sha256).
  hm_r26q5a 730c234e = q4 + (b) ahub zh early taps
  hm_r26q5b 99b9d6dd = q5a + (c) hr pin form + phy_pad entry      <- KIT PLAN (all core/kit deltas, PL die grid)
  hm_r26q5  b336d093 = q5b + (d) die.pg.grid G12                  <- G12 CANDIDATE, clock mesh BLOCKED (see d)
Each step asserts that nothing else changes.  G0 / G0C on hm_r26q5: PASS 0 errors / 1851 W (CHECKED, own run).  The finding
diff vs the q4 G0C report is exactly -15 core_pin_form WARN (the qkd_hr edge faces) and +0 new findings.

(a) TASK 1: kit-level FT coupon GRT, 50-iteration cap, M4-M7, real q4 pins + stations + core OBS M4-M5
    tools/die_plan/ft_station_probe.py gains --iterations / --signal-max (partition ceiling M7, 12.1c/12.2).
    Runs in docker 8 cpu / 24 GB cap.  Logs are in grt/grt_summary.json.  All CHECKED (own runs).

    Overflow at die-abstract derate 0.75 on M4-M7 (die_trial method of record):

    | Type | Part | Overflow M4/M5/M6/M7 = total | Use % | Verdict |
    |---|---|---|---|---|
    | hub_Ei (control) | hub_Ei | 0 | 34.9 | PASS |
    | hub_Eo | hub_Eo | 0 | 18.8 | PASS |
    | hgi_v7 | hgi_WN_1 | 46/11/378/22 = 457 | 23.4 | FAIL |
    | hgi_v5 | hgi_EN_7 | 39/3/12156/12 = 12,210 | 25.7 | FAIL |
    | hgi_v8 | hgi_WN_7 | 871/1315/26162/960 = 29,308 | 33.9 | FAIL |
    | hub_Wi | hub_Wi | 2904/12527/69010/6787 = 91,228 | 44.5 | FAIL |

    At derate 0.4 (= the 0.6-track plan gate): all 6 reach overflow 0, with 0-1 extra iterations.  Use %: v5 9.9, v7 12.9,
    v8 16.5, Ei 13.9, Eo 7.75, Wi 12.0.

    Where the 0.75 failures sit (congestion.rpt windows + renders, VIEWED):
      v5 / v7: the hg->hgi FT entry band only.  This is the 1056-bit L2090_1 / L2158_1 lane in an 84.56-um window, i.e.
        12.5 bits/um on M4/M6.
      v8: two station clusters.  One is the W-mid channel crossing, with diagonal station runs: ft26_1/ft4_3/ft26_2/ft4_4/
        ft27_2.  The other is the N-mid station block on a core edge.
      hub_Wi: the S hr core band.  This is the phy_adp/phy_pad rows plus the cdc_ci/cdc_hi channels, where ft5_1..5 and
        ft4_6/7 cross the densely packed small cores.  It is a corridor problem: pin-window widening alone does not fix it.

    Caveat: the coupon routes FT nets only.  Partition-internal nets (e.g. the 1559-b i_ectl bus) are not modelled; the
    0.75 derate stands in for them.  Heatmap gcells >100 % also occur on the PASS control (heat_summary.json), so single-
    gcell hotspots do not discriminate.  The total overflow does: the control is 0 and four flagged types fail.
    -> NO pin-window widening in q5.  Which derate is the kit gate is an ASK to COORD.  If 0.75: a q6 FT re-site for
       v5/v7 (entry-window >= ~116 um + neighbour hg pins), v8 (station de-cluster) and hub_Wi (corridor out of the
       S hr core band).
    Renders: render/<part>_{a075,a04}.png (guide demand per gcell edge / raw tracks, overflow cyan).  Viewed: v5, v7,
    v8, hub_Wi and the hub_Ei control.

(b) TASK 3: ahub zh NUMBER-CHECK + early tap (D-KV-AHUB-ZH-TAP), q5_ahub.py
    NUMBER-CHECK (zh/sta*.tcl; OpenSTA, ASAP7 RVT NLDM, zh/recip .lib, kit clock RC 0.0214 kOhm/um / 0.1133 fF/um; M7
    bound 0.0125 / 0.0925), CHECKED own STA:
      From the q4 centre entry (302.4, 241.92) to the zh clk pins, the best 1-4x BUFx12f/16f/24 delivery is:
        TT 138.7 ps (zh1, 273.6 um) / 147.8 ps (zh0, 295.3 um)
        FF 120.2 / 127.8 ps
        M7 RC bound: TT 98.9-108.5, FF 86-92
      So zh arrives at TT +95..+144 vs 250 (FF +86..+128 vs 202.5).  CONFIRMED late; the q4 0.20 ps/um model was ~2.5x
      optimistic.
      recip on ck[0]: 1x BUFx12f, 75 um -> TT 268.7 (+18.7, inside +-20; q4 model said -10.7).
      Flag: the same 0.20 ps/um trunk model (kv_core_slice) is likely optimistic elsewhere.
    Fix: per the v5.0 early-tap rule (early_core_taps.py: a dedicated drop beside the actual macro clock pin), one
    12.2a1 in-core island per facing zh pair.  Both islands sit in the 21.6-um channel x 177.12..198.72, clear of the
    macros (+1.08 keep-off, asserted) and of the core_tree islands:
      ck[1] (S pair zh0/zh1): pin (190.056, 73.44) M5, island [185.76, 69.12, 194.4, 77.76]
      ck[2] (N pair zh2/zh3): pin (190.056, 410.4) M5, island [185.76, 406.08, 194.4, 414.72]
      The pin->zh stub is 14.5 / 10.2 um (BUFx12f): TT 6.4 / 4.5 ps, FF 6.3 / 4.5 ps.
      Tap insertion = zh signed + stub = TT 252.7 / FF 209.0 (+2.7 / +6.5: inside the band, no spine shift).
    Plan changes:
      kv3_hub_C gets taps ahub.ck[1] (406.056, 1118.88) and ahub.ck[2] (406.056, 1455.84), kind core, insertion
        252.7 / 209.0.
      Fixed a q4 defect: tap ahub.ck[0] kept the q3 y 1265.76 -> 1287.36 (it now follows the moved entry).
    Files: cores/qkd_ahub_pins_r26q5.json, cores/qkd_ahub_slice_r26q5.json (macro_entries; zh sinks fed_by).
    Note: the zh signed record is FLOW-PG-invalid (unbound PG), so the 246.3 ps zh insertion is historical, UNCHECKED.
    RTL obligation (KV-KITS-7 / KV-CORES): qkd_ahub ck [0:0] -> [2:0]; g_zh[0..1] on ck[1], g_zh[2..3] on ck[2].

(c) D-KV-HR-PIN-FORM (COORD 12:23), q5_hr.py
    All 15 qkd_hr_* pin files: 25,362 edge-form pins move 0.096 um inward to the centre form (per-face counts in
    q5_hr_report.json).
    qkd_hr_phy_pad: ck_phy[0] (43.224, 95.04 N edge) and rst_n[0] (71.112, 0 S edge) move to the interior centre entry
    at (43.224, 47.52) / (43.608, 47.52).  This is the host_qm form, M5.
    9 hub_Wi landed ck_phy tap xy follow the pins (phy_pad + 8 phy_adp, MX orientation applied).
    Outline: plan of record = 86.4 x 95.04 @ (77.76, 120.96), as approved in KV-CORE-SLICE-1 ASK-3.  The 138.24 x 129.6
    the HR triage saw is the pre-slice outline in a stale die_plan copy; it is not in hm_r26q4 / q5.  I kept the 86.4
    frame -> COORD please confirm.
    Render render/q5_cores.png VIEWED.

(d) D-KV-PG-G12 (COORD 12:35 one-grid ruling), q5_pg.py
    die.pg.grid changes from 0.48@8.64 on M8 and M9 to M8 0.48@4.32 (off 2.16) / M9 12.96@34.56 (off 17.28).  This is the
    HEAD-5 grid as in e5f4fb2cd1.  PHY domain grids are unchanged.  G0/G0C PASS.
    Clock mesh rebuild on G12 (R22 recipe, run_mesh.sh): FAIL, 256 plan errors.  Every kvs_pc mesh driver (kvpc0-3 x 64)
    finds "no canonical site within tolerance".  The PL control on hm_r26q5b with the same command builds rc 0.  CHECKED.
      ROOT CAUSE (arithmetic, CHECKED): the KV mesh M9 columns are xs = 583.2 + 319.68k.  319.68 mod 34.56 = 8.64, so
      the xs phases mod 34.56 are {30.24, 4.32, 12.96, 21.6}, 8 columns each.  Every one of the 32 columns lies inside
      a G12 M9 strap, 4.32 um from the strap centre (half-width 6.48).  The G12 gaps are only 4.32 um wide
      ([6.48, 10.8] and [23.76, 28.08] mod 34.56).  The mesh PG snap is 0.68 um, and the canonical kvs_pc islands pin
      the column x in the core frame.  No 4.32-lattice M9 pitch other than 4.32 / 8.64 / 159.84 / 319.68 divides
      319.68 (= 74 x 4.32).
    The canonical mesh (R25 bodies) combined with G12 (q5grt/combo_gen.log) gives:
      metal shorts 22,011 (pg-shield 11,354 to VDD, pg-tree 10,625, pg-strap 32)
      spacing 203
      vss_tied false
    The q2 PL combo has 0 shorts.
    Die GRT of that combo (TT, 48 GB): still iterating at 13:01, >= 3 extra iterations; q2 PL needed 1.  Not polled
    further.  Log: intel2:/srv/opentallas-scratch2/claude/kv-plan-q5-1027/q5grt/combo_TT.log.
    -> ASK COORD (measured failure, 12.x not edited):
       1) A KV G12 variant whose M9 gaps sit on the column phases.  Example: M9 pitch 8.64 with ~75 % metal leaves
          only 1.08-um gaps, too narrow for 4w + shields.  Or move the 32 mesh columns + 256 kvs_pc canonical islands
          onto G12 gaps, which is a kvs_pc core re-slice.
       2) A lighter KV grid that passes on the canonical deck (PG-ACTIVITY-2), commensurate with 319.68.  For example,
          M9 at a 159.84-um period with wide straps placed between columns.
       Until then, hm_r26q5b is the kit plan (core kits do not read die.pg.grid; partitions are PG <= M7).
