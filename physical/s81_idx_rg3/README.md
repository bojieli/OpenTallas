# s81dv_idxrg3 / s81dv_idxrg3b: dsdv_idx_rg3 hard cluster kits (DRIVE-S81-IDX4-KITS, 10-20; MU.BAL.SX.3, mu7i4 die)

dsdv_idx_rg3 = the non-inline paired index reader (S81-IDX3R; one per controller pair, 8 a die in the PHY corner strips).
Hard content: 32 x ot_hdc_v41x_idx_hslice (closed view physical/ref_tile/ot_hdc_v41x_idx_hslice_m5, 172.8 x 103.68,
pins N in / S out only) as 4 chunk columns g_ch[c].u_c.g_s[0..7].u_s, + 13 x ot_sram_1r1w_1024x256_m2_r2c2 (174.744 x
70.47, M4 pins on W / E faces only). Hard area 733k um2.

SLOT FINDING (die plan owner must act): the --idxrd 4 slot is 1036.8 x 1036.8 (dv_plan IDX3_W/IDX3_H). An 8-high chunk
column on the 43.2-um child lattice spans 7 x 129.6 + 103.68 = 1010.9 um; the key / query broadcast into the 4 column
heads is 1,150 nets (k_key 544 + ql 569) that need a ~70+ um horizontal channel above the columns; 13 SRAMs in one
column with 20-um channels need >= 1,159 um. Width is fixed by the 1062.5-um strip pitch. Hence the outline grows in
HEIGHT only: main 1036.8 x 1209.6 (reader top y 1409.6 at y0 200, under-frame strip 1409.6-1786 = 376 um left for the
hrrq/hrrd risers), fallback 1036.8 x 1252.8 (top 1452.8, 333 um left). dv_plan --idxrd 4 must take the reader height
from the closed kit (IDX4 reader h 1209.6 or 1252.8, not IDX3_H).

Floorplan (both): W band 86.4 (W pins qi/si/sid/rst/ck, walker / landing-write logic); SRAM column at x 86.4 (score /
metadata queues at the bottom beside the chunk tails, 8 landing macros in the middle, item queue + 2 list macros on top);
mid band 41 um; 4 abutted chunk columns x 302.4-993.6, y 43.2-1054.1 (slice 0 on top, systolic chain N -> S through
25.9-um seams = straight M5 drops); top channel above the columns (155 / 199 um) = the broadcast + chunk input
registers; bottom 43.2 band = chunk sums -> tail adder; E band 43.2 (qo/so/st). N face rqo 184 + rri 1,088 (1.2 pins/um).
Main SRAM pitch 90.72 (20.25-um channels); fallback pitch 92.88 (22.4-um channels) + taller top channel.

SAFE checklist (pre-gate):
1 Pins PASS: source-registered (every input lands in a flop at the pin, every output leaves one; pin_regs opt-out reason
  in the spec); reset 2-flop landing + ot_rst_relay forest (40 leaves); reset_landing 2 stages in the flow.
2 Reach PASS/verify: chunk heads <= ~700 um from the broadcast source: the chunk input registers (rkey / rql, one set a
  column) sit at each column head; post-GRT native reach audit owed at the gate.
3 Fanout PASS: native census results/rtl/s81_idx3r_1020/receipts/native_rg3 (hslice TT view, keep hook, textbook 32/405):
  0 refusals, hf max <= 32, 11,598 FF.
4 Depth PASS: rg2 engine/walker unchanged (rg2 census/gate classes); textbook depth in the remote gate.
5 Storage PASS: all > 2 kb storage in the 13 SRAMs; landing FIFO lives in the controller.
6 Floorplan: children on the 43.2 lattice (abutted E-W: hslice W/E faces carry no pins), SRAMs on the macro lattice with
  >= 20-um channels; fill ~59% / 57% (hard 733k + std ~12k estimate); aspect 1.17 / 1.21; one full-width std band is
  NOT possible with a 4-column child block (bands: W / mid / E vertical + top / bottom horizontal) -- reviewer item.
7 Clock: cluster default (pre-placed balanced spine with the hslice TT clock insertion as the leaf target); --cts gate
  reports the final leaf spread (<= 80 ps TT / FF within the region); io_hold_margin 0.03.
8 Schedule PASS: no RTL change (rg3 = S81-IDX3R 8ccaf446f).
Benches: idxrd3 b3 campaign PASS (witness results/rtl/s81_idx3r_1020/receipts/bench_b3.log) + m1-m6 FAIL witnesses
(receipts/bench_m*.log), Verilator 5.050.

## S81-IDXRD-1021 (10-21): native19 structural fix (lanes/CODEX-IDX4-NATIVE19-NEXT.md)
RTL rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3.sv. Every change is a kept same-edge register copy / registered one-hot /
appended same-depth reset leaf: 0 schedule edges, 0 added cycles, no compiler/timing-contract change (EL, T0, P, DQR and
the reader window are unchanged; nothing to re-price). Mapped +368 FF (12,670 -> 13,038), synth area +156 um2 (+0.03%).
- egress take: tk0/tk1 2 x 8 lanes -> 16 + 16 kept per-lane copies (were 98..128 loads).
- landing tokens: irw/srw 12 + 12 kept copies of ir_f / sr_f (from ir_e / s_re, same edge), one per head entry x field.
- slot table: per-slot enables = own decision copy (xal/xgt/xq/xnd [6:0], same decision edge as u_al/u_gt) AND registered
  one-hot sa / sop (saoh / sopoh; sa / sop change only at update edges >= 2 apart, so the decode is exact); scl per region,
  sni/sne halves, snc quarters; sni/sne alloc values registered (uvn/uve).
- gm: kept replicas gmp / gmr (g_b data select low / high), gmq (high-half "no lower entry"), gmz (zero tests); gm keeps g_e / g_m1.
- hj3[8] (nw high byte); tch replica of the window clock for the header-beat path, with its own job-end cone (leftk,
  qvk[2], infk[3]); infk[2:0] replicas of infr for left / pw / leftk; she[4] / afr[4] for gfr.
- reset forest: u_r1 24 / u_r2 22 leaves (rl[39:0] indices preserved): rlx[3:0] jra/jrb of PC 0..3, rlx[5:4] scl of
  region 0 / 1 (u_r0 outputs see 26 / 24 async loads).
Local mapped native census (gate config, ORFS asap7lock synth): PASS, max 32, 0 role errors
(results/rtl/s81_idxrd_1021/native_probe6_summary.json). Outline unchanged: main 1036.8 x 1209.6, fallback 1036.8 x 1252.8
-- the die plan reader slot (--idxrd 4) must be 1036.8 x 1209.6 (1036.8 square cannot hold it).
