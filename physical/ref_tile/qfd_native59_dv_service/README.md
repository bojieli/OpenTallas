# qfd_native59_dv_service kit m1 (MU-D2D-OVL 10-19)
RTL: rtl/qwen_split/qfd_native59_dv_service.sv #(NU 4, MCTX 1) = d2duser epoch user tag (c93aee75b) + main QXF-LINK q_open +
S-QWCOL reset distribution / formatter eb_r copies (025424c30) + two operation context slots (MCTX). Outline / faces / pins = n2.
Benches: job.json bench stages (Verilator 5.050), witnesses results/rtl/mu_qwen_1018/d2d_ovl/n59/; compute<->KV pair on the MU seam
results/rtl/mu_qwen_1018/d2d_ovl/n59/xdie_mu_seam_r2 (12/12 as expected) + xdie_r3 (f1_n59_legacy_window = the MUT 4 Q-window witness).

SAFE-DESIGN checklist (owner 10-19):
1 Pins: PASS -- RTL flop-first at every pin (p_* registers, every output a flop); reset_landing 2 stages + 8 kept regional copies.
2 Reach: PASS -- flat tile 777.6 x 518.4, every pin registered; no die-level wire inside.
3 Fanout: PASS (watch) -- reset copies (8), formatter eb_r (16 kept); new slot steering (fs/bs/nf) drives only valid/slot gates
  (~20 loads), payload buses are not gated; check the synthesized netlist for merged keep copies (gate textbook_lint).
4 Depth: PASS (gate decides) -- slot merge = 2-way AND-OR of registered child outputs; no new arbitration; no in->out path.
5 Storage: WAIVED -- the 16 kb Q seat bank stays flops (8 seats written per edge at dd-chosen addresses: an 8-write-port bank, not
  an SRAM pattern); writes and reads are decoded constant-index slices (n2), as in the closed n2c view.
6 Floorplan: PASS -- no macros; outline = closed n2 slot (dv2f14bn); aspect 1.5.
7 Clock: gate --cts measures pin-flop spread (<= 80 ps TT+FF required); route hold margin 0.03.
8 Schedule: PASS -- static; MCTX adds no edge (both slots are the as-built children, steered on the same edges); NU/MCTX 0 path
  identical to the single-user block (benches regress_nu1 / mctx_serial).
