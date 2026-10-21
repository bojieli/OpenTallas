# s81sl_capc5i (DRIVE-S81-CAP 10-20) -- landed capc parent ot_s81sl_capc5c, see spec.json structural_change
Safe-design checklist (owner 10-19), unchanged RTL vs capc5e/g (gate census: mapped dynamic load limit 32 PASS, max 32):
1 Pins: every port lands in its face region (u_fw/u_fe/u_fcv/u_fcd in, u_on*/u_os* out); reset 2-stage regional runs. PASS
2 Reach: max wire 80 um repeated (max_wire_repeat); child crossings strong drivers. PASS
3 Fanout: census max 32 (kept copies, regional reset copies). PASS
4 Depth: setup WNS > 0 at gate (capc5g TT placement: reg->reg +97 ps). PASS
5 Storage: landing rings D=4 n32 chunks (lp generator), no runtime-indexed flop arrays > 2 kb. PASS
6 Floorplan: children on the 43.2 lattice, >= 20 um channels, aspect 1.23, fill 38% (macro/pin-bound outline, WARN). WAIVED (pin-bound)
7 Clock: 5 regions with landed crossings (19 landings); region rt = u_rt + its ring halves; post-CTS region latency balance
  (rt only) so the TT/FF pin-flop pair spread is <= 80 within each region; io_hold_margin 0.03. fixed
8 Schedule: static landings (E=K=2, D=4), no flow control; cycles unchanged vs capc5c. PASS
