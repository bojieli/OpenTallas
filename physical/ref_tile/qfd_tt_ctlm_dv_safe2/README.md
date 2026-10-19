# qfd_tt_ctlm_dv_safe2 — structural successor of safe1 r6 (QW-CTLM, LEAD-QW 10-19)

Source = codex/qw-ctlm-safe-recut-1019 @5825f8e82 (unified ctx_x/FCTX/INIT52,3/expanded 3-ROM/PINREG1 RTL, 6 SRAM + 3 OPROM + h16c).
The landed-parent RTL `rtl/qwen_dv/lp/qfd_tt_ctlm_dv_lpf_lp.sv` is byte-identical to safe1 (lp.py gen re-run; only the SDC and
record changed), so the committed landed-lockstep / LMUT / OPSEG / observer witnesses of that RTL still apply.

What changed vs safe1 (why r6 failed GPL-0305: 3,607 um2 of unowned top cells, incl. 2,351 um2 created by timing-driven repair,
forced into a 43.2 um seam; the repair flood came from the direct quarter-period landing budget, ideal -1.667 ps at sign-off):

1. **Complete comb+seq partition** (`lp_cone_regions.tcl`). Every movable std cell is owned: exclusive cones by clock root, mixed
   cones (landing read muxes, cross-root glue) by their DESTINATION root (reverse ownership), rootless -> core. No shared seam.
   core = x2.16-453.6 (W SRAM block) + x453.6-775.44 / y280.8-388.8 (the core-clocked OPROM row); hr = x453.6-775.44 / y43.2-280.8
   (h16c). Both span y43.2-388.8. Fill incl. macros ~56% (core) / ~80% (hr box is mostly h16c; its std util ~14%); the Tcl prints
   per-region std utilisation and FAILS above 60%. The N/S pin bands (~63k um2) stay top-level free area for cells created later
   by repair/CTS.
2. **Landings use the standard LANDING-CONTRACT**, not the direct quarter-period model: D4 ring, read at full-cycle age K=E=2,
   `set_multicycle_path -setup 2 -hold 3` ring->read (window (2-4)T+t_hold < dL < 2T-t_cq-t_setup). The 60+150 / 25+150 ps
   cross-root reserves are kept. No quarter-cycle reads, no phase choice. (`landing_direct_timing: false` in the lpf spec.)
3. **native_cmd[379:0] N -> E face** (M4, 0.192 pitch, y78.7-151.5): adopts the geometry proven in 5825f8e82 on the actual
   failed ODB (all 2,992 pins on legal tracks, PG/via overlap 0) — fixed hard-port -> pin reach 563.8 -> 50.4 um. The die GEN must
   bind native_cmd on the E face (top-down pin assignment, tile not closed).

Fallback in parallel (PARALLEL rule): `qfd_tt_ctlm_dv_safe2n` = identical RTL/SDC/pins/macros with NO placement regions.

## Safe-design checklist (owner 10-19)

| # | Item | Result |
|---|------|--------|
| 1 | Pins registered, reset landed in 2 stages | PASS (inherited): PINREG / OT_KEEP_PIN_REGS=1, reset_landing.json. dh_user enters through an hr pin register, lands (landing 1) into core `dhu_q`; the op-start leaf's dh_user output is unconnected, so no comb in->out path exists in this kit. mu_fault: pin reg -> landing 4 -> `mu_fault_q` -> `op_fault` -> cf STATUS (already in RTL 5825f8e82). |
| 2 | Reach <= 405 um per cycle | fixed for native_cmd (563.8 -> 50.4 um via E-face recut). The other r6 floorplan estimates (>500 um) are not placed paths; the gate's placed textbook lint (>500 um per stage) decides. |
| 3 | Fanout <= 32, kept copies | PASS by construction (inherited): reset same-edge copies max 32 (lp_reset_copies + audit), CALPIPE kept selector/mask copies (Yosys inventory 08:11). Gate lint re-checks. |
| 4 | Depth <= ~600 ps / 20 levels | Pending the gate's synthesized-netlist depth lint and CTS timing. |
| 5 | Storage > 2 kb in SRAM; delay lines >= 3 deep as rings | PASS: CALPIPE per-user FIFOs and programme store are SRAM rings (4+2 x 64x512). The 26 landings are 4-slot rings in 24-bit chunks (96 b per local ring, counter-indexed, no deeper delay line); a crossing ring cannot be an SRAM (single-clock 1R1W macros). No flop delay lines >= 3 deep remain. |
| 6 | Floorplan | Macros on the 43.2 lattice (inherited); one std-cell band per region, regions abut; aspect 1.8; total fill 46% from synthesis area. Pin faces: E 399 pins (native_cmd 5.2/um), N/S <= ~2/um. WAIVED-with-reason: the 64x512 SRAM abstract itself has ~10.2 pins/um on its W/E faces (macro property); escape is proven only by route DRC. |
| 7 | Clock | two regional roots (ck_core W/ROM row, ck_hr h16c) with landed crossings; h16c hard-child clock reference; io_hold margin 30 ps (inherited). Spread <= 80 ps TT+FF measured by the --cts gate. |
| 8 | Schedule | unchanged: same RTL, same landing ages (+3 per landing, outputs +6 / tl +3) as the record; no new cycles. |

Gate: pre_route_gate --remote auto --cts (both variants). qfd_tt_ctlm_dv is not in critical_tiles.txt, but per LEAD-QW the
packet (PNGs + these facts) goes to review before any submit.
