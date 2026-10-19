# s81sl_xgr2 -- S81 slice gather sub-leaf, structural successor of s81sl_xg (LEAD2-S81/SLICE 10-19)

Why: s81sl_xg gate2 (f3c425683) did NOT run out of memory: its trial GRT stalled 4 h in congestion extra iterations
(GATE_STALL 14400 s, peak ~5 GB) at 12 % std-cell util -- a wire-bound tile. Causes: ring line pass-through W pin -> E pin
in one cycle across 648 um (-810 ps placed on ro_e), the 24-macro x-buffer read crossbar (24 x 1,536 b converging), and a
2,517-load landing reset net on line payload registers. RTL @710b93b84 (claude/s81-xgr-1019): ot_s81sl_xg instantiates
ot_s81sl_rstop #(.RELAY(1)) and ot_s81sl_xs #(.RD2(1)); RELAY=0 / RD2=0 stay bit-identical for other users.
Variant: outline 734.4 x 604.8 (+22 % routing area), macros +43.2 in x (parallel to s81sl_xgr 648 x 561.6).

## SAFE checklist (owner 10-19)
1 Pins: waived-with-reason -- source-registered (every input lands in a flop, every output leaves a flop; RELAY outputs are
  flops); reset_landing 2 stages ON.
2 Reach: fixed -- every rstop output leaves through a relay register (line E/W, V, dl_*, nx_*): W->E / N->S crossings are
  two registered hops (~324 / ~280 um each) instead of one 648-um cycle.
3 Fanout: fixed (reset) -- line / V payload reset-free, valid bits only; per-bank kept (ot_v41_kreg) macro-select copies and
  {gate, bank} copies for the read stage. Kept-copy survival after Yosys to be confirmed at the gate (s81sl_xg showed a
  merged 4,050-load select net).
4 Depth: PASS -- read mux split 8:1 + 3:1 across two registered stages; s81sl_xg textbook depth 503 ps.
5 Storage: PASS -- x buffer 24 SRAM macros, 7 ROMs; small tables in flops (arrival tables 2 x 176 b, exponents 384 x 10 b
  flop array: existing, flagged for SRAM move if it shows in GRT).
6 Floorplan: PASS with waiver -- macros on the 43.2 lattice in x (bank columns facing their ring source), abutted 41.088
  vertical pitch inside a bank (existing); outline is pin-bound (11.9k pins), not synthesis-area bound (util < 40 %).
7 Clock: PASS -- km clock split K=16, s81sl_xg CTS measured TT 62.6 / FF 72.4 ps pin-flop spread; io_hold_margin 0.03.
8 Schedule: +1 edge on rstop line/V/dl/nx outputs and +1 on xw_d (bench --xs-out 2); INBOX line in lanes/LEAD2-S81.md;
  die schedule / token pricer owed.
