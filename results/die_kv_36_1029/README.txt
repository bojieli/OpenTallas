DIE-KV-36 (2026-10-29 15:54- PDT) KV die owner, receipts. Runs intel1 /srv/opentallas-scratch2/claude/die-kv-36-1029
(bind root = DIE-KV-35 bindroot (codex/kv-0822-1029@9178c9c155 tree + tools/die_plan patch per its PATCH.txt), new
files under bindroot/kv36/; die STA tools = main 49d8a0c889 die_sta_related via wt/die-kv-33-leaf, as DIE-KV-35).

KV-021b  event28b = eA2 + ECTL round-trip equalisation (COORD 15:53 ruling (1) default (a))
 1. Frames: 32 ECTL frames, krq = lane 'p2p ectl_<f>.rq' (1 port, 38 b), krs = 'p2p slg_<f>.krsp' (1 port) + rsp lane.
    eA2 left krq+krs = 6 on WN_5/WS_1/WS_6 (krsp/rsp first hop K+1) and 5 on the other 29 frames -> RESPONSE_LAT 18 vs 17.
 2. mk_event28b.py = DIE-KV-35 mk_event.py + pad the krq port of each short frame by (max - own) with the SAME K/depth
    arithmetic as the event26 compose_native ECTL equalisation: 29 frames x +1 = +29 port cycles; all 32 frames equal
    (assert).  vs event26: 151 ports changed (122 eA2 + 29 krq), sched 9341 -> 9492; regions/parts/start tree 0 changes;
    verify 3595 cycles, 0 identity/loop errors, 0 sim window violations, min margin lo 109.5 / hi 109.7 ps [CHECKED].
    Straps: 0 strap pin/width changes; 34 instances re-tied on 11 types; LEC variants 131 -> 132 (pc_v1__cl7f648944) [CHECKED].
 3. event28b plan (mk_plan28b.py = mk_plan28 form; latency table recomputed by schema.Plan.lane_latency, control 0
    mismatches): 151 ports, 147 lanes, +151 lane cycles; plan sha256 in sha256.txt (event28b_plan.json.gz).
 4. bindB1 (strict, R8 table r8_26): PARAM_REGEN clean; 30 R8_STALE only (hsl_EN_31.ao bound 43 vs table 42) [CHECKED].
 5. R8 regen on bindB1 (r8_28b.sh = codex-kv-25 r8_26.sh recipe: r8_invariant_split -> r8_write_groups prep -> r8.py pads
    --replica type --bus leaf, exempt kreq/krsp -> r8.py check --strap-pads -> write_groups check -> bindview):
    R8 PASS 3837 groups, 0 unequal/inversions/conflicts; pad_flops 71565 -> 71549, max_pad 17; write group dcal_bcfg ok;
    table diff vs r8_26 = 238 leaves (bound/landed +1 members of the K+1 ports) [CHECKED].
 6. bindB2 = strict bind event28b + eB sidecar + r8_28b table (recipe_kv27f_eB2.json): 0 errors, 160 partitions, 56 types,
    unbound/tied/undriven/multiply_bound 0; count-strap audit PASS 21888 bits (= control); param_regen ECTL 32 frames
    RESPONSE_LAT 18 (control 17), QK_ISSUE_AGE 34 unchanged (floor) [CHECKED bindB2_report/param_regen].
 7. Kit RTL vs control (bindCtl = copy of DIE-KV-35 bindOld, event27f + recipe_kv27f), comments stripped:
    pc_v1 x3 / pc_v3 / pc__cl254f2e73 / pc__cl5a95b461 / hroot / hub_Wo: 0 functional lines differ (only lane-cycle
    comments; count straps are parent ties).  ALL 8 hg types (kv3_hg, hg_v1, v1p2, v1p3, v1p4, v1p5, v1p6, hg_v3): exactly
    1 line each = qkd_ectl3_kiss_st RESPONSE_LAT(17) -> (18) [CHECKED hgrest.otrun.log].  No hg kit exists yet (OWNERS:
    NEEDS-KIT / PLAN-STRUCTURAL), so nothing signed goes stale; every hg kit must be generated from event28b (bindB2).
 8. CA on eventB bind (gate.sh, proofA): spice_edge TT lo 128.5 / hi 129.8, FF 113.8 / 255.6 PASS; spice_cell TT 105.0 /
    106.4, FF 105.2 / 225.3 PASS; start-skew 0/1687; intra TT setup 297.35 / 289.36; hold UNMEASURED (no kit views)
    [CHECKED-own readout, NUMBER-CHECK pending].  Note: hi margin fell 488 -> 129.8 (edge) / 453 -> 106.4 (cell) TT on
    the padded krq ports (same depth, +1 cycle) - still >= 100.
 TOK: ECTL RT now +1 on every frame (not req+1 and rsp+1): per-layer serial estimate <= +6 -> 4759.1 tok/s (-0.09 %);
    hard bound all 151 cycles serial per layer = +5436 -> 4662.6 tok/s (-2.11 %) < 5 % -> no OWNER line [arith CHECKED,
    class mapping UNCHECKED].
 KV-014 q0 LEC (fixed lec.py 0e4c244db8): intel1 die-kv-32-1029/q0lec/lec_fix/lec.json EQUIVALENT 19389/19389 compare
    points, differs 0, undecided 0 (10451 s); mutant (c_mut) NOT EQUIVALENT [CHECKED].
