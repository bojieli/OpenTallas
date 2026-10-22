# s81sl_vs_w2 -- ot_s81sl_vs re-close on current RTL (MAIN)  [S81-SLICE/CHILD 10-21]

Why: the bound view physical/ref_tile/s81sl_vs/views/ot_s81sl_vs closed at b571a8c2c (TT +21.29 / FF +17.17); 8158a1e89 (10-18 23:41)
then added the SW wr/wsel weight-row path (MUT 9) to rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vs.sv. Ports unchanged, logic changed ->
the view is stale (the prs1-e7a55f1e1 record also predates it: archive-only). No RTL change here.
Outline: 172.8 x 172.8 exact (drop-in for the closed view; parent geometry unchanged). Pins/pin_ranges = the closed kit's. Benches = closed kit set + slvs_mut9 (vs_bench.sh MUT 9, Verilator 5.050).

## SAFE review (8 points)
1 Pins: PASS -- source-registered (capture flops at every input, every output a flop); kit reset_landing 2 stages.
2 Reach: PASS -- tile <= 205.2 um.
3 Fanout: PASS (as closed) -- ENG stash index already replicated (4 kept copies, gate high_fanout fix); the wr change adds a 32-b 8:1 word select.
4 Depth: PASS -- wr adds one 8:1 x 32 b mux into the w0/w1 enable path (registered); closed at TT +21 ps on the same outline (MAIN).
5 Storage: WAIVED (unchanged closed design) -- 4 kb ENG h stash in flops, closed in b571; rule freeze 10-20: tile rules guidance.
6 Floorplan: PASS -- no macros; util ~0.52 MAIN as closed, lower in FALLBACK.
7 Clock: PASS -- one clock, centre-fed CTS; spread <= 80 TT+FF judged by gate; io_hold_margin 0.03 (was 0.0).
8 Schedule: PASS -- static; SW wr is on the fixed timeline (+4 edges for wr ops only, priced in lower_vs by 8158a1e89).
