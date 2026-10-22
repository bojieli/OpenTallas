# qfd_n59_qbank13a / 13b (QR-QBANK 10-21) -- structural successors of qbank12a (clock_rule FAIL) and qbank11a (TT -483.8)

Source = qbank12a RTL (claude/qko-n59-1021 @47c14228d, QB_WLOCAL=1 macro-local kept write-port copies, benches PASS / mutants
REJECTED in results/arch/qw_n59_qbank10_1020/receipts_wl12) and its 950.4 x 475.2 geometry (trial GRT overflow 0 on 12a).
qbank12a gate: the ONE TritonCTS tree over 950 um / 13,775 sinks: TT insertion 802 ps, pin-flop spread TT 166.9 / FF 145.6 ps.
13a MAIN: regional clock = pre-placed balanced clock spine (clock_spine.tcl; <=16-sink leaves per 60-um bin, repeated
bisection trunks around the macros, leaves padded to equal measured arrival, macro clock pins as leaves).
13b FALLBACK: TritonCTS with per-region clustering 16 sinks / 25 um, 3 levels, buffer every 40 um.

## SAFE 8-point review
1 pins: flop-first RTL unchanged, pin bands as 12a (<= ~4 pins/um), reset landing 2x32. PASS
2 reach: S face -> w1 -> w2 (macro-local) -> pins, two registered hops <= ~405 um each. PASS
3 fanout: kept copies <= 32 loads (data <= 6, one-hot 32); census binds in flow. PASS
4 depth: w2 -> macro pin wire only (fixes the 11a -483.8 reg->macro class). PASS (gate --cts measures)
5 storage: 8 x 32x546 SRAM on the 43.2 lattice, 81.4-um central channel. PASS
6 floorplan: macro fill ~52 %, channels >= 38.2 um, = 12a (GRT ovf 0). PASS
7 clock: regional leaves (13a spine / 13b clustered tree) replacing the single 802-ps tree; target spread <= 80 TT+FF. CHECK at gate
8 reset: only ce/valid reset, landed. PASS
