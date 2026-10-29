KV-KITS-21 ASK-C (DIE-KV-27 event27, KV-007, COORD ruled YES): qkd_ahub ck[2:0] -> ck[6:0], same clock, 0 added cycles.
clock_split7.py REPO OUT -> ck7/{qkd_ahub.sv, qkd_ahub_static_dw.sv, core.json} from main rtl/hdc/nearhbm/qkd_ahub_static_dw.sv +
Codex ck3 source wrapper (codex_qkd_ahub.sv / codex_core_source.json from origin/codex/kv-kits-1028 results/codex_kv_kits_1028/ahub).
Entries (pin census of event27/qkd_ahub_pins_r27.json):
  ck[0] centre: u_rr, u_core (not am), zh relays, zh_err_q, recip loop     ck[1]/ck[2] S/N zh pairs (unchanged from Codex ck3)
  ck[3] S-W (150,50):  ap_q[94:0] (ap0, ap1, ap2[8:0]) 95 FF + u_core.am[143:0] 144 FF
  ck[4] S-E (450,50):  ap_q[171:95] (ap2[42:9], ap3) 77 FF + u_io (hs_* pin flops, start/epoch/T, hf fault) whole module
  ck[5] E-S (580,110): u_rw_s fr_epoch[15:0] + fr_rz[55:0] relay (W=72 x WF_RLY stages)
  ck[6] E-N (580,330): u_rw_n fr_rz[127:56] + fr_valid relay (W=73 x WF_RLY stages)
Proof: (1) every substitution reverses byte-for-byte to the main module text (only clock tokens / split always + instances);
(2) bench_ck7.sh (tb_qkd_ahub_static_dw, Verilator 5.050, intel2): all entries tied -> PASS; each entry stopped (CKMUT 1..4) and
north zh pair stopped (CKMUT 5) -> FAIL; MUT=1 control -> FAIL.  bench/*.out.  [CHECKED-own]
Note: an inverted-clock (half-cycle) mutant on E-S and on the zh pair PASSED in a first run (bench is cycle-level), so the
mutants were changed to stopped clocks; edge-polarity is a timing matter for the kit STA, not this bench.

KITS (2026-10-29 07:40 PDT, intel2 /srv/opentallas-scratch2/claude/kv-kits-21-1029; plan = DIE-KV-28 event27 FINAL plan_e27f sha db8fc720ab16 + DIE-KV-27 event27/ pins):
  qkd_ahub__604.8x440.64 kit_hash f94e1bc39e7aed8f  gen_ahub_e27.sh (gen_core_kit_kv: ck7 core.json, hard children, --am-g-drop,
    sigmax M7, util 0.6, plan_inst ahub, --cts-setup-only --two-mode-grt --hold-ff-margin 10; kit_rtl kv-kits-7-hubc/kit_rtl).
    Pins = r27s (snap_ahub_pins.py): DIE-KV-27 ck[3..6] were off the M5 tracks (x 150/450/580) -> snapped <= 0.024 um; ck[6] (580,330)
    sat inside u_recip (371.5..587.5 x 133.9..349.9, + 4.32 halo) -> slid to x 591.864 (11.86 um; plan note allows <= 20 um off macros).
    DIE-KV owner: adopt r27s ck[3..6] xy in the plan before strict bind.
    Measured hold (kit_modes stage --measured-hold): NOT APPLICABLE ('measured hold requires rebind reference, got bound-ff').
  qkd_kvs_pc__397.44x362.88 kit_hash 9e4bf94101943131  repin_kvspc_e27.sh: KV-KITS-16 kit + io.tcl/pins.json from
    event27/qkd_kvs_pc_pins_r27.json (1665 pins moved: 288 pc__land_es S->W, o_prev 780, o_next 299, i_prev 298), OT_HOLD_FF_MARGIN 10.
    kvs_pc V2 (~233x233): plan_e27f has no such slot (all 22 kvs_pc hard cores 397.44x362.88) -> ESTIMATE-ONLY, not built.
  KIT_PREFLIGHT (tools/die_plan/kit_preflight.py --plan-dir): ahub PASS issues 0; kvs_pc PASS issues 0.
  Place (goal place = review stop) via ot-run on intel2: /srv/opentallas-scratch2/claude/kv-kits-21-1029/place_{ahub,kvspc}_kits.otrun.log. GEOM REQ before any route.
