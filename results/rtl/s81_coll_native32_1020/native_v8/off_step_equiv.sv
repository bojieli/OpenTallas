// v8 induction step (S81-COLL4 10-20): with off == snd - una (inductive hypothesis) and the registered
// S2 facts dm1 == d_ack - 1, dnz == (d_ack != 0), and in an apply cycle rr_ack == una + d_ack, the v8
// skip predicates equal the v3 ones and the v8 offset next state equals snd' - una' for both accept arms.
// Expressions copied from ot_s81ph_link_ep_safe4.sv (v3 legacy formula vs OT_COLL_NATIVE32_OFF); no range premise.
module off_step_equiv(input wire [9:0] snd, una, d_ack, input wire ok, lnch_0, rw, output wire bad);
 wire [9:0] off = snd - una, dm1 = d_ack - 1'b1, rr_ack = una + d_ack; wire dnz = d_ack != 0;
 // v3
 wire [9:0] sndl_0 = lnch_0 ? snd + 1'b1 : snd, sndl_1 = snd + 1'b1;
 wire skip_0 = ok && (d_ack > (sndl_0 - una)), skip_1 = ok && (d_ack > (sndl_1 - una));
 wire [9:0] una_n = ok ? rr_ack : una;
 wire [9:0] sndnx_0 = rw ? una_n : (skip_0 ? rr_ack : sndl_0), sndnx_1 = rw ? una_n : (skip_1 ? rr_ack : sndl_1);
 // v8
 wire g0 = d_ack > off, g1 = dnz && ((&off) || (dm1 > off));
 wire k0 = ok && (lnch_0 ? g1 : g0), k1 = ok && g1;
 wire [9:0] p1 = off + 1'b1, md = off - d_ack, md1 = off - dm1;
 wire [9:0] t1 = ok ? md1 : p1, t0 = ok ? md : off;
 wire [9:0] o0 = (rw || k0) ? 10'd0 : (lnch_0 ? t1 : t0), o1 = (rw || k1) ? 10'd0 : t1;
 assign bad = (k0 != skip_0) || (k1 != skip_1) || (o0 != sndnx_0 - una_n) || (o1 != sndnx_1 - una_n);
endmodule
