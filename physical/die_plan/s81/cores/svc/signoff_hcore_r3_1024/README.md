# svc attn_hcore r3 (WPRE re-kit) routed sign-off, 2026-10-24 (S81/KITS)

Run: intel2:/srv/opentallas-scratch2/claude/s81/hcore/ot_s81c_attn_hcore__157.68x259.2_r3 (kit = ../kits/ot_s81c_attn_hcore__157.68x259.2_r3).
signoff.py (tt,ff; 60/25 ps) ran 17:49-17:55 PDT on the routed 6_final.odb/.spef.

VERDICT: NOT SIGNED
- TT setup -4.91 ps, TNS -35.29, 18 endpoints. Worst 3 = reset RECOVERY: rst_n (input, set_input_delay -max 0.5T vs vclk)
  -> ~170 um buffer tree -> DFFASRHQN RESETN (u_h.g_h[0].u_hdp.g_c[0].u_c.g_a[1].u_a.g_f4.u.u.y[*]). The rest: reg-reg
  u_h.g_h[0].u_rc/q[2] -> u_h.g_h[0].u_hdp.g_m[16].ab[31..26] (-2.46 .. -0.85).
- FF hold +8.56 (PASS); DRV slew/cap 0; fanout max 32; DRC 0, antenna 0; pins PIN_AUDIT 1214/1214; sdc_lint PASS;
  face_guard PASS 1212/1212 (raw yosys); clock insertion pin-flops TT 249.8-267.6 (spread 17.75, INFO), FF spread 16.9.
- Cells 404,873: OVER the 400k-per-OpenROAD-run cap (rule). The next re-kit must come in under 400k.

Review of the routed images (img/): pure std-cell core, no macros; W face full-height ld_* pin column and N face ib[576]
full width; congestion heat is a continuous red column along the W pin column plus scattered hot spots (no blocked
region); worst-path image shows the reset net climbing ~170 um up the W side from the S-face pin to the g_c[0] flops.

Cause / next: the reset fails because the core takes rst_n as a one-cycle timed input into ~28k async-reset flops through
a deep buffer tree. Owner decision 2 (pipelined synchronous reset, relays <= 405 um, equal depth, no recovery waiver)
needs an in-core reset relay stage (RTL) or the RESET lane's kit change; reg-reg -2.46 needs a small RTL/placement fix on
the u_rc -> g_m[16].ab decode. Not re-launched: waiting for the RESET lane tool (lanes/RESET.md not yet published).
