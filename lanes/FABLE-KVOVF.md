# FABLE-KVOVF: KV hg / hgi routing overflow (owner lane, Fable) 2026-11-14

Scope: the 9 qwen_kvsys types kv3_hgi, kv3_hgi_v1 (2 classes), kv3_hgi_v2 (2 classes), kv3_hgi_v3 / v4 / v5, kv3_hg.
MEASURED = read from the named log, database or file. INFERRED = my reading, not run.

## 1. Verdict

The global-route overflow is a symptom. The family has a synthesis defect that breaks timing and inflates the routing
problem; the router then adds two accounting effects on top.

| # | Finding | Status | Fix | Owner |
|---|---|---|---|---|
| F1 | yosys merges the duplicated per-head 1559-bit `ti` pipeline banks: 6 banks in RTL, 3 in the netlist. One chain feeds both head columns. CTS setup -556 to -753 ps. | MEASURED | `override export OT_KEEP_WIRES = ti_b` in config.mk (existing hook) | KIT-OPS-5 (wave env), KV-102 (generator default) |
| F1b | The last stage (`u_hstN_t2`) is one bank feeding four front cores spread over 770 um; with keep alone CTS setup is still -366 ps | MEASURED | one last-stage copy per front core (as-built RTL) | KV-102; proof forms r_* |
| F2 | EST-0005: `repair_antennas` without `-allow_congestion` clears the router's allow-congestion state | MEASURED | add `repair_antennas` to the WF-1 wrapper in grt183_make.sh, or `SKIP_ANTENNA_REPAIR = 1` | KIT-OPS-5 |
| F3 | 2D overflow markers (what raises GRT-0115/0116) are capacity-0 cells inside head cores; the last one is the centre clk/rst_n pin cluster | MEASURED | allow-congestion; optional M7 core close | forms decide |
| F4 | The M5-M8 "total congestion" numbers are layer assignment only (direct core-to-core buses); 2D capacity is not exceeded there | MEASURED on kv3_hg | none needed | - |

## 2. F1: merged pipeline registers (the structural cause)

Design intent (kv3_hgi_v2 `_bound.sv`, as-built stations): the 1559-bit word from the `i_ectl_Q_N_tN` landing ring goes to
each head column through its own three register stages:
- head 2: `u_hst2_g` -> `u_hst2_t1` -> `u_hst2_t2` -> cores `u_head2_e*`
- head 3: `u_hst3_g` -> `u_head2_u_ftg` -> `u_hst3_t2` -> cores `u_head3_e*`

Both chains carry the same data, so yosys `opt_merge` folds them. `qkh_head_tstage` declares plain `reg`s (no keep).

MEASURED (`1_2_yosys.v`, flops named `u_bound.<inst>.u_reg.ti_b[*]`):

| type, kit | gather stages in RTL | `ti_b` banks in netlist | CTS setup WNS / TNS |
|---|---|---|---|
| kv3_hgi_v2__cl2862d491, fdC3 (intel1) | 6 | 3 (hst2_g, head2_u_ftg, hst2_t2) | -586 ps / -558k |
| same, kvgeom5 attempt_13 (epyc10) | 6 | 3 | placement -556 ps / -558k |
| same, kvgeom4 attempt_11 (epyc8) | 6 | 3 | - |
| kv3_hgi_v2__cle0015330, kvgeom4 a7 | 6 | 3 | - |
| kv3_hgi, kvgeom4 a8 | 6 | 3 | - |
| kv3_hgi_v1__cl141fc26e, kvgeom4 a8 | 6 | 3 | - |
| kv3_hgi_v1__cl42bc8b12, kvgeom4 a9 | 6 | 3 | -572 ps |
| kv3_hg, kv102sem_ftgrid a14 (epyc2) | 6 | 3 (head1_u_ftg, hst0_g, hst0_t2) | -753 ps / -969k |

Not checked: kv3_hgi_v3 / v4 / v5 (no netlist found on the hosts I scanned). Same module family; INFERRED same.

Effect, MEASURED (fdC3 `4_cts_final.rpt`): worst path `u_hst2_t2.u_reg.ti_b[1349]` -> `u_head3_e0/g_front_0_u_front__q_data_in[302]`,
data arrival 1363 ps through about 20 repair buffers with 80 ps wire hops; required 777 ps (core tap -130 ps, setup 74 ps).
The flop bank sits at head 2 and drives head 3, about 1.1 mm away. The running control forms (fdC3_r3, fd04_r3, v1a_r3) are
in GRT setup repair at -480 to -540 ps on 1192 to 1349 endpoints, all `u_head3_e0 ... q_data_in[*]`: they cannot reach
R-MINIMAL even if they route.

