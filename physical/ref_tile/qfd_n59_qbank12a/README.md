# qfd_n59_qbank12a (QKO-N59 10-21) -- structural successor of qbank11a

qbank11a route.a2 (ot-pve1, 2c0e988c5): GRT overflow 0 (the 11a channel fix worked), but CTS TT setup WNS -400 ps after
repair, 2,098 endpoints, all reg->macro write pins: p_dd[244] -> u_qseat.g_writer[4].u_mem/wd_in[283], launch clock 631 ps,
~920 ps of buffer daisy chain.  Cause: ONE p_dd bit drives the 17 replicated wd_in pins of its writer (16 replicas + spare
column) spread along the 160-um macro E face, and p_dd is placed where its other loads (bypass, S-face f_dd) pull it.
Fix QB_WLOCAL=1 (RTL rtl/qwen_split/qfd_native59_qbank.sv, 0 edges, bit-exact at every port): per writer a kept relay stage
w1 (d1/e1/v1/s1 == f_*, loaded from the input capture dd_x) and a kept macro-local stage w2 (== the p_*-derived write port)
that drives every write pin: 4 data copies (copy k -> replicas 4k..4k+3, copy 3 also the spare columns; <= 6 pins per flop),
16 one-hot mask flops (32 pins each), 5 address flops, 1 enable flop (reset by rst_pin exactly as p_*).  +1,664 flops.
Outline 950.4 x 475.2 = qbank11a geometry (81.4-um central channel; 11a route GRT overflow 0).

## Safe-design checklist
1 Pins: flop-first RTL unchanged (i_* S face, o_* N face); reset landing 2 stages x32. PASS
2 Reach: S face -> w1 -> w2 (beside the macro) -> pins: two registered hops for <= ~720 um Manhattan to the far macro. PASS (gate measures)
3 Fanout: new flops <= 32 loads (data copies <= 6, one-hot 32); i_dd gains 1 load per bit. PASS (in-flow census binds)
4 Depth: w2 -> macro pin is wire only; w1 -> ce is a 4-term AND + 6-bit range compare. PASS
5 Storage: 8 x 32x546 SRAM macros on the 43.2 lattice, unchanged. PASS
6 Floorplan: = qbank11a (macro fill ~52 %, channels >= 38.2 um). PASS
7 Clock: single centre-fed root as 11a (TT/FF pin spread 47.6/42.7 measured on 11a); gate re-measures. CHECK
8 Reset: only ce (valid) is reset; data/mask/addr copies unreset (writes disabled in reset). PASS
Benches: bench.sh with N59_QB_WLOCAL=1 (rnd rnd_s2 reset8 dv mu + old mutants) and mut_wl (N59_QB_WLOCAL=2, mask one lane off) must be REJECTED.
