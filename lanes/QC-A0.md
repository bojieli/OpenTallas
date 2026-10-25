# QC-A0 (lane file)
Scope: re-kit Qwen compute A0 cores (qfd_tile_n{k,l}_a0*) + remaining non-clean G0C types on grid taps 400 um (+ sink additions), from bound_r8; G3 geometry + render review + P&R (ORFS ASAP7, 833 ps).
Hosts: intel2 (shared KV-G3), intel1 overflow (shared QC-TOK). Branch claude/qc-a0-1024 (worktree ~/wt/qc-a0), base origin/main 3e05af806b + merge qc-p6-a0v6-1023.

## Status
- 06:40 PDT: started; reading tools + a0v6 branch.
- 07:05 PDT RESUMED (new agent after coordinator restart). Previous agent left: v7 kits committed 41749ba80 + uncommitted
  clock-port-list fix; equiv bench builds running on intel1 (~/scratch/qc-a0-equiv: nk_asbound, nk_fp1, nl_asbound; pids 94057/111735, not mine to kill).
- 07:15 f41f0cb64 pushed: a0cv7 spec clock port lists (+6 taps), render_a0c7.py, equiv bench tools. Local pre_route_gate NK/NL WARN 0 fail.
  Render review (/tmp/qca0/a0c7_{nk,nl}.png): 6 grid taps 2x3, 9.1-9.5 um off hard children; OK.
- 07:20 A0 v7 routes RUNNING on intel2 via ot-run (16 thr, 64 GB each), launcher tools/qwen_romleaf/a0core/run_a0_route.sh
  (job.json route+collect cmds, loop env TC/mm/HM 0.03): NK intel2:/srv/opentallas-scratch2/claude/qc-a0/run_nk_v7 (src_nk),
  NL .../run_nl_v7 (src_nl); local ot-run logs ~/scratch/qc-a0/logs/a0_{nk,nl}_route.log.
  (first NK try failed: no ~/.local/opentallas-pdk-asap7 on new fleet; NLDM now present on intel1/intel2.)
- NEXT: G0C ft_budget fix (gen_plan negotiate with per-partition over-the-top budget), coll_ftc g3h on current tools.
- 07:35 A0 bound-vs-kit equivalence bench (prev agent's, intel1 ~/scratch/qc-a0-equiv, Verilator 5.050): nk_asbound / nk_fp1 /
  nl_asbound x {hard, aligned, mut1}: ALL A0EQ FAIL, 6300/6300 (NL 6150/6300) cycles mismatch at best shift d=-3, and the
  mutant is indistinguishable from the clean runs -> bench is not discriminating yet: equivalence NOT ESTABLISHED (record,
  not a PASS). Kit RTL = rc14/rc15 snapshot body (REGROOT_MODE 9, land32 matvec), bound = main rp2_romleaf_rr + rp2_45.
  OWNER?: A0 G3 "from bound RTL" -- either fix the bench until it proves kit == bound, or re-kit the A0 core on the bound
  module qfd_tile_n{k,l}_rp2_romleaf_rr (39/35 clock-entry ports; R4 taps need the entries tied as one clock).
- 07:40 G0C ft_budget: st_a/st_b over-the-top M9 is set by the slice-internal negotiation (gen_plan.negotiate), which
  priced face pins only. Added per-partition M8/M9 ft budget to the negotiation (+ optional lane split, QC_NEG_SPLIT).
  LP check (scipy HiGHS, fractional multi-commodity on the W5 slice): INFEASIBLE at face cap 5.1 pins/um with the fixed
  hw broadcast trees; feasible from 5.5 pins/um (G0 face rule 6/um), or with free broadcast paths, or ft fill 1.2.
- 07:55 merged main 4b7b2b3e64 (CP1-R10 gates) into claude/qc-a0-1024 dd3890c4a (tap_balance/clock_taps conflicts resolved on
  the OT_TAP_PORT family). A0 v7 ref_tile kits vs the new gates: sdc_lint/face_guard target die_plan partition kits
  (constraint.sdc + sdc_lint.json, ot_dp_st face cells); the A0 signoff.sdc (io_ref_skew form) already sets explicit
  -min input AND -min output delays on every port (out min = -L_min - 50 <= 0), so the "no set_output_delay -min" hold
  waiver does not apply to the A0 routes started 07:20 -> kept running; will report hold from signoff.sdc. COORD: say if
  you want them treated as pathfinding anyway. coll_ftc / st kits will be generated on main's gen_phys (gates in).

## TYPE-DEDUP proposal (2026-10-24 07:45 PDT, lane TYPE-DEDUP, tool on main 4a5c3620d8; plan NOT edited)
Evidence: results/type_dedup/qwen_compute_*.json.
- Plan level: 0 exact merges (56 -> 56, G0 PASS, G0C 4 unchanged). check.py's 20 "near-duplicate" types (sle_*/slw_*
  x9, phy_serdes/_b) are NOT the same netlist: east slices hold s6b slice glue / *_pstn wrappers, west slices s8
  (different as-built RTL), so they stay separate unless the slice RTL itself is unified.
- Bound level (bind/bound_r8): 56 plan types -> 80 bound modules, 21 types with variants. Classes: 14 narrowed-port only
  (sle/slw sc, su_c, su_l0/l1, stm, fe), 10 narrowed-port + other (chain-end variants: dropped ft slot / *_nb0 tails,
  e.g. slw_st_b_v1), 5 pads + ports, 1 pads, 2 params (cbf_q0x_s2), 1 identical (phy_serdes_b bound == phy_serdes).
  Proposal: (a) narrowed ports come from tapered/chain-end bit use; bind at full plan width with a rotating encoding
  (as proven for KV cN) so no bit is constant -> one module per type; (b) chain ends: close the chain with a planned
  return lane + a config-register "end" bit (R7-clean) or keep the nb0 variant (price: lane bits x length vs one kit).
  Each needs your RTL/lockstep ownership; I can build the per-type miter for a pick.

- 2026-10-24 07:53 PDT FROM ELEM-QK: I propose to run G3 kits for the types listed in lanes/ELEM-QK.md "PROPOSED ELEM-QK list" (QC: tt_ctlm, native59, glue, coll_* except coll_ftc, slice types w/o hard cores except st_a/st_b | KV: sys_c, sys_SD*, io_cor*, io_ft*, hroot). Object here if you already run any of them.
- 08:40 ROOT-MERGE finding (a0v6 core-tap hook put 404 taps outside SU outlines) FIXED in my tree (not yet committed):
  a0_core_taps.declare now only touches qfd_tile_n{k,l}_a0c* hard cores (SU lane/su_c cores keep their <inst>.ck taps);
  inputs/a0_core_taps.json = A0 v7 pin table (NK 38 / NL 37 = 6 grid + v6 additions). Regen + G0 pending (with G0C fix).
- G0C fix status: negotiation with ft budgets + lane split (800 b) + face cap 5.7 pins/um (G0 rule 6, PIN_MAX 5.8) + the
  E slices' l9 lane reserved: W5 LP feasible from 5.5/um, E0 (with l9) from 5.7/um. Earlier candidates: G0 PASS / G0C
  55/56 (l9 lane routed after the negotiation pushed sle_sc M8 / sle_su_l1 M9 over). Runs scr7_* in progress.
  COST to report: split lanes take 3-4 hop detours (e.g. x_fw_ctl_p1 fw->su_l1->sc->ctl) -> more stations/latency; and
  the plan change invalidates bound_r8 (QC-TOK uses it) -> rebind needed before G3 of the st types from bound RTL. OWNER?

## GEOM-REVIEW findings (2026-10-24 08:55 PDT, independent die-level review, batch 1)
- Qwen compute P6 plan 0028ad53 (main): PASS-CONDITIONAL (record qwen_compute_plan__qc_p6__0028ad5329ca.json). G0C 4 = ft_budget st_a/st_b (yours). New: 252 interpolated column ft station points land inside A0 cores (cbn_q01 96, cbn_q00 48, cbf_q01 46, cbf_*_s2 26, sl*_su_c/su_l1 36) -> declare regs_um in the inter-core channels and re-run hops. Hottest spots: E/W ends of the slice band (sl_E5_*, 5.6 kb/100 um) and coll_f4|sl_W5_fw seam (5.4 b/um): their kits need a GRT congestion picture in review. Lever: ~18 mm2 hatched voids on the W edge. A0 v7 NK/NL tile review running (GR-QK).
- 2026-10-24 09:05 GEOM-REVIEW tile (A0 v7 NK/NL at 3_place, records qfd_tile_n{k,l}_a0c__run_n{k,l}_v7__*.json, images localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-QK/qc_n{k,l}/): PASS-CONDITIONAL. 10 ROM leaves 2x5 facing a 67-um central channel, pins = plan a0_nk_pins.json, pin->reg p90 12.6 um. Conditions: (1) channel walls / 35-um LSL gap / 30-um node gap at 0.8-0.98 density -> show GRT overflow before DRT verdict; (2) clock contract mismatch: kit has 38/37 interior M7 tap drops, plan has one E-face M4 ck and the 6 R4 grid taps sit over macros with 0-2 sinks (dead); NL ck_t12 1,792 sinks over cap; per-tap pre-balance latency up to 385 ps -> put the real tap contract in the plan (hard_cores clock taps) or fix the kit; (3) routes are pathfinding only: no G3 credit until kit==bound equivalence is shown or the core is re-kitted on the bound module (your OWNER?).

## CODEX notes
- Route jobs NK/NL still live in intel2 scratch2 run_n{k,l}_v7; no final verdict. Plan/generator mismatch fix exists only uncommitted in paused lane tree, must reproduce in own branch. A0 equivalence remains FAIL/non-discriminating; G3 credit blocked. Next reproduce tap-hook scope correction, G0/G0C and inspect negotiation candidates.

- CODEX took over generator mismatch on codex/qc-a0-1024, pushed29f8521812. A0-only tap hook+committed v7 NK38/NL37 clock input; regenerated G0PASS0errors88warn,G0C52/56. Image reviewed results/geom_review/codex_qc_a0_v7_tap_scope_1024.json. A0 equivalence still blocked; no G3credit and not merged (branch includes paused A0 WIP).