Effect on routing, MEASURED: `u_hst2_t2.ti_b[*]` nets and the `u_cland_i_ectl_Q_N_tN` ring nets are the nets named in the
fh2 congestion reports (form A iteration 30: `ti_b[285]`, `[291]`, `[292]`, `[460]`, `[461]` at the top edge of head2_e2).
INFERRED: a 1559-bit bus stretched from one head column to the other is the demand that crosses the cores.

Why no gate caught it: reg_fanout flags registers with more than 64 loads; a merged bank here has 2 to 8 loads. LEC passes
(the netlist is equivalent). The bind checks latency, which is unchanged.

Fix: `override export OT_KEEP_WIRES = ti_b` in the kit config.mk. `ot_keep_regs.tcl` (SYNTH_CANONICALIZE_TCL, already in
every kit) then keeps every flop that drives a wire named `ti_b`. No RTL, generator or tool change.
MEASURED on form k_hgi2: `OT_KEEP_WIRES: keep on wires named ti_b`; 6 x 1559 `ti_b` flops in `1_2_yosys.v`; registers
32,599 -> 37,276; standard cells 105,305 -> 114,659; reg_fanout PASS.

## 3. F2: what EST-0005 is

MEASURED (Tcl body of `repair_antennas` in opentallas/orfs:asap7lock-grtoff, OpenROAD 6cb3f2b704):
`repair_antennas` has its own `-allow_congestion` flag and always runs `grt::set_allow_congestion [info exists flags(-allow_congestion)]`.
ORFS `global_route.tcl` calls `repair_antennas -iterations N` without the flag, so the allow state set by `global_route
-allow_congestion` becomes 0. `GlobalRouter::haveRoutes()` returns `!routes.empty() && !(is_congested && !allow_congestion)`,
so it is now false, and `estimate_parasitics -global_routing` raises EST-0005. The step itself does nothing on ASAP7
(`GRT-0246 No diode`).

The same reset is why the r2 forms died with `GRT-0232 -> EST-0165 -> EST-0104` inside repair. The WF-1 hook
(grt183_make.sh, `grt_allow_cong.tcl`) fixed that for `global_route`, `repair_timing` and `repair_design`. It does not wrap
`repair_antennas`.

Fix (KIT-OPS-5): add `repair_antennas` to the wrapped commands in `grt_allow_cong.tcl`, re-asserting
`grt::set_allow_congestion 1` after the call. Until then `export SKIP_ANTENNA_REPAIR = 1` on allow-congestion kits.

## 4. F3 / F4: where the overflow sits

Source: kv3_hg attempt_14 `5_1_grt-failed.odb` (epyc2), per-gcell capacity and usage of M2-M8 dumped with OpenROAD
(`fable-kvovf/dump_hg`), and the fh2 A / C congestion reports of kv3_hgi_v2 (intel1).

2D markers (they raise GRT-0115 / GRT-0116):
- fh2 control C: 2171 -> 43 cells over 30 iterations; all 43 inside head cores, 42 with capacity 0.
- fh2 form A (M7 closed over the cores): 12288 -> 1 cell, net149942 at the centre of head2_e0.
- kv3_hg a14: 2 cells. One is net274613 to `g_t_1_u_stk__rst_n[0]` at the centre of head1_e0; the other is a landing-ring net
  61 um inside head0_e2.
- Over a head core the horizontal capacity (M6 + M8; M2 and M4 are full OBS) is zero in 20 to 32 % of the gcells. These
  cells form vertical streaks: wherever the core LEF has an M7 shape, M6 and M8 show no free track. M7 itself keeps about
  5 of 9 tracks. A net that enters over a core on M7 can go straight but cannot shift sideways without crossing a zero cell.
- Centre pins: each core has 7 clk and 7 rst_n M5 pins within 2.7 um (two gcell columns), under the core's own M6 / M7
  clock shapes. Those columns have 3 to 4 free M7 tracks and no horizontal capacity, so at least one of the 14 nets needs a
  sideways step in a zero cell. This is the residual cell in form A and in kv3_hg. The LEF leaves room (8 thin M6 shapes
  in the 8 x 8 um centre box; pin access completed with no warning), so this is a router-model limit. INFERRED: detail
  route can do it; no form has reached detail route yet.

