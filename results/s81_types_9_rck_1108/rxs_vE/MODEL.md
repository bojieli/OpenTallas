# RXS vE model before PLACE

Measured routed vD: TT -94.15ps/131 endpoints, FF -8.85ps/13. Worst class is syndrome-window sc_q to sp XNOR depth; actual route congestion image has a dense west half. Arithmetic BM recurrence previously meets placed TT with109.55ps, so preserve30 single-cycle iterations and NBM3.

SPCYC1 uses4 registered partial matrices (each sc_q138-bit source group) then pairs their XORs in sp0/sp1. It adds1200 partial-state bits, about360um2 before mapping, and one recovered cycle on k_*; x_q/lock/relock unchanged. Paired DD57→58 waits one more received word in the existing64-deep memory. Whole decoder q_* shifts+1rck; frame throughput remains one544-bit beat percycle, one codeword per10cycles. No width, traffic or lane replication change. BMTHC1 now declares only45 normal10-bit theta words and one tail bit; removes9 unused tail state bits perunit, without changing reachable results or adding cycles.

Outline259.2x216um (55987um2) retains the vD area with shorter north clock reach; max dimension259.2um, below405um hop budget. Core area(250.56x207.36)=51956um2, predicted mapped area~18kum2 (<40%fill); old125kcell estimate plus~1200 FF stays below150k, actual synth gate required. Existing south output coordinates retained so x_q and k_* align with RXB; north signal gap moves to the midpoint clock129.612um. M5 signal cap, no macros. Draft origin1296,457.92 keeps top673.92 below shore681.372. Parent old taps and exact cycle table must be rebound before plan event; no POR edit.

Need exact narrowed-tail proof and combined data/reset pipeline proof+mutants, then RAW guard/synth count and one actual PLACE; view density/clock/fanout and TT budget before CTS. No independent clock/phase claim or signoff implied.
