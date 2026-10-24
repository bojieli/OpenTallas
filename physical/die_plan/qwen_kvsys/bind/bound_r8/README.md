Qwen KV/system die plan v3.6 bound by tools/die_plan/bind.py, land_align=r8 + KV-P6-PV pads + KV param regen (BINDER3 10-23, kv39)
plan: claude/kv-p5-1023 @60404093c physical/die_plan/qwen_kvsys (v3.6: kv3_hg_v1 -> r1..r5, lat_v36), conns
../plan_cell_conns_v36.json (= v34 with kv3_hg_v1 copied to r1..r5), rewires plan_rewires_v34.json.  As-built rtl6 qkd die
@e33504a6f (bind.f paths relative to that tree overlaid with the v3.6 plan dir + this directory).  Recipe
../asbuilt_v36p.json (BINDER2 recipe + land_align r8, land_r8_exempt fault/health = KV-P5 r8_fault_exempt.py,
land_r8_extra ../kv_pv_pads_v36.json, clock_roles clk_hbm_<Q> -> clk_hbm, param_regen ../kv_regen36.py).
R8: KV-P5 table r8/qwen_kvsys_r8_landing.json @60404093c (bus leaf, replica type, bus_sub) + KV-P6-PV table
kv_pv_pads_v36.json @0e7719db9 (authoritative per id: 3,036 replaced, 64 added; INNER intra-partition delays: 128 edges
re-sized, 1,344 leaf self-loops no-op).  stale 0, uncovered 0; crossing pad flops 171,304 (shared per in-bus bit), max
pad 41; intra-partition ot_dp_dly flops 1,166,698 -> 698,218 (net die flops -314k vs the r8-only bind).
param_regen.json (kv_regen36.py = KV-P5 rules @29d54b0e2 on this landing, kv_param_rules_bound_v36.json): ECTL
RESPONSE_LAT 80 -> 12, QK_ISSUE_AGE 91 -> 34 (max(34, RL+11)); AHUB AP_OFS WS/WN/ES/EN -> -47/-47/-47/-46, FR_OFS -7;
seq KVN_A0 32 -> 34 (KV-P6 formula: v3.6 kvn 14->39, att_rx 11->34; KV-P6's 29 was the kv35 depths); PV ctl TRUNK_D
54 -> 56, FLAG_D 58 -> 0 (KV-P6-PV table).  OPEN (record.open_blockers): vport DQ 16 > 15 on *_3 + vport launch shifts
+22..+51 (boot DQ + W request-lane pads, not in the table); kg row skew 17-19 edges; RH b stream 2 edges early; boot
values (vport RT, cfg_fia, P0/P1 +2, hdr +15/+16, down/ret, d2d ages) -> KV-P6-BOOT image.
Proof: unbound / tied / undriven 0.  verify_report.json PASS (3,359,267 matched, 0 mismatched), lint 0 errors.
port_bind_strict PASS (76 masters / 160 instances).  76 types (kv3_hg split 4 by the PV hg read pads).
G3 kit RTL (KV-P6 hub singletons): bind.py kit-rtl PLAN --out <bind out> --type kv3_hub_C ... (hub_C kit lint 0 err).
