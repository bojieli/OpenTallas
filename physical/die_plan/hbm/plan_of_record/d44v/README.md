# HBM plan event d44v = the HBM RE-FORM batch plan event, part 1 (DIE-HBM-61/PLAN, 2026-11-03)

OWNER 11-03: TWO-STRIKES -> RE-FORM, ONE batch per die. Rules are design targets: plan GEOM, fill, aspect and channels
are ADVISORY. Only sign-off blocks.
DIE-HBM-61 ruling 06:5x: the >150k-cell cores go to DIE-HBM-61/SPLIT. The pin-bound and macro-channel cores go to
DIE-HBM-61/MEM. Their slots in this event are PLACEHOLDERS (unchanged), and their outlines and pins fold in when those
lanes post READY.

Base: DIE-HBM-60/PLAN v4. That is d44t + d44w (4fe0c55a9b5, on main) + d44u mu1-3sram, re-applied, + the FT S0 re-site
and nudge moves (ft_s0_resite --jog-sweep, ft_nudge clock halo; tools on this branch, f252174de86).
Sidecars are the d44t plan dir. Files that differ are in this dir; files over 200 kB are stored as .gz.
Builder: `results/die_hbm_1103/reform/build_d44v.sh WORK OUT`, steps in order:

1. **Templates (d)** `mk_tmpl.py`: the 10 per-hub `__sp_*__fx` vms_bank repins of v4 go back to their shared tables.
   That keeps the design count at 84 (DIE-HBM-61 ruling).
2. **RE-FORM slots (class 2)** `mk_reform.py`. This is a centre-kept resize via MASTER-PLAN-R6 hub_repack.run, using
   even 8.64 steps so origins stay on the 8.64 lattice. Each resize is accepted only when every one of these holds:
   - est fill <= 0.45 (target 0.40);
   - aspect <= 2;
   - each face >= pins/5 per um;
   - (W+H)/2 <= 220;
   - macro channels >= 10.8 um AND >= the pin count x 0.048/2;
   - the centre entry is not over a macro;
   - no parent station gains a register.

   Result: ot_hgi_qw_dec goes from 260x260 (fill 0.27) to 260x173.6 (fill 0.40, aspect 1.5). No station is regenerated.
   Left unchanged:
   - q2_hard_reduce: +1 register on 13 crossings;
   - subtree32: +1 on L43_o;
   - pc_ctrl_leaf_cfg_h9b: +1 on kr_data, and the odd-k form put origins off the lattice.
3. **Slot infra (a)** `mk_infra.py`: core_pg_connect: true (PG-CORECONN-2) on q_hub_ne, q_hub_nw and root, which carry
   35 + 35 + 3 placed hard-core macros.
4. **Centre clock-entry pins, LAST plan change**: tools/die_plan/clock_entry_pins.py (claude/die-hbm-60-centry-1103,
   on main). It covers 84 tables: 52 moved, 6 kept (the signed records).
5. Sidecars:
   - `reform_census.json`: per RE-FORM core, the class, the owner lane and the plan numbers.
   - `core_clock_regions.json` (OWNER: one clock entry per <= 5k sinks): 33 modules over 5k sinks get 239 regional
     entries over 576 slots. Kit/gen support for these entries is DIE-HBM-61/CLOCK. 35 modules have no sink data.
   - `ext/`: the (a)-(d) census and the ONE die crossing latency table, `crossing_latency.json`.

Proof: see the "Checks" section, appended by the builder run.

## Checks (epyc2 die-hbm-60-plan, same tools for every plan: this branch = main 08542fa9d7d + d44v tools)
- **G0+G0C** (`tools/die_plan/check.py --completeness`):
  - d44t: 74 ERROR / 128 pending-view.
  - d44v: **51 ERROR** / 128 pending-view. That is 27 gone and 4 new.
  - Of the 4 new, 3 are pre-existing items under a new message:
    - u_vmb_Q6/Q7_mu1 dq core_faces: the mu1s3 pin count changes 282 -> 281.
    - L701 reach: the hop index shifts, still 392 um.
  - The one real new item is the q_su00 lanes_plain__canon_663526 clock entry over a macro. It comes from the v4 sliver
    re-row and is listed for part 2.
  - The 8 core_faces vms_bank errors that the v4 per-hub repins had fixed are back, because of the template rule.
  - Diff: g0/g0_diff_d44t_d44v.txt.
- **Plan-time GEOM** (`tools/die_plan/plan_geom.py`, 74 types):
  - **new FAIL = 0**, gone 0. FAIL count is 225 -> 225 (advisory: every HBM type already fails clock_tap_sinks or
    clock_reach at d44t).
  - Values worse on already-failing rules: clock_tap_sinks on q_su11pv1 (5654 -> 6403), q_su31 (7073 -> 7798) and
    q_su20 (+1).
  - Values better: q_b101_nw (8491 -> 4821), q_b112, root and q_su30.
  - Diff: geom/geom_diff_d44t_d44v.txt.
- **Count** (release_tree_plan.plan_designs vs the d44c count POR): 84 -> 84 designs. The 6 signed cores keep their
  design key (qctl, tail_native x2, collar_idx256r, ring_ag, fused_tnode). See g0/count_check.txt.
- **Census (a)-(d)** (ext/census_summary.json):
  - (a) 76/81 types carry PG + clock tap + reset relays. The 5 missing PG are io/spb0/vsN0, all PHY-domain.
    379/1028 core slots are complete. Gaps: 133 reset relays, of which 128 are rp3lp3h in q_sm (SPLIT); 132 have no
    clock entry (hcol_h0/h1 merged view pending, tail_native kept). 576 slots are over 5k sinks; they are covered by
    core_clock_regions.json, which is declared but has no kit support yet.
  - (b) 203/357 die lanes are > 400 um and 195 are hop-compliant. 8 are not: L5/L5m, L34/L34m, L730/L730m and
    L6b/L6bm, with first FT hop 463-726 um. Type-internal stations > 400 um: 20,045, all hops <= 405. FT slots 520,
    0 over.
  - (c) ONE crossing latency table, ext/crossing_latency.json.gz: 21,100 crossings (357 die lanes = 4,013 cycles,
    20,743 internal = 91,789 regs) and 1,156 registered hard-core faces. Added plan cycles: 18. RTL/SPLIT/MEM hook: 0.
  - (d) 81 types, of which 12 near-duplicate pairs would cut 12 types. Hard cores: 74 modules, 106 designs,
    1,156 instances. Unifying variants would cut 32 designs.