"Total congestion" per layer (kv3_hg: M5 96 / M6 246 / M7 73 / M8 87), MEASURED:
- All of it lies in one L-shaped path next to head1_e0: one gcell row at y = 245.1 (x 809 to 860, M6 and M8) and one
  column at x = 877.2 (M5 and M7), outside the core.
- The nets are two direct core-to-core buses: `w_head1_e2_g_t_5_u_stk_kp_o[*]` (e2 south face to e0 north face, 55 um
  sideways) and `w_head1_e0_g_front_0_u_front_f_t2[*]` (e0 east face to e1 west face, 135 um along the face), plus
  `u_ft_ft2_o_3` hops.
- 15 nets share a row that has 43 tracks over four layers. The 2D router sees no overflow; layer assignment stacks the
  wires on the layers next to the pin layer. It does not raise GRT-0115 and is not a capacity problem.

Why closing M7 moved overflow to M5 (form A: M5 158 / M7 488 against C: M5 6 / M7 576). INFERRED from the kv3_hg data, not
measured on kv3_hgi_v2 (form A wrote no database): these counts are the layer-assignment kind. With M7 shut over the
cores, north-south runs move to the street columns beside the cores, where pin-layer wires are assigned to M5 and M7
alike. The 2D marker count fell from 43 to 1 in the same run.

Cost of the M7 close, MEASURED: wirelength 8.755 M um -> 8.837 M um (+0.9 %), M7 demand 658k -> 374k.

## 5. Forms

All from synth on the kvgeom5 kits, goal route, `ot-run --mem 56 --threads 12`, launched 22:56 PST on epyc2 (copies on
epyc10, epyc7, epyc9). Dirs `/srv/opentallas-scratch2/claude/fable-kvovf/forms/<form>/<type>`, logs intel2
`~/kvovf/<form>.log`, status `bash ~/kvovf/st.sh` on intel2.

| form | type | settings |
|---|---|---|
| k_hgi2 | kv3_hgi_v2__cl2862d491 | OT_KEEP_WIRES=ti_b, allow-congestion, SKIP_ANTENNA_REPAIR |
| k_hgi2_m7 | kv3_hgi_v2__cl2862d491 | same + M7 closed over the head cores (16 um centre column open) |
| k_hg | kv3_hg | as k_hgi2 |
| k_hg_m7 | kv3_hg | as k_hgi2_m7 |
| r_hgi2 | kv3_hgi_v2__cl2862d491 | k_hgi2 + per-core copies of the last stage (rep_t2.py), launched 00:37 |
| r_hg | kv3_hg | same |

TYPE-KVHGI2 keeps m7a (kv3_hgi_v2, intel1) and m7hg_g (kv3_hg GRT only): merged netlists, useful for the route answer only.

Judge: (1) placement / CTS setup WNS against -556 / -753 ps; (2) GRT markers; (3) DRT DRC 0; (4) signoff.json TT setup >= -42 ps, FF hold >= 0.

## 6. Results

State 2026-11-15 00:45 PST (later results in section 9). Nothing has reached detail route yet; no form is proven.

| form | stage reached | setup WNS / TNS | note |
|---|---|---|---|
| control (merged), kvgeom5 a13 | placement | -556 ps / -558k | wave kit |
| control fdC3 | CTS | -586 ps / -558k | GRT setup repair stuck near -480..-540 ps |
| k_hgi2, k_hgi2_m7 (keep) | CTS done 00:10, GRT running | placement -594 ps / -189k; CTS -366 ps / -142k | TNS 3.9x better, WNS still far out |
| k_hg, k_hg_m7 (keep) | global placement | - | |
| r_hgi2, r_hg (keep + per-core last stage) | launched 00:37 from synth | - | RTL elaborates (yosys hierarchy -check) |
| m7a (TYPE-KVHGI2, merged + M7 close) | GRT iteration 25/30 at 00:10 | - | route answer only |
| m7hg_g (TYPE-KVHGI2, kv3_hg GRT only) | GRT iteration 15/30 at 00:05 | - | route answer only |

### 6.1 Second structural finding (F1b): the last stage is one bank for four cores 770 um apart

MEASURED on k_hgi2 `4_cts.odb` (`fable-kvovf/pos_hgi2/pos.txt`):
- The q_data part (512 bits) of ALL stage banks sits at y = 980..1008 next to the top front core: `u_hst2_g`, `u_hst2_t1`,
  `u_hst2_t2`, `u_hst3_g`, `u_head2_u_ftg` at x median 172..209; only `u_hst3_t2` moved to head 3 (x median 761).
  The three stages are a chain in one spot; they do not step toward the cores.
