# PV v8 G2 join low bank pin geometry (11-24)

Exact E11 PV v8 kit `kv3_pv_v8_1124043905`. The placed-scan 415 µm measurement uses a macro bounding-box proxy. In issued RTL the 512 direct low-bank bits map `u_pvg2_p1.s0__ts[i]` to `u_pv_u_g2_j.ts1[i]`. The same kit LEFs and exact placed R0/MX orientations give pin-center Manhattan 336.528–532.944 µm, with 333 of 512 beyond 405 µm. The adjacent P0 macro occupies the direct channel. A perimeter path around its body has lower-bound length 461.040–657.456 µm before halo or routing-layer constraints. The west-perimeter sketch shows five representative bits.

The separate high 512 `s1__ts` bits already pass through an explicit one-cycle bank. A small move of P1 alone cannot recover the direct low 512. A candidate with unchanged join-edge age could move the existing join input capture for bank 2 (`t_r[1024+:512]`) out of the hard join into a west-side parent bank. The revised join would take those registered inputs at the existing `tb[2]` boundary. This requires a new typed hard abstract with its corresponding internal combinational input contract, exact clock/boundary timing, mapped equivalence and actual placed capacity. No proposed capture has been launched. The whole PV v8 hold remains.

- [Pin pairs and macro perimeter](pv_v8_g2_pins_1124.png)
- [All 512 pin pairs](pv_v8_g2_exact_lef_witness_1124.json)
- [Whole exact placed review](kv_a5t3_pv_v8_1124.md)

The draft west bank fits eight columns spaced 1.35 µm from x631.80 and 64 rows spaced 0.27 µm from y914.76. The existing FIRM and macro footprints clear the examined x626.00–643.296, y893.00–940.00 window. Projected maximum P1→bank and bank→join legs are 369.990 and 316.602 µm, including source pin escape. The fresh clock, PG and row measurements are still required.
