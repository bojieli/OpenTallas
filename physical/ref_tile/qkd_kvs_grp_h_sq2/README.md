# qkd_kvs_grp_h_sq2: square DOMSPLIT group, structural clock redesign (KV-GRP-CTL 10-19)

Same RTL, ports, pins, outline (388.8 sq) and SRAM bank as qkd_kvs_grp_h_sq1 (codex/kv-grp-safe-1019 cf5150d12). Changed: clock topology only.

Why: sq1 --cts gate (ot-epyc8 /srv/opentallas-scratch/claude/ref_gate/qkd_kvs_grp_h_sq1-20261019-080306) measured core_clk
pin-flop spread TT 94.3 / FF 96.4 ps, hck 32/28 ps > 80 (clock rule FAIL). The count-bisection spine started at 205 ps leaf spread, then padded 1,858
leaves with ~12k delay cells to 28.6 ps at placement RC; pad-cell delay does not track the wire-dominated trunk across
corners (same class as el1013-smh-r11: 28.8 ps TT -> 102 ps FF). Fix: OT_SPINE_SYM=1 symmetric centre-of-bbox tree, centre-fed trunk, no tree pad, SAFE_BALANCE, 16-sink leaves.

SAFE checklist (KV-GRP-CTL review before gate):
1 Pins: pin_regs OFF waived: wires-only composition of the static join (every edge age priced in die_ages.json); 35 comb
  in->out bits are the pure y__tok/y__tep/y__est = x__* pass words (0 levels, pins adjacent on W 193-204 um, <12 um wire);
  reset lands 2 stages in RTL per domain (qkd_kv_rst_land u_rrc/u_rrh). WAIVED-with-reason (die schedule owns those ages).
2 Reach: 388.8 square, textbook reach 146.8 um. PASS.
3 Fanout: textbook high_fanout clean in sq1 synthesis (reset kept copies per child). PASS.
4 Depth: sq1 textbook depth 565 ps (< 600); placement reg2reg slack >= +104 ps TT. PASS (in->out pass words waived in 1).
5 Storage: four ot_sram_1r1w_128x256 macros; no runtime-indexed flop arrays added. PASS.
6 Floorplan: SRAMs on 43.2 lattice (43.2/172.8 x 43.2/129.6), 1:1, full-width upper std-cell band; E face 5.58 pins/um;
  util ~15% WAIVED (pin-bound, coordinator-approved in sq1). Die must re-slot grp to 388.8 sq (MU-DIE-KV).
7 Clock: FIXED by this kit (see Why); io_hold_margin 0.03; gate must show TT/FF pin-flop spread <= 80.
8 Schedule: static; no added cycles (clock-only change).