- The loads of the last stage are the `g_front_*__q_data_in` pins of four cores per head: e0 at y = 233, e2 at y = 337,
  e4 at y = 683, e6 at y = 1002. One bank cannot be near all four.
- Worst path now: `u_hst2_t2.ti_b[1557]` -> `u_head2_e0 q_data_in[510]`, own head, arrival 1144 ps, required 778 ps. Launch
  clock arrives at 309 ps, the core captures on the early tap (-130 ps), so the wire budget is about 240 ps
  (INFERRED: about 260 um at the 110-um repair hops seen in the path). The path is 760 um.

Fix under test (forms r_*): one copy of the last stage per front core (`u_hstN_t2r_eK`, 4 per head), same data, same
latency. `fable-kvovf/bin/rep_t2.py` edits the kit `_bound.sv`; `OT_KEEP_WIRES = ti_b` keeps the copies apart. The copy
at each core then needs only a short hop; the stage before it (flop to flop, about 690 ps) covers the distance.
Cost in this form: 4 x 1575 flops per head where 1 x 1575 was declared (the generator should emit only the bits each core
reads). This is an as-built RTL change, so the real fix belongs to the KV-102 generator; the kit edit is the proof.

### 6.2 Other types with the same merge (sweep of the newest kits on epyc2 and epyc10)

`fable-kvovf/bin/sweep.py`: same-module instances whose flop count is under half of their best sibling.
MEASURED `qkh_head_gather_stage: 3 of 6 below half` on kv3_hg, kv3_hg_v1p2, kv3_hg_v1p5, kv3_hg_v3, kv3_hgi,
kv3_hgi_v1 (both classes), kv3_hgi_v2__cle0015330, kv3_hgi_v5. So the ring-class hg_v1p* / hg_v3 types carry it too.
The `ot_dp_dly` rows of that sweep (pv, hub, pc, S81 col) are NOT findings: instances there differ in width parameter;
the script does not separate that. Not followed up.


## 7. Class fix (to apply when a form passes)

0. KV-102: per-front-core last stage in the as-built generator for every hg / hgi type (section 6.1), if r_* proves it.
1. KIT-OPS-5: qwen_kvsys item env for the 9 types -> kit config.mk `override export OT_KEEP_WIRES = ti_b`; relaunch from
   synth (the netlist changes; no stage resume).
2. KIT-OPS-5: `repair_antennas` in the WF-1 allow-congestion wrapper (all dies).
3. Only if the keep forms still need it: `m7_core_close.tcl` sourced from `grt_pre_nonport.tcl` for kits with
   `kv3_head_eighth_*` cores.
4. KV-102: make the keep the generator default for replicated station registers, and add a kit gate: an as-built stage
   instance with fewer flops than its siblings fails before floorplan.

## 8. Dead ends, do not repeat

- hgi re-floor, density / routability forms, soft blockages (fd03, fd04, fdC2, fdC3, planB, v0, v1): all on the merged netlist.
- Any form without OT_KEEP_WIRES: setup stays near -500 ps.
- Counting the per-layer "total congestion" as the blocker: only the 2D markers gate.
- Per-core last-stage copy only (forms r_hgi2, r_hg; stopped 01:5x on COORD order). MEASURED r_hgi2: the copies sit at
  their cores, but the two stages before them stay at the ring (y about 993), so the long hop moves one stage upstream
  (755 um in head 2, about 1,000 um in head 3). CTS setup -365 ps / TNS -277k against -366 ps / -142k for keep only.
- Private chains without stationing (forms c_hgi2, c_hg; stopped 03:0x on COORD order). MEASURED c_hgi2: placement
  -600 ps / -303k, CTS -495 ps / TNS -379k (keep only: -366 / -142k). Global placement does not spread a linear register
  chain: the kit relay hook found the 24 chain groups and stationed 0, because the ring that drives them is not fixed yet
  when the hook runs.
- relay_mid.tcl as shipped on these chains (forms s_hgi2, s_hg; stopped 02:3x by me, superseded by t_*): stations at
  1/4, 2/4, 3/4 leave a last hop of 310-400 um on head 3, and the last station stops on the near side of a core whose
  pins face away.

- Three-stage chains on spans over 1,140 um (COORD 03:2x, FABLE-CLOSURE-STRATEGY lever 7): chain depth is
  ceil(span / 380 um); head 3 of kv3_hgi_v2 needs 4 stages.

- Keep-only forms on kv3_hg (k_hg, k_hg_m7; stopped 04:2x on COORD order). MEASURED: CTS -739 / -723 ps against -753 ps
  merged; pre-route hold repair sat at iteration 0 for 2 h 10 min (FF hold -290 ps, TNS -1.29M). kv3_hg needs plan
  stations on nine bus families (section 11.2); no kit setting closes it.

