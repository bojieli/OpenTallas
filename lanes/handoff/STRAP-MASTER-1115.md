QC strap master (FABLE-PD-QCC-0740 R1), built 11-15 by CORE-ROWS-1115 on epyc9. STATUS: kits built, running build -> sign-off (+ hold ECO if FF hold only); NOT signed yet.

Master: sta_region_strap_s1 (162x162, same plan pins + 10 strap pins = 504 pins). Twins: util 0.5 (strap_u5) and 0.4 (strap_u4), default yosys frontend.
Kits: /srv/opentallas-scratch2/claude/core-rows-1115/strapb/s1_<u5|u4>/sta_region_strap_s1/kits/sta_region_strap_s1_synth0
Pins file: .../strapb/s1_u5/sta_region_strap_s1/pins.json   LEF/lib: after sign-off, from the kit signoff/export (not yet produced)
Strap pins (M5, S face, x 91.788 + 0.288*i, y 0.048, direction in): strap_skew_n[4:0], strap_skew_s[4:0]
Encoding: unsigned binary = the SKEW depth in edges that the bound RTL passes as .SKEW_N/.SKEW_S. Verified range 3..24.
 S4p 8/9, 8/10 ; S4q2 9/10, 9/11 ; S4v2/S4fw bound state 14/14 (HI_PAD 0).  Tie constants: strap_skew_n = 5'd<SKEW_N>, strap_skew_s = 5'd<SKEW_S>.
Built state: S4v2/S4fw bound instance (defaults, HI_PAD 0, SKEW 14). HI_PAD is NOT strapped: S4p/S4q2 types with HI_PAD 17/18 need another master or a HI_PAD strap.
RTL: /srv/opentallas-scratch2/claude/core-rows-1115/strap/qfd_dv_s8s_skew_strap.sv (sram_delay_t: read offset + valid tap from dd; tap_delay_t: 2-bit shift chain with tap mux replaces the c0/c1 ring pair, no latch ring)
Generator: .../core-rows-1115/mk_strap.py (rewrites the nb0 core; nb0 itself untouched). Bench: .../strap/tb_skew_strap.sv: 22 depths x 2000 edges lock-step vs qfd_dv_s8s_sram_delay and ring c0+c1: 44000 compares, 0 errors; an off-by-one tap mutation fails (33472 errors).
Timing note: strap pins are declared quasi-static (set_false_path -from strap ports), as for ID straps.
Design deviation to review: the 2-bit valid/bad chain is plain flops (24 deep), not the n32 latch ring.

param_wrap.wrap_bound: cannot emit strap ties today. It (a) only renames the instance header `<base> #(params) inst (` to `<master> inst (`, requires the parameter text to match exactly, and leaves the port list untouched; (b) wrapper_sv is a pure pass-through from PORTS[base], which has no entry for qfd_dv_s8_station_tail1_nb0.
KIT-OPS-5 change: allow hard_core.param_wrap {"base":..., "straps":{"strap_skew_n":N,"strap_skew_s":S}}: PORTS entry for the nb0 base incl. the strap ports; wrap_bound drops SKEW_N/SKEW_S from the exact-match text (or matches them against the straps) and inserts .strap_skew_n(5'dN), .strap_skew_s(5'dS) into the instance connections; master name independent of SKEW. Also the bind/G0 check from R1 (param_wrap vs bound instance).

== UPDATE 11-15 (COORD r90 follow-up) ==
Variant 2 (HI_PAD strapped too): master sta_region_strap_s2 = s1 + strap_hi_pad[4:0] (value = HI_PAD edges, 0..24, 0 = wire; M5 S face after the skew pins; 509 pins). Twins util 0.5/0.4 launched (ot-run, epyc9). Logs on epyc7: /tmp/core-rows-1115-strap2-<u5|u4>.log. Kits: /srv/opentallas-scratch2/claude/core-rows-1115/strapb/s2_<u5|u4>/sta_region_strap_s2/kits/sta_region_strap_s2_synth0. s2 covers S4p (HI 17/18, 8/9..8/10), S4q2 (9/10..9/11), S4v2 (0, 14/14). Cost: pad chain depth 24 for 74 bits = up to 6 x 74 extra flops vs the 18-deep build.
Ties: S4p h17 17/8/9; S4q2 h18 18/9/11; S4v2 0/14/14 = strap_hi_pad, strap_skew_n, strap_skew_s.
LEC (equivalence of strap core vs original nb0 core):
 (a) text diff of the generated core vs the original nb0 text: 21 changed lines = port decl + the 6 delay instances + 3 pad instances only, nothing else (/tmp/orig_nb0.sv vs sta_region_strap_s2_core.sv).
 (b) yosys SAT, free inputs, init zero, rst_n 1, depth 72 steps, compared from step 48, original-form delay/pad blocks (params) vs strap-form blocks tied: (8,9,HI17) (9,10,HI18) (14,14,HI0): all no counterexample; a mutated tie (n 9->10) gives a counterexample. Files /srv/opentallas-scratch2/claude/core-rows-1115/strap/lec/lec_*.{sv,ys,log}.
 This is BOUNDED (72 steps) block-level, composed with (a); not an unbounded whole-core sequential LEC (lec.py needs register correspondence, the delay structures differ by design). Plus random lock-step benches tb_skew_strap/tb_pad_strap, 0 errors at every depth.
n6 masters: ALL THREE n6 ECOs SIGNED (SIGNED, 1 ECO iteration; LEC PASS for h17_n6_s7 and h18_n6_s8; h18_n6_s7 LEC still running). The ECO_RC=1 lines in /tmp/core-rows-1115-eco-h18_n6_s7|s8.log are my duplicate relaunches (eco dir exists), harmless.