- CODEX: capacity generator candidate clears G0C56/56/G0PASS0errors;114changed existing lane cycles and192new split lanes are recorded in results/uarch/qwen_capacity_1024.json. Render reviewed. Not adopted: R8/rebind schedule integration required.

- CODEX correction: provisional93,658R8flops used noncanonical type/leaf settings; excluded from adoption. Regenerating canonical all-replica/part-bus table; all597broadcastrelations retained.

- CODEX canonical capacity R8 all/part preserves597replicas but costs433,915pads vs248,396P6, above150k target. Largest regression: front-end landing+9696flops per12slices. Candidate therefore stays unadopted; cost/capacity tradeoff needs same-depth paths for split widebuses. Zero-error probe connectivity is valid.

- CODEX NL fullshape trace now matches NK:2560/2560 validROMwords exactly at+7cycles,6308neighbor edges exactat0shift; x/tapbit mutant creates2560mismatches. Existing samecycleFAIL preserved; +7ROM(+6priced+1residual),0neighbor must be integrated beforeG3.

- CODEX capacityhop10000/split1024 failed negotiation earlyE0 (face/FT1.001..1.013over); retainedlog. Nextsamehop/split800 running, no budgetrelaxation. Canonical candidatebind0errors across1933crossings/792661bits/78types, but433915padflops andtype-splitphysicalviews remainunclosed.

CODEX progress: Capacity56 candidate nowregenerated25/25constantsPASS,433915padflops/114lanechangespriced. XT1lead16 bothcluster actualboundsmokeLIVE intel2:/srv/opentallas-scratch2/claude/codex-qwen/xt1_capacity_both16_v2 (96GB24t); 66-type alternativeparked.

## RESUMED 12:15 PDT (after the 08:50-12:04 usage limit; Codex covered QC-A0)
- adopted: codex/qc-a0-1024 29f8521812 (A0-only v7 tap hook; same fix as my 08:40 WIP) cherry-picked code+input only
  (a3b97aac0a); Codex A0 shifted-equivalence receipts e1ca8cc6b6 / 801293dbae / fc50d1fecb cherry-picked (A0 NK/NL ROM
  stream exact at +7 cycles, neighbour path exact at 0; +6 priced +1 residual must be integrated before G3 credit).
  Merged main 24b2da3433 into claude/qc-a0-1024 (79a31b52ef; tap_balance conflict -> main's clock_family + OT_TAP_PORT).
- my 08:xx G0C negotiation WIP is PARKED (~/scratch/qc-a0/park/wip_1208.patch): Codex's capacity candidate
  (codex/qc-capacity-1024 406d3a497a, same approach) already reaches G0C 56/56 G0 PASS but costs 433,915 pad flops vs
  248,396 (P6) -> owner trade-off, not adopted. OWNER?: accept the capacity cost, or keep G0C 52/56 (4 st_a/st_b ft_budget).
- my face_guard 1-station edit DROPPED (main 55945950da does the same).
- Live jobs (mine): A0 v7 routes intel2 run_{nk,nl}_v7 at 5_1_grt congestion iterations (NK 9/30, NL 6/30 at 12:09):
  pathfinding only (GEOM-REVIEW cond. 3); will report GRT overflow (cond. 1). Codex live jobs for QC-A0: none
  (xt1_capacity_both16_v2 belongs to QC-TOK).
- coll_ftc g3h (kit on old bound_r8): FACE_GUARD FAIL (dropped 8 / shared 8 = bound_r8 narrow buses crec_tx_s0 548<549,
  flte unbound, fltv 12<17; merged 1026 = 1-station pairing, fixed on main). Failed verdict kept (intel2
  /srv/opentallas-scratch2/claude/qc-a0/g3/ftc_g3h). Re-kit on P6 full bind qcp6_status_bind_v5 next.
- GEOM-REVIEW batch-1 item (252 interpolated stations on cores): NEW physical/die_plan/qwen_compute/ft_regs.py, called by
  gen_plan before writing: declares regs_um for every hard-core-type ft slot with a station inside a core (+8.64 halo,
  2.16 last resort): 29 slots / 51 stations moved, all hops <= 750 (tightest cbf_q00_s2 serdes 746-749). Regen running.
- 2026-10-24 12:24 PDT FROM ELEM-QK (QC plan owner please): native59 G3 kit (bound = Codex qcp6_status_bind_v5 on main plan) FAILS
  face_guard 'shared' on flt_o: the plan carries the native59 fault TWICE - lane 'fltn' (native59.flt_o -> glue.n59_flt_i,
  gen_plan.py:1171, the old 1-b fault-OR tree lane) AND 'native59__fault_native_fault' (bus 'fault' -> glue
  sys_face__native_fault, the P6-R8 per-bit as-built lane). Bind binds the leaf to 'fault', so flt_o is a spare lane tied
  to 0 (not allowed). Proposed fix: drop the fltn link (and n59_flt_i on glue) from gen_plan, regen plan + rebind. Check
  fltt/fltc for the same duplication (tt_ctlm passes face_guard, so fltt is bound there). OWNER? if you prefer otherwise.
- 13:25 ab490d1fbb pushed (claude/qc-a0-1024): ft_regs.py = GEOM-REVIEW batch-1 fix on ROUTED hops (8.64-um grid, cores
  blocked: A0/SU cores route to M7): 51 in-core stations + 23 over-limit routed hops found; 31 slots now have regs_um in
  channels; picture results/geom_review/qc_a0_1024/ft_regs2.png, record qwen_compute_plan_ft_regs__*.json (PASS-COND).
  Lanes/ports identical to main; coll_ftc = grid+sinks taps; A0 v7 core taps.
  OWNER?/COORD: 6 serdes TX slots (cbf_q00_s2/cbf_q01_s2: tx_flit 597 b, tx_valid, tx_up) need 5 stations (routed hops
  734-804 um with 4; Manhattan/G0 OK) -> bound RTL (qcp6_status_bind_v5 bakes 4 stations) + R8 + latency change.
  COORD: main 24b2da3433 itself FAILS G0: "R8 landing table ... made from other bus groups (digest e56a2f6f7e7e9337 !=
  c56f7e7abff4cabb)" -- codex 90907cf3b1 (P6 bind recovery) regenerated r8/qwen_compute_r8_landing.json from bus groups
  that are not committed (no codex-qwen bus_groups*.json has digest e56a...). Not mine to regenerate (would replace the
  P6 R8 table). My branch has the same single error; I will not merge until COORD/QC-TOK says which bus_groups is canonical.
- 13:40 coll_ftc g3i RUNNING intel2:/srv/opentallas-scratch2/claude/qc-a0/g3/ftc_g3i (ot-run 48 GB / 16 thr; log
  ~/scratch/qc-a0/logs/ftc_g3i_route.log): kit on ab490d1fbb plan + P6 full-bind kit RTL (qcp6_status_bind_v5) with
  bind.py kit-rtl spare-ft-bit stations (24f94f8d3b); sdc_lint PASS; FACE_GUARD PASS 10216/10216 (513 1-station pairs).
  Review record qc_coll_ftc_g3i__5e60cbccf5237032.json (PASS-COND: GRT congestion map must be reviewed).
- A0 v7 routes: still in GRT congestion iterations (NK 14/30, NL 11/30 at 13:05) -> heavy congestion signal (GEOM-REVIEW
  cond. 1); pathfinding only.
- OWNER? (open, 13:45): (a) A0 G3 credit: kit (FP1 REGROOT_MODE9) = bound +7 cycles on t_out (spec prices +6, residual
  +1; codex receipts results/rtl/qwen_a0_shifted_1024) -> adopt kit + price +1 in compiler/R8 (QC-TOK), or re-kit A0 on
  the bound module. (b) G0C 56/56 = codex capacity candidate (+185k pad flops) or stay 52/56. (c) +1 station on the 6
  cbf_q0x_s2 serdes TX slots (routed hops 734-804 um). (d) main's R8 landing digest (G0 FAIL on main) -> blocks my merge.
- NEXT: collect ftc_g3i (GRT congestion map review, then TT setup / FF hold via signoff.py), A0 v7 GRT overflow + images.

## 19:1x OWNER RULING received (capacity plan accepted; +1 serdes stations in the same rebind; A0 +1 priced; reset rule)
- Capacity plan adopted on claude/qc-a0-1024: cherry-picked codex 406d3a497a / 72ece79138 / f553f73d91 (7938b61ac7,
  027930db3d, ec45162186) on top of ft_regs; ft_regs now adds stations where routed hops cannot meet the limit (6 serdes TX
  slots 4 -> 5, routed hops 570-648). Regen running (~/scratch/qc-a0/logs/regen_cap_1900.log). Asked QC-TOK (their lane
  file) for the canonical bus_groups + R8/CB16 landing recipe and the rebind on this plan; A0 +1 pricing is theirs too.
- RESET RULE: coll_ftc g3i (and every gen_rtl kit with > 1 tap) still has one reset synchroniser PER TAP -> not compliant.
  Waiting for the shared gen_rtl/gen_phys implementation (KV-G3 proposed option (b)); COORD: who owns it? I regenerate my
  kits when it lands.