- Private stationed chain on kv3_hg alone (t_hg; stopped 05:5x on COORD order). MEASURED: CTS -737 ps / -707k against
  keep only -739 / -694k. The other bus families of section 11.2 dominate.

## 9. Update 2026-11-15 01:55 PST

- Keep only: kv3_hgi_v2 CTS -366 ps / -142k (merged -586 / -558k); after pre-route hold repair -431 ps, FF hold +3.7 ps
  with 36,635 hold cells. kv3_hg CTS -739 ps / -694k (k_hg) and -723 ps / -709k (k_hg_m7) against -753 ps / -969k merged:
  the merge is not the main limiter on kv3_hg. Worst paths of kv3_hg not read yet (its CTS report has no path list).
- Why placement leaves the stages at the ring: a two-pin register chain has the same wirelength wherever the middle
  register sits, so global placement has no force toward the midpoint.
- Forms c_hgi2 / c_hg (launched 01:45 from synth, running on epyc7, copies on epyc2/9/10): each front core gets a private
  three-stage chain from ring to core (`fable-kvovf/bin/rep_chain.py`, 24 stage copies per type, originals removed), and
  the kit's relay_mid.tcl is pointed at them (`OT_RELAY_MID_RE = ^(.*[.]u_[A-Za-z0-9_]+r_e[0-9]+)[.]`, `OT_RELAY_MID_FIT = 1`)
  so each stage is fixed on the ring-to-core line. kv3_hgi_v2 grows to 133,919 standard cells (105,305 before).
  Open: relay_mid stations a chain only when its source is a fixed flop; not yet confirmed in the log.
- m7a (TYPE-KVHGI2, merged netlist + M7 close): first global route total congestion 234 (M5 2 / M6 1 / M7 231) against 624
  in the control; the first incremental route passed without GRT-0232.
- Running: k_hgi2, k_hgi2_m7 (global route), k_hg, k_hg_m7 (CTS), c_hgi2, c_hg.

## 10. Update 2026-11-15 03:05 PST

Forms t_hgi2 / t_hg (launched 02:35 from synth, epyc2; copies on epyc7/9/10): private three-stage chain per front core
(rep_chain.py) + keep + the kit copy of relay_mid.tcl with three edits (`fable-kvovf/bin/relay_deep.tcl`, `mk_s.sh`, `mk_t.sh`):
1. a chain head with soft drivers takes its source from a deeper backward trace to fixed points, sampled evenly over the bank;
2. `OT_RELAY_MID_TAIL_AT_SINK = 1`: stations at L*j/n, so the last stage is at the sink;
3. the last station searches rings around the sink pins, not along the line. `OT_RELAY_MID_MAX_HOP_UM = 520`.

MEASURED t_hgi2 stationing log: 21 of 24 stations, 16,707 flops FIRM (the 3 left to placement are the head-2 e6 chain,
span under 200 um). Source centroids (128-137, 890-980). Last stations at y 262 / 303 / 648 / 968 for pins at
233 / 337 / 683 / 1002, both heads. Longest stage hops about 520 um (head 3: source -> g 519, ftg -> t2 425).
Timing: pending (CTS report).

## 11. Update 2026-11-15 03:30 PST

### 11.1 k_hgi2 first global route (keep only, no M7 close): MEASURED
3 congested gcells, total congestion 171 (M4 4 / M6 3 / M7 157 / M8 7); control on the merged netlist: 43 gcells, 624.
m7a (merged + M7 close): 234. All 3 cells have capacity 0 inside a head core: (193.8, 123.1) at the centre clk/rst_n pin
cluster of head2_e0; (171.6, 688.6) and (245.7, 688.0) just inside the bottom edge of head2_e4. Wirelength 8.89 M um
(control 8.76 M). So keeping the banks apart removes most of the over-core demand without closing M7. Setup going into
repair is -431 ps: this form answers the route question only.

### 11.2 kv3_hg critical paths (k_hg 4_cts.odb, TT, placement parasitics; `fable-kvovf/sta_k_hg/`): MEASURED
4,915 violating endpoints in group clk, WNS -705 ps, TNS -741k; 28 asynchronous (reset) endpoints to -496 ps.
Every family is a single-cycle hop of 0.75 to 2.1 mm straight line. The head chain is one family of nine.

