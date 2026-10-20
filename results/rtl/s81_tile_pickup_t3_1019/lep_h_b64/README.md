s81sl_lepmuh_b64 -- MU endpoint (ot_s81sl_lep_mu_h, RX_SRAM=1, IN_PIPE=1) gate kit, LEAD2-S81/LEPCAP 10-19. Structural successor of
s81sl_lepmuh_sf (gate FAIL: DPL edge-spacing/padding on the 32.4 um std band, ~85% placed fill).
Branch claude/s81-lepcap-1019 (RTL on codex/mu-lep-rxsram-1019 d37b5dae1 + IN_PIPE eec2dca41).

Changes vs _sf: (1) one full-width std band y259.2..324.0 (64.8 um, 30.5k um2); macros above the band moved +43.2
(TX banks 3/4 -> y345.6/432.0, RX rows -> y518.4/561.6), outline 475.2x604.8 (aspect 1.27), all origins on the 43.2
lattice, channels >= 20; clk/rst_n W pins moved to the band centre (283-299). (2) IN_PIPE=1: one face register stage on
ro/t_host/t_kd/mu_c (+1 edge each, same relative timing; INBOX line in lanes/LEAD2-S81.md) and 6 KEPT
ot_s81sl_lep_vcopy copies of ro[0] (and of t_kd[53] in H) feeding the 138 frame-slice / 18 push-group / 2 lane
landing registers (<= 28 loads per copy; input nets now 7 loads, were 160 / 139). ot_s81sl_lep_vcopy in
SYNTH_KEEP_MODULES (keep_hierarchy, non-parameterised: no paramod rename). A: host-only keep entries dropped
(they matched nothing at HOST_EN 0 -> _sf keep_modules FAIL).

Benches (Verilator 5.050, ot-epyc6, results/rtl/s81_lepcap_1019): exact s1/s5 PASS with IN_PIPE 1 (reference fed
through one TB face register: all same-cycle checks hold at +1); IN_PIPE 0 regression PASS (default unchanged);
mutants FAIL with committed witnesses (A: TAGDROP/LANDCUT/STALEHD/VSKEW; H: HSTAMP/TAGDROP/LANDCUT/KSOFF/VSKEW;
VSKEW = one copy group bypasses the face stage -> TX regional-state assertion).

SAFE-DESIGN checklist (pre-gate; gate packet re-checks 3/6/7 on actual placement):
 1 Pins: PASS -- source-registered pin flops (rop/thp/tkp/mcp in, lo/ri/ml_wd/mu_rt/f_* out); reset_landing 2 stages.
 2 Reach: PASS by geometry -- band centre y291.6; farthest macro / face pin ~ 290 um from the band (< 405).
 3 Fanout: FIXED -- ro[0] 160 / t_kd[53] 139 -> 6 kept copies <= 28 loads; gate synth netlist must hold 6 (A) / 12 (H)
   ot_s81sl_lep_vcopy instances.
 4 Depth: PASS -- mapped depth 350 ps (H, _sf census); IN_PIPE adds only register stages.
 5 Storage: PASS -- RX + TX in SRAM macros (20), no runtime-indexed flop tables.
 6 Floorplan: FIXED -- 64.8 um full-width band (placed-area basis ~43-46%, synthesis 27-29%), 43.2 lattice, aspect 1.27.
 7 Clock: gate-checked -- clk W pin at band centre, one root ~18.5k sinks (guidance only); spread <= 80 TT+FF required;
   io_hold 0.03, hold margin 0.045.
 8 Schedule: +1 edge on ro/t_host/t_kd/mu_c handed to LEAD2-S81 INBOX (static; no credits added).
