# FABLE-FIX-HEAD-LEP0N-R7 (Fable, 11-21 19:55-20:4x PST): hd_lep0N one-cut split at 846.72, BLOCKED at the coll_o0 window (successor of R6)

Predecessors: lanes/handoff/FABLE-FIX-HEAD-LEP0N-R6.md (-R5, -R4 still valid for RTL facts and the rename map).
Lane dir intel2 L=/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-r7 (clone = lane clone of main cd2cd11c4e + uncommitted
type_split patch, plan/, tmp/, cut/). Proof dir epyc10, same path L/cut. Hub logs intel2 ~/fable-fix-head-lep0n-r7/.
No kit launched, no plan event, no live tree written, nothing resealed. R6 and event trees were only read.

## In flight (2 units, adopt both)
- oth-ubuntu-1136304-1795317736 (epyc9, R4's six-content 0-cycle equivalence). Still in "6. EQUIV_INDUCT" at 20:3x PST.
  Pass = PARTS_EQUIV_PASS in intel2 ~/fable-fix-head-lep0n-r4/parts_equiv_e9.otrun.log. NOT proven yet.
- oth-ubuntu-1452654-1795321534 (ot-run client pid 432115 on intel2; epyc10, L/cut/prove_cut.sh): cut form (RA 4) == six-content form. Log
  ~/fable-fix-head-lep0n-r7/cut_equiv_ra4c_e10.otrun.log, proof log epyc10 L/cut/proof/cut_equiv.log. Pass = CUT_EQUIV_PASS.
  At 20:3x PST in EQUIV_SIMPLE, 372,023 cells; hide cones 98 (forward) and 1,129 (backward) wires. NOT proven yet.
  Three earlier runs of mine were cancelled by me (RA 2 form; an empty backward cone; a relaunch that collided with a
  cancel that had timed out). If $equiv cells stay unproven: look for same-named wires two edges apart that the hide
  cones (prove_cut.sh, @fwd / @bwd) missed, and hide them in the gate.

## BLOCKER for COORD: no street cut passes type_split, 846.72 and 855.36 included
Bus coll_o0 (512 bits, N face, type frame x 831.28-1036.48) straddles every cut in 846.72-967.68. Its pins abut
lk_WN0 (hd_serdes) coll_i0, and HEAD ports carry no die window: both types place pins from their own bus window. hd_serdes
has 12 instances whose coll windows also face hd_st_turn, hd_st_n3_turn, hd_mesh, hd_ctl_n, hd_host_e and hd_st_k5, so the
window cannot be clipped or moved. Tool result (L/plan/split_spec_846.json): "type_split: FAIL hd_lep0N port
coll_WN0_d__0 window [831.280, 1036.480] straddles a cut [846.72]". R5 census item 4 named this; R6's option A did not.
Options:
- (U, my recommendation) cut at x 820.8 in the 16 um gap between coll_i0 (ends 815.28) and coll_o0 (starts 831.28), and
  move pairs 1 and 2 west by 25.92 um (x 69.12 -> 43.2, shape and y kept). Price: the W channel shrinks 69.12 -> 43.2 um,
  and 11 die_clock_tree reserved sites plus taps clk_t216, clk_t220, clk_t19 in x 43.2-69.12 must be re-seated by the HEAD
  die clock (the die clock must retarget two pieces anyway). Measured with tmp/premove.py 820.8 25.92 _u; with it
  type_split passes the window step and goes on to the gaps below.
- (Q) tool support for a bus split by the cut (W owns coll_o0 bits 0-49 as its own N bus): type_split, gen, portbind,
  LATCHECK and a per-bit COL0. Days.
- (R) compress hd_serdes coll_i0: 12 instances and 6 partner types. Dead.

## Second finding: type_split has never run a HEAD type; three gaps fixed, one open
Patch L/plan/type_split_head_r7.patch (uncommitted in L/clone, NOT pushed, no tests yet):
1. ports without face / window_um (13 of 15 lep0N ports) crashed _port_ends and _clip_windows: new port_face() resolves the
   face through schema.Plan; clip_windows fails closed on a straddling type-frame window.
2. core taps u_rg<i>.u_pair.clk sit in the band, 250 um off their pair: accepted when the tap lies in its core's piece.
3. HEAD per-bus landing pins cland_{dn,up}_{ready,fault}_<bus> follow their bus; rst_start_raw_<n> go by position.
OPEN (next failure, cut-independent): landing_contract.collector_children are {bus, ready, fault, xy_um, seam} on HEAD
(monitor "region", root node cland_up_ready_lepk_o0), not {part, index}; _landing_contract raises KeyError 'part'. The
collector / local-source / band split needs the HEAD per-bus form before any HEAD type can split. Expect more gaps after it
(sidecar rows, START pins). Then gen.py rtl, strict bind and LATCHECK, none of which has seen a split HEAD type.

## Done
- Step 3 answered: the lep0N START / status keys (landing_reader_start, landing_writer_start, landing_status_anchors,
  landing_status_input_stages) are written by tools/s81_head/head_sideband_street_rows.py (NF14; default --types
  hd_lep0N,hd_ctl; report prep/nf14_report.json). Re-derive per piece with --types hd_lep0N,hd_lep0N_w --redo after gen.py rtl
  (it reads the wrapper for the reset relay table). reset_tree_anchor: tools/die_plan/reach_fix.py. reset_start_raw_exports:
  head_reset_exports.py. Hub RFPL / relay_sites: head_rf_plan_delta.py (the hub loses 8 K leaves, so leaf indices shift).
- Pre-split plan L/plan/plan_cut_pre.json (cut 846.72) and plan_cut_pre_u.json (820.8), by tmp/premove.py from R5's
  plan_parts.json; reports premove_report*.json; no problems for 846.72:
  - u_land g_t[0] -> (861.0, 298.16), g_t[1] -> (861.0, 254.96): the street stack of g_t[2..4] continued south. wdq_bank0 / 1
    beside them (x 955.5-962.5). Reset local taps (898.56, 311.04), (915.84, 293.76) -> x 855.36. Read hop g_t[0] -> mrd_bank0
    is about 350 um: watch setup, re-seat mrd_bank0 if it fails.
  - RX banks: g_rx[1] b3 -> (941.868, 708.492), b0 -> (941.868, 734.412); g_rx[2] b0 -> (967.788, 604.812), b3 -> (864.108, 483.852).
  - KRX form changed from R6's: lanes 1, 2 take KR 4, RA 4 (hub RXA 16'h0440, KRX 16'h2440). The region keeps r0, s0, r2 and takes
    the old hub row s1; the boundary pair stands for hub r4, s2. No new E row, no W row moves. Reason: K pins span x 72-462
    on the pair's K face, so two W stages cannot reach the cut within 405 um.
  - TXI 4 -> 2: surviving g_s[0], g_s[1] on the W sites r2, s1. TX read rows renamed to u_rg<i>.u_txl.g_tx[i].od (the reg left
    the hub in the TX extraction; lo<i>_d has no cell in parts.il). Flop names after synthesis not checked.
  - u_rg1 / u_rg2 = ot_s81hd_lep0N_rgnl, nets rs1 / rs2 removed, hub ports rs1 / rs2 open.
- RTL L/cut/proof/ot_s81hd_lep0N_rgnl.sv (generated by cut/cutgen.py from R4's rgn): local reset fan, ot_rst_fan depth 5
  for the K leaves, + ot_rst_relay_tree3m (4 groups, 107 locals) for tx_rst / tx_rt, i.e. the hub's release edges (5 and 8).
- Equivalence set-up L/cut/prove_cut.sh: eq_ref (six contents) vs eq_gate (cut form, two-flop pair on h2r1 r2h1 h2r2 r2h2),
  rst_n held 1 in both. Declared delta: tx_ovf of lanes 1, 2 two edges later. NOT covered: reset release (local fan vs hub
  leaves) and the flush of the reset-free pair flops; both need a small bench.
- R6's plan_parts_moved.json was not built or used.

## Work order left
1. COORD rules on the blocker. 2. HEAD collector form in type_split, tests, ot-push-main. 3. Sources: the parts RTL,
split_tx_io_stages.sv and rgnl are in no plan `sources` list and not on main; private tree (nlink 1) with them. 4. PD rows
(RX row y 638.28 break, coll_i1 / coll_i2 rings, measured OT_PREGRT_HOLD_R2R_MARGIN as --ab). 5. coll_i0: pre-plan with ONE
internal station so that fold_legs + the pair keep 2 stations (0 cycles); not done. 6. Split, re-derive keys, strict bind,
LATCHECK, private-spec kits (wave env), routed LEC, sign-off. 7. e1b: HEAD-START-R18 told to keep the lep0N START rows out
until the split plan exists.