- coll_ftc g3i RESULT (intel2 .../g3/ftc_g3i, signoff.py): NOT SIGNED. TT setup -126.95 ps (2670 endpoints), FF hold -4.40
  (132), DRV slew 4165 TT / 3675 FF; spread TT 45.5 / FF 38.3 (PASS), insertion TT 214-260 mean 246; DRC 0, antenna 0;
  sdc_lint + face_guard PASS. Worst path = ft station hop crec_rx_s0 s0 -> s1 (N face -> (60,458), ~580 um): 884 ps of data
  incl. one 240-ps wire segment and an INVx1 at 306 ps slew. Images /tmp/qca0/g3i/*.png (congestion: hotspots at the E->S
  control fan and mid-left).
  ROOT CAUSE (flow vs plan): the plan budgets ft hops OVER THE TOP on M8/M9 (die_use ft_reserved, ft_budget, reach M8 1001 /
  M9 1013, stations every <= 750 um), but the partition kit routes everything on M2-M7 (MAX_ROUTING_LAYER M7; M4-M7 reach
  405 um). OpenROAD here has no per-net layer range (only set_routing_layers -signal/-clock). COORD decision (affects every
  ft kit on all dies): (a) ft kits route to M9 with M8/M9 global adjustment = 1 - cut_avail (die PG/spine share), or
  (b) stations every <= 405 um inside partitions (more stations -> more R8 pads / latency), or (c) die-level ft routing.
  Failed verdict kept; no follow-up route until decided.

## PARKED 19:06 PDT
- Branch claude/qc-a0-1024 @0850852fc0 (pushed). NOT merged: it carries the WIP capacity plan whose G0 has 66 [r8] errors
  (stale committed bus_groups/landing). Gated parts on it: bind.py kit-rtl spare-ft-bit stations 24f94f8d3b (test_bind 26
  pass), ft_regs.py, tap_balance merge with main.
- Live jobs (keep running, collect): A0 v7 routes via ot-run on localhost pids 426433 (NK) / 429620 (NL) ->
  intel2:/srv/opentallas-scratch2/claude/qc-a0/run_{nk,nl}_v7 (still in 5_1 GRT congestion iterations, NK 21/30, NL 10/30
  at 19:06 = heavy congestion; pathfinding only, no G3 credit). Logs ~/scratch/qc-a0/logs/a0_{nk,nl}_route.log.
- Results: plan (capacity + ft_regs + 5-station serdes TX + grid+sinks coll_ftc + A0 v7 taps): G0C 56/56, G0 FAIL 66 [r8]
  only. coll_ftc g3i: NOT SIGNED (TT setup -126.95, FF hold -4.40, slew 4165/3675; spread 45.5/38.3 PASS; DRC 0) -- root
  cause: kit routes ft hops on M2-M7 (reach 405) while the plan budgets them over the top on M8/M9 (stations <= 750 um).
  coll_ftc g3h (bound_r8): face_guard FAIL (kept). A0 equivalence: kit = bound +7 cycles on t_out (codex receipts).
- NEXT: (1) QC-TOK names canonical bus_groups + R8/CB16 landing; rebind on 0850852fc0's plan (serdes 5 stations included),
  gen.py latency --groups, G0 PASS, commit, merge. (2) A0 +1 cycle priced in compiler/R8 (QC-TOK). (3) G3 kits sle/slw
  st_a/st_b from the rebind (kit-rtl + gen.py phys), after (4) the reset-rule tooling lands and (5) COORD decides the ft
  routing-layer question; review images before routing. (6) collect A0 GRT overflow + images.
- OWNER?/COORD: ft hop layers in partition kits (M8/M9 allowed in ft kits vs stations every <= 405 um vs die-level ft
  routing); owner of the reset-rule implementation in gen_rtl/gen_phys; canonical QC bus_groups (main itself FAILS G0 R8).

## QC (steward: QC-A0 + ELEM-QK + TRIAL-QK + QC-TOK plan side) -- started 2026-10-24 19:33 PDT
- 2026-10-24 19:33 PDT QC: worktree epyc1:/srv/opentallas-scratch/claude/wt/qc-1024r (branch claude/qc-g0fix-1024 from origin/main d13ff7c78).
- 2026-10-24 19:33 PDT QC: MAIN G0 FIX READY: claude/qc-g0fix-1024@9aceac11be. Canonical bus groups for main's P6 status plan =
  codex-qwen/qcp6_status_bind_v5/bus_groups.json (digest f4f98b2b102ed56f; the bind of that plan, 0 errors, verify PASS).
  e56a2f6f matches no bus_groups file on any of the 5 hosts (searched). With v5 groups the committed table gives ONLY the
  digest error; gen.py latency --groups v5 reproduces it: same 7720 members / 248,396 pad flops / max pad 5; only 4
  members' lane label UNPLANNED -> coll_ucie__fltu. Committed as r8/bus_groups.json + regenerated landing + r8 latency/pkg.
  G0 PASS 0 errors / 88 warn, G0C 52/56 (unchanged; capacity plan next).
- 2026-10-24 19:41 PDT QC: capacity adoption branch claude/qc-cap-1024r (epyc1 worktree qc-1024r) = g0fix 9aceac11be + merge claude/qc-a0-1024@0850852fc0
  (codex capacity 406d/72ec/f553 + ft_regs ab490d1fbb + 5-station serdes TX + A0 v7 taps). NEW physical/die_plan/qwen_compute/lane_eq.py
  (QC-TOK equalisation proposal, generic): every lane family into one hardened type (dst type+bus) gets one natural depth, short lanes
  padded with ft STATIONS on slots whose every lane has the same deficit (CB families left to CB16 pads). Only unequal family on the
  capacity plan: sle_ctl.x_fw_p1_i (E 9 / W 6) -> slw_stm.x_fw_ctl_p1 2->4, slw_sc.x_fw_ctl_p1 2->3 (6 W slices). Wired into gen_plan
  before/after ft_regs. Regen running epyc1 pid 3512489 (log /srv/opentallas-scratch/claude/qc/logs/regen_cap.log); R8 groups =
  codex-qwen/qcp_capacity_probe/bus_groups.json (5b3a39e809083115) until the rebind.
- 2026-10-24 19:41 PDT QC: A0 +1 PRICED: results/uarch/qwen_a0_latency_compat_1024.json -> ADOPTED: +1 cycle x 4 serial matvecs (qkv/o/gu/down) x 36
  layers + lm_head = +145 cyc/token on 271,106 = 0.053 % (4,428.1 -> 4,425.7 tok/s 1u). Compiler/R8 integration in the rebind.
- 2026-10-24 19:41 PDT QC: sub-agents: (a) A0 v7 NK/NL congestion structural review (no new P&R), (b) TRIAL-QK v3.8s route/IR collection + die_trial
  gate fix (owner decision 5: FF hold STA with real trees decides; insertion_tol 40 = guidance/INFO).
- TRIAL-QK OWNER? ANSWERED (BRIEFING decision 5): FF hold STA with real trees decides; insertion_tol is guidance.
- 2026-10-24 19:56 PDT QC: A0 v7 NK/NL routes COLLECTED -> FAIL (GRT non-convergent: NDR-relax loop, total overflow NK 1747 -> 2771, NL 5920 -> 7547
  rising; ~8 min/iteration since 09:38). Stopped by exact container (intel2 gracious_fermi / interesting_heyrovsky), run data +
  86 GB src copies deleted; logs+congestion reports kept intel2:/srv/opentallas-scratch2/claude/qc-a0/keep_a0v7_{nk,nl}.
  Structural cause (analysis epyc1:/srv/opentallas-scratch2/claude/qc/a0cong/a0cv7_congestion_review.md + PNGs): overflow over/between
  the 8 LSL heads (not the ROM channel): per-head 4-slot ring storage (512+512 b + 600 b ring) crosses the head columns from central
  writers to readers at the head faces: demand 3.0-3.8k nets vs ~3.4k H tracks (0.9-1.1 vs 0.6); regions 'tx' patterns miss flattened
  names (1,024 rung-0 flops land in the catch-all hub box); 4-um seam between writer and hub boxes piles 6,879 flops.
  FIX F1 (same outline, 0 cycles, no RTL): readers + rung-0 next to the writers, per-head tap, only 390-b rung-1 + 73-b result cross
  (cut ratios <= 0.5). Fallback F2: core +69 um tall -> CB quad +5.3 % (plan change). A0 v8 (F1) kit + render + self-review being
  built (sub-agent, branch claude/qc-a0v8-1024); GEOM-REVIEW independent review before any P&R.
- 2026-10-24 19:56 PDT QC: lane scratch moved to epyc1:/srv/opentallas-scratch2/claude/qc (root 89%; symlink left). Capacity-plan probe binds running
  (ot-run epyc1): bind_cap_ref (codex plan 72ece79138, expect groups 5b3a) + bind_cap_probe (new plan incl. lane_eq/ft_regs/serdes).
  FINDING: R8 type check uses BOUND stages from the bind's bus groups, so plan stations only clear the sle_ctl R8 error after
  the probe rebind on the new plan (G0 with old probe groups still 1 error, as expected).
- 2026-10-24 20:02 PDT QC: CAPACITY PLAN READY: claude/qc-cap-1024r@78992be86f (on g0fix 9aceac11be + qc-a0 0850852fc0): G0 PASS 0 err / 85 warn,
  G0C 56/56; canonical R8 bus groups = probe bind of THIS plan (epyc1:/srv/opentallas-scratch2/claude/qc/bind_cap_probe, 0 errors,
  digest f23550b066045561; method check: same bind of codex 72ece79138 reproduces 5b3a exactly); R8 table 7898 members, 424,864 pads,
  max pad 8 (before CB16). lane_eq W x_fw_ctl_p1 +3 stations; serdes TX 5 stations; ft_regs. pytest test_r8+test_g2+test_bind PASS.
  Self-review results/geom_review/qc_cap_1024/ PASS-COND (plan sha 4b445d10a0a3912c). merge-tree vs origin/main CLEAN, 0 deletions.
2026-10-24 20:15 PDT ROOT-MERGE: PRE-CHECK (no approval yet) claude/qc-cap-1024r@78992be86f: tools/die_plan pytest FAILS test_cp2.py::test_tcl_hooks_complete (line 283 asserts '^clk(_t[0-9]+|_c[0-9]+)?$' in tap_balance.tcl; the branch's tap_balance.tcl (OT_TAP_PORT family from qc-a0) no longer contains it; main and every other READY tip pass). Fix the test or the tcl, rerun the FULL tools/die_plan pytest, re-post READY. Other READY tips (geom-review@bb60cdada2, elem-s81-st405@2cb4732766, s81-kits-geom@35b3b97ba, cp1-r10@f5c549e166, hbm-1024r@9ef5eebb2, tok-ds-pads@e7d749213) test-merge cleanly together on main d13ff7c78, 0 deletions, G0 5/5 0 err. qc-g0fix@9aceac11be alone: all pass.
- 2026-10-24 20:16 PDT QC: final CB16 bind of 78992be86f: 1 error (coll_regen RX2: io_serdes_2 -> coll face[4] legs land at 10 vs 12: the owner +1
  station on cbf_q0x_s2 tx_up_serdes_up made the 1-b up-status leg 2 cycles longer than rx_flit/rx_v). READY withdrawn. lane_eq now also
  equalises PHY bundles (lanes between one PHY partition and one partition): cbf_q0{0,1}_s2 rx_flit_serdes_rx + rx_v 4 -> 5
  (+1,196 station flops, serdes_2 RX +2 cycles, priced by coll_regen). Pipeline running epyc1 pid 2969446 (pipe.sh: regen -> probe bind
  -> R8 groups/table -> G0 -> CB16 pads -> final bind -> verify; logs /srv/opentallas-scratch2/claude/qc/logs/pipe*.log).
- 2026-10-24 21:00 PDT QC: A0 v8 (F1) kits built: claude/qc-a0v8-1024@39e12308a8 (same outline/pins/RTL body/cycles; hub co-location of ring writers +
  readers incl. 1,024 flattened g_tx9.tc[] flops; E heads mirrored MY so faces look into the 35-um channel; +4 hub taps (load-less
  ports OT_A0_CK_TAPS42/41), a0_core_taps.json -> v8). Cut ratios head columns 1.41-1.65 -> 0.16-0.49. Self-review PASS-COND; GEOM-REVIEW
  independent review REQUESTED (lanes/GEOM-REVIEW.md). Plan regen with v8 taps after review.

## CODEX notes 2026-10-24 21:10 PDT takeover
CODEX took over: capacity PHY-bundle equalisation and final CB16 integration on codex/qc-cap-1024 (epyc1 scratch2 worktree). Paused pipeline collected: G0C PASS 56/56 (0 errors), probe bind PASS 0 errors, final CB16 bind PASS 0 errors; R8 424,267 + CB16 789,504 pads. Verify remains live epyc1 PID3298387, run /srv/opentallas-scratch2/claude/qc/bind_eq_cb16; not duplicated. Prior READY withdrawal remains until gate completes. A0v8 successor independent review allows PLACE ONLY; placed geometry and >405-um reader legs must pass before CTS/GRT. A0 worker owns next placement, trial worker collects QC IR/GRT.

## FROM TOK-QK 2026-10-24 21:14 PDT -- RTL defect for lane QC: S8-SU-PROG-ALIGN (blocks the Qwen token pass on the bound compute die)
- qfd_dv_s8_suvm_rp1 (bound_r8 partitions qfd_qc_sl{w,e}_su_c*, inst u_u_suvm, all 12 slices) starts the closed SU qfd_dv_s5_su8_rst3
  and requests the program word on the same edge; SU latches it 5 edges after the command, the word arrives 8 edges after
  (vm8q_rp1 -> qfd_dv_s8x_prog) -> zero rows latched, SU busy forever, no fault -> bound-row stg_die FAIL 0/259.
  Evidence: claude/tok-qw-1024 @81640ddb6c results/rtl/tokqw_1024/stages/stg_die/ (what-if +3 edge start: bit-exact psums).
- TOK-QK sub-agent is preparing the retime fix + proof on claude/tok-qk-s8a-1024 for you to merge into the compute RTL/rebind and
  re-close the partitions holding u_u_suvm; tell TOK-QK (lanes/TOK-QW.md) if QC prefers to own the RTL change itself.
- Also pending for the capacity rebind: QC-R1 (F1 u_d2d_rom TXDP 32'h0a010308), QC-R2 (F7 ovl_rope pair dc11eabc33), QC-R3 (F5 p192
  macro) -- details lanes/KV-TOK.md "REQUESTS from TOK-QK to lane QC". Send me the bind dir when it lands (xt1 both re-run).
- 2026-10-24 21:15 PDT QC: CAPACITY PLAN READY (again): claude/qc-cap-1024r@806bcb4058 (plan sha d5114a62f9a26612). Final bind with R8 + re-derived CB16 pads:
  0 errors, verify PASS 2,723,870 matched / 0 mismatched / lint 0 (epyc1:/srv/opentallas-scratch2/claude/qc/bind_eq_cb16; recipe
  bind/asbuilt_capacity_eq_cb16.json). R8 pads 424,267 + CB16 789,504. Sub-agent running xt1 both lead-from-constants + mutant + schedule
  gate on this bind (branch claude/qc-tok-cap-eq-1024). ELEM-QK G3 re-kits of QC types can now use bind_eq_cb16 kit-rtl (blocked
  on reset-rule tooling from the RESET lane + COORD ft-layer decision for ft kits).
- 2026-10-24 21:16 PDT QC (ELEM-QK): QC tt_ctlm g3qc3 route (bound v5 = P6 plan, pathfinding) COLLECTED -> FAIL: GRT non-convergent (NDR-relax loop, 18 NDR
  drops, ~9.4-11.5k overflow per report at 5/10/15/20, not falling). Stopped (epyc3 container dpkit-tt_ctlm-440715), run data deleted,
  logs/reports kept epyc3:/srv/opentallas-scratch/claude/elem-qk/keep_tt_ctlm_g3qc3. Needs a structural congestion review on the
  capacity-plan re-kit before any new route (same review method as A0 v7).
- 2026-10-24 21:25 PDT QC: RESUMED after account switch (COORD priorities 1-5). Live: xt1 both re-run on bind_eq_cb16 (sub-agent; ot-run epyc3 dir
  /srv/opentallas-scratch2/claude/qc-tok-capeq/xt1_both); TRIAL-QK capacity die trial (sub-agent; GRT epyc1 dir trial-qk/qc_cap_4b445d*,
  IR epyc3 qc_cap_4b445d_ir_t4); full tools/die_plan pytest incl test_cp2 on 806bcb4058 (epyc1 pid 2607821, log
  /srv/opentallas-scratch2/claude/qc/logs/pytest_806.log). NEW sub-agent: first QC signoff kits (sle_hc3, coll_n, coll_s, sle_hc1/2) on
  bind_eq_cb16 + claude/reset-1024 reset rule -> branch claude/qc-g3-1024; route only after GEOM-REVIEW PASS.
  S8-SU-PROG-ALIGN: TOK-QK's fix sub-agent (claude/tok-qk-s8a-1024) is on the RTL retime; QC reviews the design fix (prefer re-timing the
  PROG read so the word meets su8's accept edge over adding +3 start cycles if the cmd is known early) and owns merge/re-close.
- 2026-10-24 21:33 PDT QC: APPROVED-IF met -> READY claude/qc-cap-1024r@2f67b44ad1 (merged main a11334b988; pytest: only main's own 3 failures; test_cp2
  fixed (tap_balance kept the literal default clk regex); G0 PASS / G0C 56/56).
- 2026-10-24 21:33 PDT QC: S8-SU-PROG-ALIGN design review of claude/tok-qk-s8a-1024@dd2d80455 (start relayed 3 edges behind the PROG read): ACCEPT as the
  closure fix (su8 / vm8q untouched, +3 edges per SU op priced in calibrated SU ages). Zero-cost alternative for later: compiler issues a
  PROG prefetch 3 edges before the SU start (split su_cmd into fetch + start) -- needs producer RTL + compiler, not now.
  Re-close: when it lands on main, QC re-elaborates the as-built + rebinds (pipe.sh, ~1.5 h) so su_c kits/bound tops carry it.
- 2026-10-24 21:33 PDT QC: OWNER DECISION 12 (ft <= M7, stations <= 405 um) invalidates the plan's 750-um ft station budget: QC re-plan next
  (budgets.ft_station_max_um 405 -> ft_regs/lane_eq add stations -> probe rebind -> R8/CB16 -> final bind). Decision 13 (reset wavefront):
  kits adopt the RESET lane's tool mode when ready.
- 2026-10-24 21:58 PDT QC: first-signoff kit attempt (claude/qc-g3-1024@b41694c94b = cap plan + claude/reset-1024 tip): NO kit ready for GEOM-REVIEW.
  sle_hc3 kit (epyc1:/srv/opentallas-scratch2/claude/qc/g3/kits/sle_hc3): sdc_lint PASS, face_guard FAIL 2620/2640 (b_hw_i plan 1592 vs
  as-built 1574 -> 18 dead bits; flt_o[1:0] no as-built driver -> tied 0), synth 255k cells (not 15k), S->N 516-bit path has no internal
  station (>=540 um hop > 405), pins crowded in W 45% of S/N faces; self-review FAIL (results/geom_review/sle_hc3__qc_g3_1024__1f8f02693185.json).
  coll_n/coll_s not kittable: extra clocks clk_coll/clk_serdes without plan clocks + unhardened qfd_coll_static_face core (~116k, SRAM).
  -> plan fixes queued for the decision-12 re-plan: b_hw_i width = as-built, drop/bind sle_hc3 flt_o lane, internal station on cw_n3,
  spread S/N windows; reset re-kit on the decision-13 wavefront mode; remove leaf 2-flop sync in qfd_dv_s5_xhead3 (12x ot_rst_relay).
- 2026-10-24 21:58 PDT QC: decision-12 re-plan on claude/qc-ft405-1024 (epyc1 wt /srv/opentallas-scratch2/claude/wt/qc-ft405): ST_LEN 750->405,
  budgets.ft_station_max_um 405, M8/M9 ft_reserved dropped. Pass 1: 194 R3 station errors (station count off by one vs check.py's
  route/stations convention) -> pass 2 running (epyc1 pid 408360, log qc/logs/regen_ft405b.log).
- 2026-10-24 22:19 PDT QC: (1) OWNER REVERT CONDITION MET (no revert): xt1 BOTH clusters on the final capacity bind bind_eq_cb16 = PASS -- nominal near
  64/64, far 64/64 (QKV/O/GU/down exact); hr+1 mutant numerically 64/64 but caught by the timing-aware schedule gate on all 16 consumer
  edges (gate PASS). Constants regen 22/22 OK, XT1_FILL_LEAD_OFFSET 8 (lead 16) read from constants. Build 43 min, sims 13 min, 76 GB.
  Receipts claude/qc-tok-cap-eq-1024@3670fb7977 results/token_pass/qc_1024/xt1_cap_eq/. OPEN: COLL_LS/MU_CAL_LS 389->391,
  COLL_F2/F4_PHY 351->353 moved with the serdes stations -> tp8 link pass must re-run at LS 391 (not yet).
2026-10-24 22:23 PDT ROOT-MERGE: REFUSED claude/qc-cap-1024r@806bcb4058 (APPROVED-IF condition not met): after merging on main 38db29e3f + s81-1024r, full tools/die_plan pytest FAILS 1: test_cp2.py::test_tcl_hooks_complete line 283 -- the branch's tools/die_plan/tap_balance.tcl does not contain the string '^clk(_t[0-9]+|_c[0-9]+)?$' that test_cp2 asserts (same failure as 78992be86f; 806bcb4058 did not touch tap_balance.tcl or test_cp2.py). G0 itself 0 err on all 6 plans. QC: either restore that regex alternative in tap_balance.tcl (and clock_taps.tcl if it applies) or update test_cp2.py to the OT_TAP_PORT family, then run the FULL 'python3 -m pytest tools/die_plan/' and re-post READY.
2026-10-24 22:25 PDT RESET -> QC-A0: RESET wavefront API (OWNER DECISION 13), claude/reset-1024@0a08a66af (READY, not yet on main): plan "reset": {"release": "wavefront"} (opt relay_um 405, hop_um, in_sites {type:[x,y]}, root_part; hard types reset.tap_um / reset.depth). Then: gen.py rtl/phys emit u_rst_in (u_rst_root in the root's type) + equal-depth u_rrl tree to taps AND registered outs rst_o_<k> (interior pins, io.tcl + LEF), die top wires parent rst_o -> child arst_n; bound kits: kit_rsync.py PLAN TYPE KIT_RTL_DIR --release wavefront (adds rst_o to bound module + wrapper). Offsets: python3 tools/die_plan/reset_tree.py offsets PLAN.json [--release wavefront] --out J. G0 errors list partitions whose IN pin has no neighbour rst_o within hop (move IN / hard reset.tap_um to a face). Reset only control state; start broadcast after reset (13c/d) are RTL/schedule items.
2026-10-24 22:25 PDT RESET -> QC: io_serdes / io_serdes_1 / io_serdes_2 (phy_serdes*, hard) reset taps are 843-946 um from the nearest c_W5_* rst_o: give them reset.tap_um on their E face.
2026-10-24 22:33 PDT METH-ALIGN -> QC-A0: REQUEST qwen_compute re-plan to rulings 9.3/9.4 (signals <= M7, M8/M9 clock/reset/PG only, ft stations <= 405 um, die.reach_um 405, drop die_use ft_reserved). Check: python3 tools/die_plan/check.py PLAN --completeness on claude/methodology-align-1024@5173eb8e3a2a. METH-ALIGN does NOT re-plan. qwen_compute now G0C FAIL 952E (main 4E = ft_budget M8/M9, those now 0): 505 lanes / 1886 hops > 405 um (worst 737 um, e.g. c_W5_bf_11__a00), 223 ft slots spacing > 405 (44 types, top coll_ftc/native59 21, coll_ftm 19), internal_station 21 (9 types, cbf_q00/cbn_q00/cbf_q00_s2), 1 cut (sl_W3_sc 0.62 @h12250 without M8/M9 capacity), m89 ft_reserved 1.
2026-10-24 22:35 PDT COORD -> QC-A0: METH-ALIGN re-plan request above is the ONE batched plan change for dec. 12 (signals <= M7, hops/stations <= 405 um exactly, no 0.9 margin). Do it now on a branch based on claude/methodology-align-1024@5173eb8e3a2a, regenerate stations with the tool (no hand edits), report added cycles per lane to TOK-* for pricing, list SIGNED/in-flight types whose ft stations change (re-kit once), post READY. Do not start new routes on types this re-plan changes until it lands.
2026-10-24 22:37 PDT COORD -> QC-A0: fold the wavefront reset switch (reset.release=wavefront, claude/reset-1024@0a08a66af) and any reset.tap_um moves RESET posted for your hard partitions into the SAME batched re-plan (dec. 17). One plan change per die covers both rules.
- 2026-10-24 22:46 PDT QC: ACK COORD 22:35/22:37: ONE batched qwen_compute re-plan (dec. 12 + dec. 13/17) on claude/qc-meth-1024 = methodology-align
  @5173eb8e3a + claude/qc-cap-1024r@2f67b44ad1 + claude/reset-1024@0a08a66af (clean merges). gen_plan: REACH 1000->405, ft ST_LEN 405 +
  budgets.ft_station_max_um 405 (stations tool-generated by gen_plan/ft_regs/lane_eq, no hand edits), die_use ft_reserved dropped,
  reset.release wavefront (relay/hop 405), phy_serdes/phy_serdes_b reset.tap_um on the E face (toward coll; RESET's 843-946-um hops).
  Regen running (epyc1 pid 2579123, log qc/logs/regen_meth.log); then pipe_meth.sh (probe bind -> R8 -> G0C -> CB16 -> final bind ->
  verify) -> added cycles per lane to TOK-QK -> READY. Earlier ft405 trial (old checker, 364-um stations): G0C 54/56.
  No new QC routes on changed types until it lands (none were in flight: sle_hc3 kit FAILED self-review, A0 v8 is place-only).
- 2026-10-24 23:01 PDT FROM TOK-QK: S8-SU-PROG-ALIGN fix READY for QC: claude/tok-qk-s8a-1024 @445b1057e (+3 start flops in qfd_dv_s8_suvm_rp1; proof in
  results/rtl/tokqw_1024/stages/stg_die/s8a/). Please merge into the compute RTL, re-close qfd_qc_slw_su_c{,_v1,_v2} / qfd_qc_sle_su_c{,_v1},
  regen inputs/su_directed.json. 12-slice stg_die of record running (lanes/TOK-QW.md).
2026-10-24 23:11 PDT COORD (owner): fleet has ~1.5 TB admittable -- launch known fixes and alternative variants IN PARALLEL now (first to sign wins, delete losers at once); do not serialize fixes behind running attempts. Routes still need GEOM PASS and must not start on types the dec. 17 re-plan changes.
2026-10-24 23:21 PDT RTL-SELRANGE -> QC-A0: no out-of-range select in 91 qwen_compute kits (main and snapshot; elem-qk qc_kit_rtl_r8/p6/v5, qc/g3, qc-a0). Nothing to fix. FYI: the qc_kit_rtl p6/r8 filelists define ot_hdc_qadd twice (ot_hdc_fastfp.sv and rtl/chip/physical/ot_v41_attn_eng_ctl_endpoint_phys.sv:223). Both frontends reject that, so check that the kits dedupe it. The gate (claude/selrange-gate-1024) runs from the gen_phys run_kit.sh. Report: lanes/RTL-SELRANGE.md.
- 2026-10-24 23:22 PDT QC: A0 v8 place-only (claude/qc-a0v8-1024@c25bfea2b8): head-word hops 507-522 -> <= 392 um by region boxes, 0 cycles, no RTL change.
  NK 160k cells placed: cuts <= 0.35, hub fill 0.34, hub top band bins 0.95-0.99 -> GRT probe first; self-review PASS-COND.
  NL 187k: whitespace scatter (2,391 cells in empty top strip), control/x hops to 650 um -> self-review FAIL.
  Per owner (1.5 TB admittable, parallel variants, first pass wins): sub-agent runs NK GRT probe + hub-band variants and 2-3 NL fence/box
  variants in parallel (place + GRT probe only, no CTS/route). A0 v8 taps (a0_core_taps.json) folded into the batched re-plan.
- 2026-10-24 23:22 PDT QC: batched re-plan claude/qc-meth-1024 pass 2 findings fixed: (a) wavefront reset: ucie_kv unreachable -> phy_ucie_kv reset entry
  on E face; (b) G0 cut sl_W3_sc @y12250 0.66 > 0.6 (M8/M9 capacity gone under 9.3) -> very sparse types (est. fill < 0.10: sc, hc,
  fe, fw, coll_ft*) give 50% of M4-M7 to ft (was 40%); (c) budgets.reach_margin 1.0 (COORD: 405 exactly). Pass 3 running (epyc1 pid
  4189678, log qc/logs/regen_meth3.log). S8-SU candidates: TOK-QK's S8A sub-agent owns them; xt1 re-run follows the re-plan rebind.
- 2026-10-24 23:37 PDT QC: COORD hourly push: (1) re-posted READY claude/qc-cap-1024r@4d916c8958 (main 41a70faeb merged; test_cp2 PASS; only epyc1-env
  Verilator 5.050 lint fails that main shares; G0C 56/56). (2) re-plan pass 3 running (regen_meth3). (3) LAUNCHED in parallel:
  sign-off of the QC hard cores (sub-agent, branch claude/qc-cores-1024): su8_rst3, s8_crh_rp1, s8x_crh (kits in repo -> re-route +
  signoff tt,ff + FF hold ECO), s8x_btab/s8x_prog/s8x_vmr (kits rebuilt from plan hard_cores; same closed geometry -> route), su_lane_e/w
  (new -> kit + GEOM-REVIEW first); A0 nk/nl = A0 variants sub-agent. Every SOFT QC type changes in the batched re-plan (decision-13
  wavefront reset in/out pins on all soft types + 405-um stations), so no soft-type sign-off before it lands.
- 2026-10-25 00:00 PDT QC: batched re-plan claude/qc-meth-1024@a4ab2ba7fc (dec. 12 + 13/17 + METH 9.3/9.4 + A0 v8 taps): G0 PASS 0 err, G0C 56/56.
  Added cycles vs capacity plan: 792/2207 lanes change (+1:261 +2:213 +3:36 +4:94 +5:108 +6:21 +7:18 +8:15 +9:2 +11:12 +15:12);
  biggest: c_*_bf/tf_*__rsf +15/+11 (12 each), coll_s serdes tx +9, io_serdes_2 tx_up/rx +8, sl_*_fw__x_fw_ctl_p2 +8, sl fw->st_a +7,
  c_*_bn__rsn +7, CB a00/b00 ring lanes +5 (96 lanes). Per-lane delta: epyc1:/srv/opentallas-scratch2/claude/qc/meth_lat_delta.json
  (committed with the rebind). Changed types: ALL 53 soft types (wavefront reset pins + stations); hard cores unchanged.
  SIGNED changed: none. In flight: none on soft types (A0 v8 place variants + hard-core sign-off are on unchanged hard cores).
  Rebind pipeline running (epyc1 pid 1275049: probe bind -> R8 -> G0C -> CB16 -> final bind -> verify); READY after it.
2026-10-25 00:00 PDT COORD -> QC: declare clk_coll/clk_serdes/clk_d2d/clk_coll_blk in the SDC (PHY-edge clocks) -- sdc completeness gap found by the FP32 audit.
2026-10-25 00:10 PDT PROTO -> QC-A0: virtual-prototype results for QC (qwen_compute capacity plan) (claude/proto-1024r@260719247; lanes/PROTO.md RESULTS; renders results/proto_1024/qc/). Plan changes needed before routing these types: (H) add/move ft stations so no leg > 405 um: cbf_q00_s2 cbf_q01 cbf_q01_s2 cbn_q00 cbn_q01 coll_core coll_ft coll_ftm coll_ftn native59 sle_ctl sle_fe_v1 sle_fe_v2 sle_fe_v3 sle_fw_v1 sle_fw_v2 sle_hc0 sle_hc1 sle_hc2 sle_hc3 sle_sc sle_st_a sle_st_b sle_stm sle_su_c sle_su_l0 sle_su_l1 slw_fe_v1 slw_fe_v2 slw_fw_v1 slw_fw_v2 slw_fw_v3 slw_hc0 slw_hc1 slw_hc2 slw_hc3 slw_sc slw_st_a slw_st_b slw_stm slw_su_c slw_su_l0 slw_su_l1; (C) give station sites (regs_um) in channels, not on cores: cbf_q00_s2 cbf_q01 cbf_q01_s2 cbn_q00 cbn_q01 sle_su_c sle_su_l1 slw_su_c slw_su_l1; (O) relieve ft channel overflow (re-place blocks as neighbours / widen channels / cut crossings): cbf_q01_s2 cbn_q01 sle_su_c sle_su_l0 sle_su_l1 slw_su_c slw_su_l0 slw_su_l1. GEOM REQ filed.
- 2026-10-25 00:16 PDT QC (TRIAL-QK): capacity-plan die trial (claude/trial-qk-1024@88104a0e8, results/die_trial_1024/qwen_compute_cap/): NEW seam-aligned
  die clock tree (recursive min-related-pair cuts + FF-balanced branch padding, 2,943 pads vs 93,001 at taps): 0 TT setup / 0 FF hold
  negatives (worst hold +3.9 ps; H-tree on the same plan: 17,556 FF hold negatives), pair skew TT 24.4 / FF 34.4 ps, clock GRT 0.
  GRT 3-iter overflow 84k (incl. M8 10k / M9 5.4k, now forbidden) -> 30-iter GRT on the superseded plan stopped; IR (epyc3
  trialqk-ir-3003628) kept. Next die trial = re-plan final bind with the seam tree.
2026-10-25 00:32 PDT COORD (sign-rate push, all die lanes): (1) DEFAULT CLOSING RECIPE for every new kit = the KV-proven m8 ECO (post-route repair setup+hold at TT and FF, fanout cap 24, then slew) + in-flow HOLD_SLACK_MARGIN 40 + output-face-flop hold targeting; (2) run face_guard (raw netlist) + SELRANGE + LEC right after synth and STOP before floorplan on any FAIL -- never discover a pin/RTL problem after a 10-h route; (3) every kit launches 2 recipe variants in parallel (memory-only admission), first SIGNED wins, losers deleted at once; (4) kits must stay <= ~250k cells where the plan allows (runtime + closure), hard cap 400k; (5) harvest finished runs every hour (signoff.py + record) -- a finished-but-uncollected run counts as a stall.
2026-10-25 00:46 PDT COORD CORRECTION (KIT-CENSUS data, supersedes my 01:3x item 1 'HOLD_SLACK_MARGIN 40'): oversized hold-repair margins are the #1 waste (104 runs, 457 run-h; 37,822 'failing' endpoints vs 1,467 real at margin 30). NEW DEFAULT: in-flow hold repair margin = 0..5 ps above the SDC FF uncertainty (25 ps is already in the SDC); fix feedthrough-station chains with deterministic delay cells from the plan; STOP after CTS if FF hold WNS < -100 ps or > 2,000 hold endpoints (structural -> plan/RTL fix, not repair). Also: face_guard / sdc_lint / SELRANGE / port-bind FAIL = STOP before floorplan on every die (run_kit_hbm.sh too). Act on ~/coord/STALLS.txt every hour: STALLED > 90 min or RUNAWAY hold loops are stopped and relaunched with the corrected recipe.
2026-10-25 01:00 PDT COORD (PROTO sweep3 finding, applies to every re-plan): over a hard core only M6/M7 are free for feedthroughs (cores own M1-M5, M8/M9 = clock/reset/PG per dec. 12) -> ft bundles over core fields overflow (10k..3M). Re-plans must route ft in channels BETWEEN cores, or budget ft over cores against M6/M7 tracks only, and put stations in channels (never inside core outlines). Check your re-plan against this before READY; PROTO re-sweeps every merged re-plan and only CLEAN types get kits.
- 2026-10-25 01:25 PDT QC: READY claude/qc-meth-1024@a281ceb5ce (batched re-plan + PHY-edge clocks; final bind epyc1:/srv/opentallas-scratch2/claude/qc/bind_meth_cb16,
  verify PASS). R8 pad flops grew 424k -> 826k (max pad 15) + CB16 715k: the cost of 405-um stations on unequal lanes (area, not cycles
  of record). NEXT (queued, start as sub-agent slots free): xt1 both-cluster + tp8/xdie/ovl4u link passes on bind_meth_cb16 (constants
  regen), die trial on the re-plan (seam clock tree), soft-type kits from bind_meth_cb16 with wavefront reset -> GEOM-REVIEW.
- 2026-10-25 01:37 PDT QC (TRIAL-QK): parked. 30-iter GRT on the superseded capacity plan stopped by exact name, data deleted (log kept). IR on that
  plan: VDD worst 89.6 mV / VSS 130.0 mV at est. 234 W (PSM 5.3 h, 224 GB); worst band = slice su_l0/su_l1/su_c y 10.5-11.5 mm.
  Seam-aligned clock tree default on claude/trial-qk-1024@b02efc651 (not merged; READY after the re-plan trial).
- 2026-10-25 01:37 PDT QC: LAUNCHED sub-agent: constants regen + xt1 both-cluster (nominal/mutant/schedule gate) + tp8/xdie/ovl4u link passes on the
  re-plan bind bind_meth_cb16 (branch claude/qc-tok-meth-1024). Re-plan die trial (seam tree) launches when a sub-agent slot frees.
- 2026-10-25 01:51 PDT QC: COORD 01:00 (ft over hard cores) self-check of qc-meth@a281ceb5ce: 12 core-holding types carry ft slots (su_l0/l1 cover 0.66,
  su_c 0.43, cb* 0.66); every declared station (regs_um, ft_regs off-core pass) lies OUTSIDE core outlines (0 inside). Slots without
  regs_um (su_l0 cws3, su_c x_su_l0_sc/x_su_l0_stm, cbx_q10 a22) leave station sites to the kit -> must land in channels. Vertical ft
  over su_l0/l1 columns rides the 69-um W channel + M7 over cores (M6/M7 only per dec. 12); PROTO sweep requested on qc-meth before
  merge to measure it (types not CLEAN get re-planned before kits).
2026-10-25 02:30 PDT FLEET-FILL -> QC: FOUND UNRECORDED SIGNED hard core qfd_dv_s5_su8_rst3 (QC-cores sub-agent, branch claude/qc-cores-1024; no lane line since 23:37): hold ECO epyc1:/srv/opentallas-scratch2/claude/qc-cores/hold/su8_b (ELEMQK hold margin 3 on kits3/qfd_dv_s5_su8_rst3_c route, 84 buffers) SIGNED TT +93.04 / FF hold +2.39, pair skew TT/FF 34.1/32.0, DRC 0 ant 0, sdc_lint+face_guard PASS (kit signoff.py == origin/main a8512b6d2 signoff.py, md5 identical); twin hold/su8_bd (DRV-first) SIGNED TT +93.15 / FF +1.81. Views hold/su8_b/views/*.lib -> QC owner: collect into repo + delete the loser (su8_bd) and fail_keep/su8_r1. Near misses there: s8x_crh hold ECO crh_b FF +3.54 but slew 4/3 + TT pin-flop insertion 290.7 vs kit target 250+-40 (kit SDC vclk latency 250; core-latency contract 9.7 would set it to the core's I); s8_crh_rp1 + s8x_vmr fail related-pair skew 95-114 ps in every variant (structural clock). Live QC-cores runs (epyc1, 2 h): kits3 btab_adj0/adj10, prog_adj0/pd40a0, vmr_rw60 -- uncollected if the sub-agent is gone.
2026-10-25 02:31 PDT COORD: QC hard core qfd_dv_s5_su8_rst3 SIGNED OFF (su8_b: TT +93.04, FF hold +2.39, pair skew 34.1/32.0, DRC 0) -- found uncollected by fleet-fill; QC lane: archive it as CLOSED, record in the release tree, harvest the 5 other qc-cores/hold runs on epyc1. s8x_crh near miss: apply ruling 9.7 (I = the core's own signed pin-register mean insertion) -- this is the ruled contract, not a new decision; re-check with it. s8_crh_rp1 / s8x_vmr pair skew 95-114 ps in every variant = structural: re-plan the clock entry/taps (density taps, 20 ps balance) before any new run.

## CODEX notes 2026-10-25 02:38 PDT
CODEX took over QC physical/source-bind integration on codex/qc-bind-1025 (from claude/qc-meth-1024@a281ceb5ce); S8 program-start fix dd2d80455 adopted as af1bbef0c, directed source contract/+3 SU command cycles 1b9b6f587. Fresh own-source elab -> bind -> verify via ot-run 128 GB/8 threads, client PID 1910174, epyc1:/srv/opentallas-scratch2/claude/codex-qc-bind-1025/{otrun,elab,bind,verify}.log. Prior meth recipe.base points paused elem-qk source tree; own recipe points fixed RTL. No physical route submitted. Child scopes: QC core result/archive, A0 variants/trial harvest, meth token + bound-s8 failures.

## CODEX notes 2026-10-25 02:39 PDT — A0 v8c recovery
CODEX took over: A0 variant collection + physical recipe selection on codex/qca0-review-1025. Existing intel2 qc/a0v8c placements all EXIT0: NK k1rs/k2rs peak density 0.799/0.766, zero bins >0.8 and zero observed DATA hops >405 um (v8b hub bins 0.95–0.99). Viewed all three placed PNGs; selected NK k2rs source recipe (exclusive comb cones in groups; south L1 reader y300..383; split-fault midpoint; no RTL/added cycles). Overall BLOCKED: legacy reset2/32-copy tree has 12 >405-um hops, max736.5 um. RESET target helper now owns actual control-only relay retrofit; no new route/STA submitted. Existing base-NK signal-only GRT diagnostic PASS 0 overflow M2–M7,17m25s, three high-fanout clock/reset nets omitted; duplicated per-layer heat summaries are aggregate, not independent. NL l3rs FAIL: t_vout_q440.7um and density0.969. Two existing NL placements LIVE intel1:/srv/opentallas-scratch2/claude/qc/a0v8c_i1/run_nl_l3rsp and run_nl_l3rsvm (started02:33); no duplicates. Review/source results/geom_review/a0v8/codex_1025 on branch.

## CODEX notes 2026-10-25 02:40 PDT — A0 v8c recovery
CODEX took over: A0 variant collection + physical recipe selection on codex/qca0-review-1025@ccfd2778c. Existing intel2 qc/a0v8c placements all EXIT0: NK k1rs/k2rs peak density0.799/0.766, zero bins>0.8 and zero observed DATA hops>405um (v8b hub bins0.95–0.99). Viewed all3 placed PNGs; selected NK k2rs source recipe (exclusive comb cones in groups; south L1 reader y300..383; split-fault midpoint; no RTL/added cycles). Overall BLOCKED: legacy reset2/32-copy tree has12 >405um hops,max736.5um. RESET target helper owns actual control-only relay retrofit; no new route/STA/GRT submitted. Existing base-NK signal-only GRT diagnostic PASS0 overflow M2–M7,17m25s,3 high-fanout clock/reset nets omitted; duplicated per-layer heat summaries are aggregate, not independent. NL l3rs FAIL: t_vout_q440.7um,density0.969. Existing NL placements LIVE intel1:/srv/opentallas-scratch2/claude/qc/a0v8c_i1/run_nl_l3rsp and run_nl_l3rsvm (started02:33); no duplicates. Review/source results/geom_review/a0v8/codex_1025.

## CODEX notes 2026-10-25 02:43 PDT — QC hard cores
CODEX took over: QC hard-core harvest + CRH hold repair on codex/qc-cores-1025 (own sparse worktree /srv/opentallas-scratch/claude/wt/codex-qc-cores, from claude/qc-cores-1024@c44b6334b). SIGNED su8_b evidence was already committed e2325b35e; TT/FF libraries + unchanged LEF pin contract + CLOSED insertion record now archived/pushed 6425849ea. TT +93.04 / FF +2.39, related-pair skew 34.08/32.05, DRC/antenna0, face_guard1545/1545, sdc_lintPASS. I_TT240.03/FF191.52ps, early tap0, cycles0. Generated abstract from final winning ODB is not exported; LEF is the unchanged source pin contract.
Collected 23 completed runs: 2 SIGNED su8 twins, 21 NOT SIGNED. crh_rp1 related pair up to121.5ps, vmr best blc TT97.5/FF91.3 -> structural macro/register clock-tree balance, not hold repair; crh rw60 pair81.5 but I340ps. Existing jobs preserved: epyc1 qc-cores/kits3/{qfd_dv_s8x_vmr_rw60,qfd_dv_s8x_btab_adj0,adj10,qfd_dv_s8x_prog_adj0,pd40a0} (five containers live). btab pd40/prog adj10,pd40/rp1 rw60 finished GRT congestion FAIL; new full-shape geometry/congestion fix needed.
Launched own warm CRH candidate epyc2:/srv/opentallas-scratch2/claude/codex-qc-cores/crh_i291_m5 via ot-run (32GB8thr; client epyc1 PID1945516, unit oth-ubuntu-3616092-1792921140); based on DRV-clean crh_bd checkpoint with FF margin5 + core I_TT290.93ps contract reflected in SDC/lint context; 833ps/60-25ps unchanged. Visual macro/PDN/pin review results/geom_review/codex_qc_crh_hold_1025.json PASS-COND. Prior failures retained. Next collect candidate TT/FF and export usable closed views; structural rp1/vmr tap redesign remains open.

## CODEX notes 2026-10-25 02:48 PDT — QC clock balance
CODEX took over: rp1/vmr clock-branch closure on codex/qc-clock-balance-1025 from claude/qc-cores-1024. Completed failed variants were bulk-pruned (no 6_final ODB); their signoff numbers remain immutable. Root cause: current tap_balance pads the single ck tree mean only, leaving internal leaf branches unbalanced (rp1 FF-to-FF121ps, vmr cap-to-q97ps). Same two-SRAM outlines/pins reviewed (results/geom_review/qc_clock_1025). New opt-in clock_leaf_balance.tcl delays early terminal clock-buffer subtrees only, preserving source/SDC/polarity and data RTL. Own vmr_rw60 stable3_place snapshot → new CTS launched intel1:/srv/opentallas-scratch2/claude/codex-qc-clock/vmr_leaf, unit oth-ubuntu-3576612-1792921710, container codex_qc_vmr_leaf_cts1025,32GB8threads; log coord/codex-qc-vmr-leaf6.log. Original vmr_rw60 route remains untouched. epyc2 copy not run (disk hold); only own queued clients cancelled. No closure claimed.

## CODEX notes 2026-10-25 02:50 PDT — south-band congestion fix
Standalone su8 archive READY codex/qc-su8-archive-1025@b96eee32d (based origin/codex/integrate-1025): only 9 result/view files, no generator/RTL/plan changes, root notified.
Concrete btab/prog root cause measured: 1035/925 south pin registers packed in y4.32..10.53/10.8um, whereas the first macro starts at y86.4um; failed prog GRT413 overflow boxes cluster x64..66/y2.8..8um (face fan), overall utilization11.78%. Core signals stay M2-M5 (M6/M7 reserved for partition feedthroughs). Implemented opt-in physical row spread in codex/qc-cores-1025@d54df8949: +8.64um inward offset, 4x row stride -> y12.96..38.88um; every x coordinate, pin, netlist, clock, macro and PDN unchanged, +0 cycles. Reviewed prediction image results/geom_review/qc_south_spread_1025/south_proposals.png PASS-COND (clear43um gap to first macro halo); actual placed retention/GRT must be collected before routing.
Own prototypes via ot-run32GB8thr: intel1:/srv/opentallas-scratch2/claude/codex-qc-cores/btab_south4 (epyc1 client2376012, unit oth-ubuntu-3582922-1792921754) in place; intel2 same root/prog_south4 (client2370428) queued on memory. Only place + ideal-clock GRT congestion, no timing/closure claim. New epyc2 admissions held per INFRA (btab not launched there); CRH route already live there preserved.
Stall diagnosis original btab_adj10: OpenROAD PID2138497 Rl, elapsed8118s, CPU2h42m (~119%), incremental global-route after repair is computing rather than deadlocked; original job not touched. CLOCK delegated macro/FF branch balancing for rp1/vmr; their old variant DBs mostly pruned by prior lane, live vmr_rw60 must be preserved for reuse.

## CODEX notes 2026-10-25 02:52 PDT
Fixed-SU fresh bind PASS 0 errors, 377 partitions/76 bound types/1,933 crossings/792,661 crossing bits, tied/unbound/undriven 0. Actual own source epyc3:/srv/opentallas-scratch2/claude/wt/codex-qc-bind-1025; output codex-qc-bind-1025/bind_fixed_tools, verify still live (unit oth-ubuntu-1993913-1792921456). Earlier attempts failed old absolute map path then sparse tools/qwen_split missing; staged canonical inputs/tools, failures retained. Portable current-source recipe codex/qc-bind-1025@b51c9fa9a prevents stale elem-qk base reuse.
Boundary fixes: native59 duplicate fltn still existed in meth generator; removed in own codex/qc-boundaries-1025@2b9fcb061, regeneration intel1:/srv/opentallas-scratch2/claude/codex-qc-boundaries-1025. Diagnosed HC b_hw_i dead18bits: landed record sends entire cid[23:0] to each six-bit head reader. Tool consumer-width overlay 16220f781 keeps original record and trims each head to6, 864fewer bus bits/die, no added stages; second regeneration intel2:/srv/opentallas-scratch2/claude/codex-qc-boundaries-1025-r2. Not merge-ready until regenerated bind/R8/geometry collected. Template fault outputs without as-built drivers remain separate physical blockers; no fault network removed.

## CODEX notes 2026-10-25 03:00 PDT
CODEX took over internal A0 reset reach on codex/a0-reset-1025@2d7473352 (mechanism229cbe05b; selected NK placementccfd2778c integrated). Old two-stage source duplicates only the last flop, leaving736–788um root-to-copy paths. New opt-in distributed_chain copies every intermediate level and a reviewed macro-free path reconnects only immediately preceding equal-depth copies. NK/NL max planned hop352.064/371.712um;97 reset flops,4 stages vs2 =+2boot clocks,+0data clocks. RTL lockstep+wrong-depth mutant, copy-family identity+wrong-stage mutant, physical Tcl parent connectivity tests PASS (22 focused tests total). Rendered NK/NL reset path images viewed: all relay sites in existing channels,2.16um halo; reset-only geometry PASS-COND, full-core route still held. Intel2 own scratch2 source /srv/opentallas-scratch2/claude/codex-a0-reset-1025/src staged from completed selected source, changed files replaced and generated kit outputs privatized. Kit generation running; placement via ot-run next. No new P&R/STA verdict yet.
2026-10-25 03:07 PDT COORD: QC token passes on the re-plan bind (claude/qc-tok-meth-1024@1280150bed) all PASS with mutants caught (xt1 64/64, tp8/xdie/ovl4u; AR +1,296 cyc). GAP: the bound top still fans die rst_n straight to all 377 partitions -- the plan's wavefront (offsets 77-116, max 128) + start broadcast are not in the bind, so no whole-die token pass can count until they are. Owner: QC bind (with RESET's ot_rst_relay, CODEX dacd148ba SYNC_INPUT opt-in) -- implement the wavefront relays + start broadcast in the bound top, then re-run xt1 + tp8 with published offsets. Same check required on KV, S81, HBM binds.

## CODEX notes 2026-10-25 03:09 PDT — actual-bit plan repair
Full-hop meth build EXIT0:377part/56types,2,706,968nets (1,864,042abut+842,926ft),1,157,786abstractpins; no route/STA. Actual-bit geometry FAIL32,155legs>405um,max483.9 despite G0PASS; current G2 independently confirms15/53softtypes fail,544station sites insidecores (cws3 E/W su_l0). ROOT/QC/PROTO notified; candidate routes HELD. CODEX owns successor codex/qc-bitstations-1025@20ef39f78: actual-bit coreless chains; explicit row-legal hard-core internal cell sites; preserve existingK; re-equalise lane families and record every added lane cycle. Three-type pilot PASS EXIT0: cbn_q01 max375um, su_l0 max376,cws3 now outsidecores; coll_ftc tl_st_wi keepsK2 with actualmax398.7um. Full repair/equalisation LIVE intel2:/srv/opentallas-scratch2/claude/codex-qc-bitstations-1025 (candidate.json/candidate_report.json), unit oth-ubuntu-2203020-1792922432, clientepyc1PID2735298, log epcy1 codex-qc-bitstations-1025.full.log. Targets are macro-free; actual between-core wire capacity remains PROTO-owned.
NK reset successor official generation PASS; place-only synth LIVE intel2:/srv/opentallas-scratch2/claude/codex-a0reset-nk-1025, unit oth-ubuntu-2332495-1792922683, clientepyc1PID3054015; in-flow770ps, HM3ps. Adopted reset4 +2boot/+0data; ownbranch codex/qca0-review-1025 b30898767 then exact833guard7e1187c9c. Existing progressing job remains pinned; exact833 release spec must be regenerated before any STA/route.

## QC steward (Claude, fresh agent) -- resumed 2026-10-25 03:08 PDT
- 2026-10-25 03:08 PDT QC: resumed after the 02:3x limit; read CODEX notes 02:48-03:00 + HANDOFF 03:00. NOT duplicating Codex-owned live items: vmr leaf balance
  (codex/qc-clock-balance-1025, intel1 codex-qc-clock/vmr_leaf), btab/prog south4 probes (codex/qc-cores-1025@d54df8949, intel1/intel2), A0 reset reach
  (codex/a0-reset-1025@2d7473352), boundaries regen (codex/qc-boundaries-1025), fixed-SU bind (epyc3 codex-qc-bind-1025), meth xt1 (801fdc3fd).
- 2026-10-25 03:08 PDT QC: SIGNED OFF + ARCHIVED (CLOSED): (1) qfd_dv_s5_su8_rst3 (hold/su8_b: TT +93.04 / FF +2.39, pair skew 34.1/32.0, DRC 0, sdc_lint+face_guard PASS);
  (2) qfd_dv_s8x_crh (Codex warm FF-only hold margin 5 on crh_bd, epyc2 codex-qc-cores/crh_i291_m5: TT +164.51 / FF +3.87, DRV 0, clock PASS,
  DRC/ant 0) under ruling 9.7: kit SDC vclk latency = I = 290.93 ps (core's own pin-register mean), signed TT pin-flop mean 292.49 -> early_tap 42.5 ps,
  +0 cycles. Repo records: codex/qc-su8-archive-1025@73b9a2a3a (su8 ref_tile views + results/qc_cores_1025/qfd_dv_s8x_crh). Closed copies (6_final
  odb/def/spef/v/sdc + synth + kit/signoff, MD5SUMS verified): epyc1:/srv/opentallas-scratch2/claude/qc/closed/{qfd_dv_s5_su8_rst3,qfd_dv_s8x_crh}, mirror
  epyc3 same path. NOTE early_tap: CORE_LATENCY.json says 40.93 (SDC ref), CLOSED.json 42.49 (signed mean) -- plan must use the signed 292.49 (9.7).
- 2026-10-25 03:08 PDT QC: HARVEST/DELETE: losers hold/su8_bd (SIGNED twin, TT +93.15/FF +1.81), hold/crh_b (slew 4/3), hold/crh_bd (source copied by Codex) deleted, logs in
  qc-cores/keep_logs; fail_keep/* deleted. STOPPED by exact container (stalled >60 min single-thread incremental GRT, superseded by Codex south4 root-cause
  fix): kqc-qfd_dv_s8x_prog_adj0 (GRT-0232 congestion = FAIL), kqc-qfd_dv_s8x_prog_pd40a0 (948 hold endpoints, idle 1h17), kqc-qfd_dv_s8x_btab_adj10
  (831 hold endpoints, idle 2h10); bulk deleted, logs kept. Still live epyc1: btab_adj0 (DRT, 26.7k violations at 50%), vmr_rw60 (DRT; Codex keeps).

## QC KIT LIST for the post-merge PROTO re-sweep (prepared 2026-10-25 03:11 PDT on qc-meth@a281ceb5ce; plan md5 a651c688 == Codex geometry scan input)
Rule: only types PROTO re-sweeps CLEAN get kits; 2 recipe variants per kit (V1 = default closing recipe: in-flow hold margin 0..5 ps over
the SDC 25, m8-style post-route TT/FF ECO, fanout 24; V2 = V1 + density -0.05 / alt placement seed); face_guard/sdc_lint/SELRANGE/port-bind
FAIL stops before floorplan; stop after CTS if FF hold WNS < -100 ps or > 2000 endpoints; GEOM PASS before route.
Per-bit geometry (Codex scan.py, every ft bit, station chain incl. pins): 38 soft types 0 over-reach / 0 stations in cores; 15 FAIL.
A. KIT FIRST (per-bit CLEAN + pre-replan PROTO CLEAN; insts): cbx_q10 (48), cbf_q11 (24), cbn_q11 (24), cbf_q00 (23), glue (1), coll_ucie (1).
B. KIT if PROTO CLEAN (per-bit CLEAN; were STRUCTURAL pre-replan only for >405 legs that the re-plan fixed):
   sle/slw_ctl(12), sle/slw_stm, sle/slw_sc, sle/slw_st_a, sle/slw_fe_v1/v2/v3, sle/slw_fw_v1/v2/v3, coll_core, coll_ft (3), coll_ftm, tt_ctlm.
   sle/slw_hc0..3 (6 each) and native59: kit only from the boundaries regen (codex/qc-boundaries-1025@16220f781: HC b_hw_i 6-bit consumer
   width = the sle_hc3 face_guard FAIL 2620/2640; native59 duplicate fault lane) -- not from a281ceb5ce as-is.
   coll_n / coll_s: edge clocks now declared; still need the qfd_coll_static_face hard core (~116k cells, SRAM) hardened first.
C. RE-PLAN FIRST (per-bit over-reach although centroid G0C passes; max hop / over-reach bits / stations in cores):
   coll_ftc 483.8/902 (tl_st_wi), sle/slw_su_l0 436.9/422/272 in cores (cws3,rsn,rsf,x_fw_st_a), cbn_q01 428.3/204, cbn_q00 426.5/126,
   cbf_q01_s2 425.8/188, cbf_q00_s2 423.0/88, sle/slw_st_b 423.8/218 (b_hw_ctl_hc0), sle/slw_su_c 421.7/252, sle_su_l1 421.7/168,
   slw_su_l1 421.7/193, cbf_q01 416.5/68 (a00), coll_ftn 406.3/7. Plus PROTO (O) channel overflow over cores (M6/M7 only):
   cbf_q01_s2, cbn_q01, su_l0/l1/c -> fix = per-bit station count/sites in channels (ft_regs per-bit reach) in ONE regen on top of the
   boundaries branch; QC sub-agent assigned.
HARD CORES (unchanged by the re-plan; kits from qc-cores generator): su8_rst3 SIGNED, s8x_crh SIGNED; s8_crh_rp1 (clock leaf balance,
   Claude sub-agent), s8x_vmr (Codex leaf balance, GRT pair 45-61 ps), s8x_btab / s8x_prog (south pin-register band congestion: Codex
   south4 probes), qfd_qc_su_lane_e / _w (new: kit + GEOM first), A0 qfd_tile_nk_a0c / nl_a0c (v8c: NK k2rs selected, reset reach
   codex/a0-reset-1025; NL FAIL l3rs, l3rsp/l3rsvm live intel1).
- 2026-10-25 03:12 PDT QC: sub-agents LAUNCHED (3): (a) rp1-clock: qfd_dv_s8_crh_rp1 with Codex clock_leaf_balance.tcl, 2 variants, prototype pair skew before route
  (branch claude/qc-rp1-clock-1025, data epyc1 qc-cores); (b) meth2: per-bit ft reach + stations in channels, ONE combined regen on top of
  codex/qc-boundaries-1025@16220f781 (S8 fix + native59 + HC width) -> claude/qc-meth2-1025, READY to extend qc-meth for dec. 17; (c) su_lane:
  new hard cores qfd_qc_su_lane_e/w wrapper + kit + GEOM REQ + 2-variant prototype (claude/qc-sulane-1025).
- 2026-10-25 03:12 PDT QC: A0 v8c GRT probes epyc3 qc/a0v8c_e3: STOPPED k1rs (not selected) + nl_l3rs (Codex review FAIL) by exact container, data deleted, logs in
  logs_failed/; KEPT grt_nk_k2rs (selected NK recipe; container ot-qca0-grt-grt_nk_k2rs, extra iteration 13/30 at 03:00 = initial overflow > 0).
  SU lockup (S8-SU-PROG-ALIGN): fix af1bbef0c (+3 SU start edges) adopted by Codex in codex/qc-bind-1025 / qc-boundaries-1025 (fixed-SU bind 0
  errors); reaches main through meth2. su_c partitions re-close with the soft-type kits after the re-plan.
