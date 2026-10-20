Gate 2 (TW2-S81C199, 10-19): compact199 pinreg --pnr-stop-after cts with route IO reference CK_SS_MEAN=594 (measured; gate1 used stale 841).
Run: ot-epyc4:/srv/opentallas-scratch/claude/s81-c199-pinreg-ss594 (gate.sh = ../gate.sh with CK_SS_MEAN=594), finished 01:27.
Band: 839/840 ports register-at-pin (skip a_ctr[13]), as gate1.
Clock (ck.json, CTS placement RC, raw source): boundary TT 556.8-605.3 (spread 48.5, mean 595.0) FF 444.6-493.2 (spread 48.6) -> <=80 PASS (gate1 68.2/48.9). All flops TT 539.9-694.1.
Hold repair at CTS (margin 30, hold corner mm): start WS -82.5 (gate1 -306); 25401+2532+13 = 27,946 hold buffers, end WS +30.0; util 58.8 -> 61.2%. The count is internal reg->reg margin-30 repair (21,479 endpoints), not IO padding.
Setup (CTS placement RC, TT, 730 ps): WNS -5.44 ps / TNS -5.91 ps (route repairs). GRT not run (gate stops after CTS).
Native TT probe (same tcl as gate1, signoff_col.sdc, placement RC; native_audit.json): launch max 173.3 ps (ppos[0]), 0/64 >220 PASS (gate1 517.6; closed view 243);
  capture max 119.1 ps (a_ctr[3]), 0/775 >190 PASS (gate1 44.6; closed 206.7); 0 combinational pins. Reference = boundary mean 595.0.
pseg[2] under signoff SDC: setup slack +370.4, hold slack +61.1 (gate1 had ~23 BUFx2 hold pad on this output; now gone).
Layout: 450.144x198.72 (aspect 2.27, unchanged slot), fill 0.59, 2 ROMs stacked at x 42.3 (closed-view placement), clock pin N face x 227.
  Pins: E 777 over y 62.0-136.5 (74.5 um, 10.4/um on the span, 3.9/um face), S 148 over full face (0.33/um), N 1 (clk). Pin set/positions inherited from the closed view.
Verdict: PASS (diagnostic, CTS placement RC; routed native qualification follows the route). Critical prefix ot_v41_bf_ -> coordinator review, no submit by the lane.
