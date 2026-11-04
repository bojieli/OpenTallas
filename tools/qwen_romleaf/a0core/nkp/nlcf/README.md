# NL A0 tile conservative form v3 (DIE-QC-66/CLK, OWNER directive 11-03)

Kit: qfd_tile_nl_a0c_a0nl14icg1r1p7c = the NL v2 kit (claude/die-qc-66-nkpipe-1103@42849e677a4, a0nl14icg1r1p2)
with two die-local changes; the NL v2 build continues, first to sign wins.

1. RTL form: VERILOG_TOP_PARAMS NKP 2 -> NKP 7 (all three ot_qwen_w12_matvec_part depth cuts: bit0 K-limit prep
   c32/kdm registered, bit1 raw XTX rung 0 + per-leaf round (v2), bit2 round-step sum). 0 visible cycles, so no
   schedule change for TOK-VERIFY-1. Targets: the v2 CTS worst setup path g_gm_fast.g_kl[0].sa -> kdif[1][18]
   (FEED-FORWARD, ~872 ps cell / ~32 ps wire, slack -160 ps @ CTS) is the bit0 cut.
   Bench: tb_a0_nlp7.sv (= tb_a0_nlp.sv, u_k1 NKP 7) strict output + engine-state compare vs NKP 0.
2. Clock form (PROBED, NOT IN THIS BUILD -- two strikes): rr_balance.tcl (PRE_CTS via b3_pre_cts.tcl, OT_RR_SPLIT=1 OT_RR_BALANCE=1): ck_de register sinks
   split into <=5000-sink regional entries (BUFx24 root at each region centroid), TritonCTS builds one tree per
   entry, then right after CTS (before the FF hold gate/repair) every entry is delay-chained to a common insertion
   target T = max(macro ck_de anchor, entry means) -- a balanced multi-entry, not free CTS per root (the naive
   5-root split measured hold -209.6 / 2239).
Pins: every port already registered (ot_unreg_pins.txt 0, OT_KEEP_PIN_REGS=1); util/place density 0.45 unchanged.
probe.sh = CTS-only probe of the clock form on the v2 placement; build_v3.sh = the one build + sign-off + RE-SIGN.

Probe 11-03 19:37 (v2 placement, CTS-only): entries equalized to 915-927 ps (5 entries, max 4616 sinks), but the split
lifts register insertion to ~920 ps while ck_regs (port side) stays ~600 and the macros 568 -> FF hold -260.4 / 2902
(naive split -209.6 / 2239; v2 single tree -100.9 / 2401, repaired to +15 at CTS).  Two failed split forms -> the
build keeps the v2 single gated tree; a common target across ck_de_regs + ck_regs + macros is the open item.
Bench NKP 7 vs NKP 0: NKP_PASS MUT=0 (14000 checks, strict_out 0, engine_state 0); MUT 3 / 7 controls FAIL as required.