| family (endpoints, worst slack) | from -> to | straight / path um |
|---|---|---|
| `u_bin_i_slg_Q_N_krsp/q` (912, -568) | landing ring at (124, 281) -> input register at (293, 1411) | 1299 / 1736 |
| astk owner `response_data` (232, -601) | owner logic at (659, 589) -> (1250, 1510) | 1512 / 1566 |
| head0 e0 / e2 `q_data_in` (853, -494) | `u_hst0_t2` at (236, 992) -> core pins at (143, 233) | 853 / 1254 |
| `u_hst0_g`, `u_hst1_g` D (568, -428) | ectl core q0 `t0` at (188, 1322) -> stage at (173, 238) | 1099 / 1587 |
| head1 e0 / e2 `q_data_in` (820, -254) | `u_hst1_t2` at (720, 991) -> (713, 233) | 766 / 1056 |
| astk `eq_p` (80, -509) | astk ex core at (1175, 627) -> (316, 1444) | 1676 / 1692 |
| ectl q3 / q2 `rsp_data` (494, -302) | `u_bin_i_slg` register at (301, 1290) -> core q3 at (976, 1368) | 752 / 1128 |
| head e0 `u_kt__kp_in` (297, -343) | core head1_e7 `kp_o` at (1170, 1002) -> core head1_e0 at (862, 233), no register | 1077 / 1269 |
| `u_bin_i_hst_*`, `u_bin_i_head_*`, `u_bout_o_ectl_*` (about 150, -559 to -633) | ring or ectl core -> face register | 1733 to 2030 |
| reset relay -> ectl q3 `rst_n`, astk owner RESETN (29, -629) | relay at (630, 760) -> (1085, 1408) / (961, 1512) | 1083 to 1103 |

Reading: kv3_hg has no stations on the buses between the ectl columns (top), the astk strip (middle), the head cores
and the faces. The private-chain fix addresses two of these families (head q_data and the g stage). The rest need
plan stations (KV-102): one or two register stages per bus, the same rule as section 6.1, plus a registered hop for the
core-to-core `kp` bus (770 um between cores). t_hg will show the chain families only; its WNS will stay near -600 ps.
INFERRED: the same holds for kv3_hg_v1p* / hg_v3 (same floorplan family); not measured.

### 11.3 Next form if t_hgi2 misses on its 520-um hops
u_hgi2: chain depth = ceil(span / 380 um) (4 stages on head 3). Caveat to settle with KV-102 before it counts: a fourth
stage adds one cycle on that chain, so either every chain of the type gets the same depth (+1 cycle of lane latency for
the type, a plan change) or the bind latency check fails. The kit form can prove timing first.

## 12. t_hgi2 after CTS (2026-11-15 03:50 PST): the chain class is closed; three other families remain

