# COLL native32 v8: sender offset as state (S81-COLL4, 10-20) -- source QUALIFIED, layout NOT RUN

Define `OT_COLL_NATIVE32_OFF` (on top of `OT_COLL_NATIVE32` v3; default off, v3 netlist unchanged without it).

## Change (0 added cycles, same transfer function)
- `off = snd - una` is kept as two same-edge state registers (`off_s` sender/replay-index cone, `off_r` ready cone).
  Skip compare `d_ack > (snd + launch - una)` becomes `d_ack > off` / `(d_ack!=0) && (&off || d_ack-1 > off)`
  (Codex v6 identity) on registered `s2dackm1 = d_ack-1`, `s2dnz = d_ack!=0` computed in S2 beside `s2dack`.
  The v3 critical chain snd -> +1 -> launch mux -> subtract -> compare -> rp_r (621.8 ps / 16 lv) is gone.
- `off' = 0` on rewind or skip, else `off + launch - (ok ? d_ack : 0)` (d_ack = rr_ack - una exactly in an apply cycle).
- Fanout guards found by iterating the mapped census (each rejected step preserved in native_v8a..d):
  v8a in_valid 112 (ABC folded wr into every rp_r mux bit) -> replay write-group term through kept `ot_s81ph_kp4_20`;
  v8b c_inord-side OR2 33 -> receive write-group term through kept `kp4_20`;
  v8c ok_f 37 / nxt_rw[6] 36 / ok_ready 35 -> own copies ok_o, ok_f2, nxt_rw2, una_rw2; v8d ok_o 33 -> ok_o2.
- Removed: una_skip, una_so copies. Added FF vs v3: +36 (16,342 mapped; 55 SRAMs unchanged).

## Evidence (source = branch claude/s81-coll4-1020, ep file sha in coll_census netlist sha below)
- Induction step miter `off_step_equiv.sv` (33 inputs, no range premise): Yosys SAT PASS (`off_step_equiv.log`).
- Sim asserts in RTL every cycle: off_s/off_r == snd-una, copies equal, skip == v3 formula, d_ack == rr_ack-una.
- Production boundary miter, Verilator 5.050 (`bench/`): m0 PASS 79,994 checks (no assert fired);
  m1 FAIL 20009, m2 COLL_COLLISION_UNSAFE fatal, m3 FAIL 79775, m4 FAIL 79760 (identical to v3 witnesses).
- Mapped synthesis (ORFS, CH_BOARD 700, TT): BUF/INV-collapsed census 0 roots > 32, max 32 (`coll_census.json`);
  actual-Liberty native census PASS, 48,713 roots, max 32 (`actual_roles_summary.json`, netlist sha 862d3029...).
- Depth: 540.1 ps / 14 levels (d_fr -> replay ready_r) <= 600 (`textbook_native.json`; verdict WARN only clock guidance
  16,342 sinks > 15k, which is guidance per owner 10-17 clock rule: judged on measured spread).
- Synth area 71,491 um2 total (std ~9.5k + macros 62,002).

## SAFE checklist (source items)
1 pins registered (unchanged v3) PASS · 2 reach: layout NOT RUN · 3 fanout max32 PASS · 4 depth 540.1 PASS ·
5 storage 55 SRAM PASS · 6 floorplan: OPEN (s4/s4b geometries failed placement, see ../s4_terminal) ·
7 clock: layout NOT RUN · 8 schedule: 0 added cycles, nothing to price PASS.

## Geometry blocker (next)
All four s4/s4b gates are terminal FAIL in placement: W_s4 / E_s4b GPL-0305 (archived by Codex), E_s4 DPL-0033,
W_s4b DPL negotiation stuck (21,901 illegal of 81,614 one-row cells) then OT_SPINE spread diverging 224->464 ps,
log idle 1.5 h -> cancelled 02:53 (`s4_terminal/`). OT_SPINE inserts 16-34k clock cells for 16k sinks; a single
28.8-39.6 um band sized only for the 9.4k um2 synthesis std area cannot hold them. Next geometry must budget band area
for the spine/repair cells (or regional roots) before any gate.