MEASURED (kit CTS report): setup WNS -328.7 ps, TNS -47.2k. Keep only: -366.5 / -142.0k. Merged: -586.3 / -558.3k.
MEASURED (my endpoint listing on t_hgi2 4_cts.odb, TT, placement parasitics, `fable-kvovf/sta_t_hgi2/`; it reads
-412 ps / -80.9k because it does not apply the kit's later corrections, so use it for the split, not the totals):
466 violating endpoints, all in group clk. None is a chain endpoint: no `q_data_in`, no stage `ti_b` D pin. The
520-um stage hops close, so u_hgi2 (depth rule) is not needed for this type.

| family | endpoints | worst | from -> to, straight distance |
|---|---|---|---|
| core-to-core `kp` / `kpv` / `gf` bus into `u_headN_e0/u_kt__*` | 430 (both heads) | -412 ps | e7 901-1081 um (-412), e6 780 um (-232), e5 602-782 um (-143), e4 480-520 um (-13 to -39); e1-e3 meet |
| reset relay `u_rs_ri_head2_u_score_rst_n` -> core `rst_n` pins | about 30 | -319 ps | 785 to 1336 um, one relay for all cores of both heads |
| `u_cland_rst_ft0_i` -> `u_cland_fstart_*` flops | 5 | -244 ps | 1090 to 1486 um |
| landing ring -> `u_bin_i_ectl_Q_N_tN/q` | 5 | -113 ps | 598 to 852 um |

The `kp` outputs leave their core 456-489 ps into the cycle, and e0 captures on the early tap, so a direct hop closes
only up to about 480 um. Budget from the numbers above: core output -> a register about 650 ps; register -> e0 pin
about 250 ps (about 260 um). e7 at 1081 um needs two registers; latency must be equal on all 16 `t` inputs of the kt
tree, so every `kp` / `kpv` / `gf` input gets the same depth.

Class fix for kv3_hgi* (KV-102, as-built generator + plan):
1. keep (`OT_KEEP_WIRES = ti_b`) + private ti chain per front core + stationing with the last stage at the pins (proved here at CTS);
2. two register stages on every `kp` / `kpv` / `gf` input of `u_kt` (uniform, +2 cycles on the kt path), stationed the same way;
3. one reset relay per core (or per core pair) instead of one for both heads;
4. a stage on `u_cland_rst_ft0_i -> fstart`, and the `u_bin_i_ectl_Q_N_tN` register next to its ring.
Items 2-4 change lane latency or the reset tree; they need the RTL owner's functional check and the bind, which a kit
form cannot give. Kit form v_hgi2 (items 1-3 edited into the kit RTL) can prove the physical side only.

## 13. Update 2026-11-15 04:25 PST
- v_hgi2 (PHYSICAL-ONLY proof, COORD approved, does not count): t_hgi2 kit + two register stages on every kp / kpv / gf
  input of `u_headN_e0/u_kt` (14 source-core groups) + one reset relay flop per head core (16), `fable-kvovf/bin/v_edit.py`,
  `OT_KEEP_WIRES = ti_b kvq`. Launched 03:58 from synth, running on epyc10 (copies on epyc2/7/9); passed the pre-floorplan
  gates. Not functionally checked: kp path +2 cycles, core reset release +1 cycle.
- Running: v_hgi2 (placement), t_hgi2 (pre-route hold repair: FF hold -237 ps, TNS -1.89M at iteration 0), t_hg (placement),
  k_hgi2 / k_hgi2_m7 (incremental route repair; two allow-congestion reroutes passed without GRT-0232).
- The real kv3_hgi* fix is KV-102's plan delta (dispatched by COORD 03:5x).

## 14. v_hgi2 after CTS (2026-11-15 05:15 PST), PHYSICAL-ONLY, does not count

MEASURED (kit CTS report, TT): setup WNS -414.2 ps, TNS -4.47k. t_hgi2: -328.7 / -47.2k. Keep only: -366.5 / -142.0k.
Merged: -586.3 / -558.3k. Placement on v_hgi2 was -173.2 / -125.6k.
Stationing log: 49 of 60 stations fitted, 11 reset relays on the nearest-free fallback, 18,354 flops FIRM. kp second
stages at y 262.9 beside the e0 `u_kt` pins (y 233).

MEASURED split (my listing on 4_cts.odb, `fable-kvovf/sta_v_hgi2/`; it reads -252 ps / -2.1k): 30 violating endpoints.
- kp / kpv / gf bus: 0 (was 430). Core `rst_n` pins: 0 (was about 30). Chain: 0.
- 7 are the new reset relay flops' own D pins (-227 to -14 ps): the long hop moved from relay -> core to
  synchroniser -> relay. The reset tree needs two levels (one mid relay, then one per core).
- 7 `u_cland_fstart_*` / `u_cland_tstart_o` flops from `u_cland_rst_ft0_i` (-252 to -33 ps), 4 `u_cland_origin` (-37),
  1 `u_cland_raw_reset_o` (-13): one-bit start / reset broadcasts over 1.1-1.5 mm.
- 6 `u_bin_i_ectl_Q_N_tN/q` (-80 ps): input register away from its ring.
- 2 `u_headN_u_score.u_rof.q` (-52, -39); 3 asynchronous and 1 path-delay endpoint under -8 ps.
All remaining failures are one-bit control broadcasts or a 6-bit register: each needs a relay stage (KV-102 reset / start
tree), not a bus pipeline. The kit WNS of -414 ps is one of these (`u_cland_fstart_ft0_o`).

## 15. Plan handle for the start / reset broadcast (answer to KV-102, 2026-11-15 05:55 PST)

MEASURED in the kit RTL: `u_cland_rst_ft0_i` is an `ot_dp_rrelay` on the last reset-tree relay (`rst_rl_225`, depth 7,
at (1274.4, 574.3) on the E face). Its Q is `cland_reset_ft0_i` = `cland_start_raw`, the raw reset of every
`u_cland_fstart_<bus>` face flop, of `u_cland_origin`, `u_cland_tstart_o` and (through a second relay) `u_cland_raw_reset_o`.
One flop on the E face feeds flops on all faces.

Read in `tools/die_plan/clock_landings.py` (not run):
- Plan key `partition_types.<type>.clock.landing_raw_branches` (schema `tools/die_plan/landing_raw_branches.py`: branches
  with name / base / stages / consumers). Consumer roles the generator honours: `fstart:<bus>` for each
  `u_cland_fstart_<bus>` (line 1610, `_branch_raw`) and `origin` (line 2165). Each consumer gets a literal copy of the
  raw relay chain at the same depth, sited next to it: release cycle unchanged, flops only.
- Tool that writes it for KV types in one event: `tools/die_plan/kv_start_corridor_event.py --types ...`, step `raw`
  (TYPE-SAFE-2-KV 11-08; data cycles 0, reset depth 0).
- Second existing handle with the same effect per face: `clock.landing_local_resets`, entries from
  `tools/die_plan/fstart_reset_leaves.py plan` (HEAD form, DIE-HEAD-76).
- No handle: `u_cland_tstart_o` takes `cland_start_raw` literally (line 1906) and `u_cland_raw_reset_o` has no role. On
  v_hgi2 these are -33 ps and -13 ps, inside R-MINIMAL (-42 ps), as are the four `u_cland_origin` flops (-37 ps), so no
  generator change is needed to pass. If wanted later: two more `_branch_raw` roles in clock_landings.py.

Consumers that need a branch on kv3_hgi_v2 (v_hgi2 CTS): `fstart:ft3_o` (-252 ps), `fstart:ft0_o` (-249),
`fstart:o_head_Q_N_N__u_fts_s_b` (-107), `fstart:o_hst_Q_N_N_sN_s_b` (-106), `fstart:ft1_o` (-71).
Not checked: whether the kv3_hgi* plan entries already carry `landing_raw_branches`.

## 16. Why `kv_start_corridor_event.py raw` found no corridor (diagnosis for KV-102, 2026-11-15 06:55 PST)

Run on the kvgeom7f plan and its strict bind RTL (epyc7 `kv-102/kvgeom7/out_kvgeom7f/bind/out/rtl`), tool tree
`kw45/kv102t18_kvgeom7f`, on a private copy; nothing was written to KV-102's directories.

Cause 1, MEASURED (all 11 kv3_hgi* failures and most of kv3_hg*): `raw_type` builds the reset chain only from
`ot_dp_rrelay` lines that carry a `// ... depth N @ (x, y)` comment (`REL`). On a type without a START plan
`cland_start_raw` is the default ring reset relay `u_cland_rst_<bus>` (`.q(cland_reset_ft0_i)`), which the emitter writes
without that comment. The chain is `[raw]`, the base loop `range(len(chain) - 2, -1, -1)` is empty, and every consumer
fails. The message prints `fails[:4]`, sorted, so `origin` always showed first. Not the 405-um limit, not the span.

Cause 2, MEASURED: consumer targets inside a keepout. The origin target is (cland_tstart_in.x, 12); on kv3_hgi_v2 that
is under head core e0, and the pin itself is interior at (159.3, 324.0). FSTART pins on the S face at y = 2.656 under a
bottom head core fail the same way (`START endpoint inside keepout or outside outline`): kv3_hgi_v3 (7 consumers), v6 (2),
v7 (2), v8 (1), and `o_kvs_hroot_Q_o_cN` on kv3_hg_v1, v1p2..p6, v3. `_free_point` does not help there: it can return a
point outside the outline (y = -4.32).

Rule (three parts, in `raw_type`):
1. a raw relay without a depth comment takes depth = driver depth + 1 and the driver's site (it is never a base);
2. an origin row inside a keepout falls back to the `cland_tstart_in` pin;
3. any consumer target inside a keepout or outside the core area uses the nearest free point INSIDE the core area.

Evidence:
- Parts 1 + 2: `fable-kvovf/bin/raw_fix_patch.py` (epyc7; rewrites a copy of the tool; sha256 of the patched copy starts
  d4fbd559b682, 16 changed lines). Per type, `fable-kvovf/rawfix/{log,rep,plan}_<type>.*`: PASS on 8 of 19: kv3_hg
  (18 branches, 63 copies), kv3_hgi (7, 21), hgi_v1 x2 (6, 18 each), hgi_v2 x2 (7, 29 each), hgi_v4 (28, 77), hgi_v5
  (29, 88); 108 consumers, longest hop 404.9 um. Still failing: the 11 types of cause 2.
- Part 3, probed only (`fable-kvovf/bin/raw_dbg.py`, function `bfree`, not in the patch): all 13 consumers tested on
  kv3_hgi_v3 / v6 / v7 / v8 and kv3_hg_v1 then find a corridor, with the target moved 4 to 27 um.
Not done: the generator and a bind on the resulting plans (KV-102 gates), and a tool test.
