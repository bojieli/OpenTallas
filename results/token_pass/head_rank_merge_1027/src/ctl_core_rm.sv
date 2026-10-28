`timescale 1ns/1ps
`default_nettype none
// TOK-ALL-16 bench driver in place of the ctl LEAF ot_s81hd_ctl_core (same ports as main).  = TOK-ALL-15 driver
// (x_o in the hsf0 sno_q format, b_i spine result monitor) PLUS the rank merge on the generated die:
//   * at the b_i result edge R the driver registers the own BEST record {pos21, user10, bits32, row17, v1} (edge R+1:
//     ov_p into the REAL ot_s81hd_rank_merge_hsf0 and v into three REAL ot_s81hd_best64_tx on a_tx_o / b7_tx_o / n_tx_o);
//   * the three lanes leave through the generated stations to mesh0S / mesh7S / mesh7N (REAL ot_s81hd_mesh_ep_core:
//     best64 decode, 2 x dsfd_coll_lane_w_safe8_ntf link_ep+gearbox, copy FIFOs, beat_tx), the generated coll stations,
//     the REAL ot_s81hd_serdes_link (ot_pdie_serdes: KP4 enc/dec, rate matcher; PMA analog behavioural) and, in tb, the
//     pads looped back with a channel delay K so that serdes-leaf to serdes-leaf = D (see tb), back into the far mesh
//     and the generated rx stations to a_rx_i / b7_rx_i / n_rx_i -> REAL ot_s81hd_mesh64_rx x3 -> rank merge.
//   * Peer substitution (one die simulated): the loop ES->WS models the WEST peer's east transmission, WS->ES the EAST
//     peer's, EN->EN the diagonal peer's.  So each tx lane carries THAT peer's record (golden per-rank argmax):
//     b7_tx (mesh7S->ES) = west peer, a_tx (mesh0S->WS) = east peer, n_tx (mesh7N->EN) = diagonal peer.  All peers
//     transmit at the same static edge as the own rank (identical dies, same compiled date).
// Measured: b_i result edge R -> rank-merge valid edge (final 4-rank argmax), per-lane copy arrival edges.
// Plusargs: as TOK-15 + +PW_ROW/+PW_BITS (west peer) +PE_ROW/+PE_BITS (east) +PD_ROW/+PD_BITS (diag), +FIN_ROW/+FIN_BITS
//   (expected final), +DROP_N (control: diagonal peer never transmits), +CORR_E (control: east peer record bit flip
//   after the canonical check is NOT possible -> we flip the transmitted bits field, expectation stays golden).
module ot_s81hd_ctl_core #(parameter integer SK=11,parameter integer MUT_DRAFT_EARLY=0)(
 input wire ck,rst_n,start_i,lep_fault_i, input wire[10:0]lw_i,
 input wire[1103:0]lepk_i0, output wire[1103:0]lepk_o0,
 output wire lepf_o0, output wire[44:0]unit_o0,input wire[31:0]ctrl_i0,
 output wire[564:0]x_o,input wire[564:0]b_i,
 output wire[276:0]h_tx_o,input wire[275:0]h_rx_i,
 output wire[63:0]a_tx_o,b7_tx_o,n_tx_o,input wire[63:0]a_rx_i,b7_rx_i,n_rx_i
);
 assign lepk_o0='0; assign lepf_o0=1'b0; assign unit_o0='0; assign h_tx_o='0;
 localparam integer NX = 8192 + 7*SK + 8;
 reg [255:0] xa [0:255]; reg [255:0] xb [0:63];
 reg [564:0] xq; assign x_o = xq;
 string dir; integer go_at, npos, gap, exp_row, xshift; reg [31:0] exp_bits;
 integer pw_row, pe_row, pd_row, fin_row, drop_n, corr_e; reg [31:0] pw_bits, pe_bits, pd_bits, fin_bits;
 integer cyc = 0, t = -1, pos = 0, nres = 0, bad = 0, go_cyc [0:15], res_cyc [0:15], nfin = 0, fbad = 0;
 initial begin
  if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
  if (!$value$plusargs("GO_AT=%d", go_at)) go_at = 400;
  if (!$value$plusargs("NPOS=%d", npos)) npos = 1;
  if (!$value$plusargs("GAP=%d", gap)) gap = 10357;
  if (!$value$plusargs("EXP_ROW=%d", exp_row)) exp_row = 21946;
  if (!$value$plusargs("EXP_BITS=%h", exp_bits)) exp_bits = 32'h4173a558;
  if (!$value$plusargs("XSHIFT=%d", xshift)) xshift = 0;
  if (!$value$plusargs("PW_ROW=%d", pw_row)) pw_row = 103774;  if (!$value$plusargs("PW_BITS=%h", pw_bits)) pw_bits = 32'h414142e8;
  if (!$value$plusargs("PE_ROW=%d", pe_row)) pe_row = 33100;   if (!$value$plusargs("PE_BITS=%h", pe_bits)) pe_bits = 32'h41345fd2;
  if (!$value$plusargs("PD_ROW=%d", pd_row)) pd_row = 93642;   if (!$value$plusargs("PD_BITS=%h", pd_bits)) pd_bits = 32'h41363460;
  if (!$value$plusargs("FIN_ROW=%d", fin_row)) fin_row = 21946; if (!$value$plusargs("FIN_BITS=%h", fin_bits)) fin_bits = 32'h4173a558;
  if (!$value$plusargs("DROP_N=%d", drop_n)) drop_n = 0;
  if (!$value$plusargs("CORR_E=%d", corr_e)) corr_e = 0;
  $readmemh({dir, "/xa.hex"}, xa); $readmemh({dir, "/xb.hex"}, xb);
 end
 reg run = 1'b0;
 always @(posedge ck or negedge rst_n)
  if (!rst_n) begin run <= 1'b0; cyc <= 0; t <= -1; pos <= 0; xq <= '0; end
  else begin
   if (start_i) run <= 1'b1;
   if (run) cyc <= cyc + 1;
   xq <= '0;
   if (run && pos < npos && cyc == go_at + pos * gap) begin
    t <= 1; go_cyc[pos] = cyc + 1;
    xq[512] <= 1'b1; xq[513] <= 1'b1; xq[514] <= 1'b1; xq[531:515] <= 17'h1FFFF; xq[563:532] <= 32'hFF800000; xq[564] <= 1'b0;
   end else if (t >= 1) begin
    t <= (t - 5 + 1 >= NX) ? -1 : t + 1;
    xq[513] <= 1'b1;
    if (t >= 5) begin xq[255:0] <= xa[(t - 5 + xshift) % 256]; xq[511:256] <= xb[(t - 5) % 64]; end
    if (t - 5 + 1 >= NX) pos <= pos + 1;
   end
  end
 // ---------------- spine result monitor (TOK-15) + own/peer BEST issue
 function automatic [552:0] bestf(input [20:0] p, input [31:0] bits, input [16:0] row, input [3:0] rank);
  bestf = {1'b1, 455'd0, p, 10'd0, bits, row, 1'b1, 8'd0, rank, 4'd1};
 endfunction
 reg ov; reg [80:0] orec; reg tv_a, tv_b7, tv_n; reg [552:0] tf_a, tf_b7, tf_n;
 always @(posedge ck or negedge rst_n)
  if (!rst_n) begin ov <= 1'b0; tv_a <= 1'b0; tv_b7 <= 1'b0; tv_n <= 1'b0; end
  else begin
   ov <= 1'b0; tv_a <= 1'b0; tv_b7 <= 1'b0; tv_n <= 1'b0;
   if (run && b_i[514]) begin
    $display("DIE_SPINE_RESULT pos%0d row%0d bits%08h flt%0d go_to_result%0d", nres, b_i[531:515], b_i[563:532], b_i[564], cyc - go_cyc[nres]);
    if (b_i[531:515] !== exp_row[16:0] || b_i[563:532] !== exp_bits || b_i[564]) begin bad++; $display("DIE_SPINE_MISMATCH pos%0d", nres); end
    res_cyc[nres] = cyc;
    ov <= 1'b1; orec <= {21'(nres), 10'd0, b_i[563:532], b_i[531:515], 1'b1};
    tv_a <= 1'b1;  tf_a  <= bestf(21'(nres), pe_bits ^ (corr_e ? 32'h0000_0100 : 32'h0), 17'(pe_row), 4'd1);
    tv_b7 <= 1'b1; tf_b7 <= bestf(21'(nres), pw_bits, 17'(pw_row), 4'd3);
    tv_n <= (drop_n == 0); tf_n <= bestf(21'(nres), pd_bits, 17'(pd_row), 4'd2);
    nres++;
   end
  end
 wire fa, fb7, fn;
 ot_s81hd_best64_tx u_ta (.ck(ck), .rn(rst_n), .v(tv_a),  .frame(tf_a),  .lane(a_tx_o),  .fault(fa));
 ot_s81hd_best64_tx u_tb (.ck(ck), .rn(rst_n), .v(tv_b7), .frame(tf_b7), .lane(b7_tx_o), .fault(fb7));
 ot_s81hd_best64_tx u_tn (.ck(ck), .rn(rst_n), .v(tv_n),  .frame(tf_n),  .lane(n_tx_o),  .fault(fn));
 // ---------------- ctl-side receivers (REAL ot_s81hd_mesh64_rx) -> REAL rank merge
 wire va0, vb0, va1, vb1, va2, vb2, rf0, rf1, rf2; wire [552:0] fr0, fr1, fr2; wire [11:0] ep0, ep1, ep2;
 ot_s81hd_mesh64_rx u_r0 (.ck(ck), .rn(rst_n), .lane(a_rx_i),  .va(va0), .vb(vb0), .frame(fr0), .ep_fault(ep0), .fault(rf0));
 ot_s81hd_mesh64_rx u_r1 (.ck(ck), .rn(rst_n), .lane(b7_rx_i), .va(va1), .vb(vb1), .frame(fr1), .ep_fault(ep1), .fault(rf1));
 ot_s81hd_mesh64_rx u_r2 (.ck(ck), .rn(rst_n), .lane(n_rx_i),  .va(va2), .vb(vb2), .frame(fr2), .ep_fault(ep2), .fault(rf2));
 // the receiver frame is shared by both copies of a peer: present it on both slots of the pair
 wire mv; wire [48:0] mrb; wire [30:0] mid; wire tagf, cpyf, nanf, chkv; wire [6:0] ovw;
 ot_s81hd_rank_merge_hsf0
`ifdef TOK16_MUT_ROW
  #(.MUT_ROW(1))
`endif
  u_rm (.ck(ck), .rst_pin_n(rst_n), .rst_hold_n(rst_n), .ov_p(ov), .orec_d(orec),
  .mrx_v({vb2, va2, vb1, va1, vb0, va0}), .mrx_d({fr2, fr2, fr1, fr1, fr0, fr0}),
  .valid(mv), .row_bits(mrb), .identity(mid), .tag_fault(tagf), .copy_fault(cpyf), .nan_fault(nanf), .check_valid(chkv),
  .overwrite(ovw));
 // copy check: hold copy A per pair and compare against copy B when it lands (the merge's slots see one shared frame bus)
 reg [96:0] ca [0:2]; integer cpy_bad = 0, ovw_n = 0;
 always @(posedge ck) begin
  if (va0) ca[0] <= fr0[96:0]; if (va1) ca[1] <= fr1[96:0]; if (va2) ca[2] <= fr2[96:0];
  if (vb0 && fr0[96:0] !== ca[0]) cpy_bad++; if (vb1 && fr1[96:0] !== ca[1]) cpy_bad++; if (vb2 && fr2[96:0] !== ca[2]) cpy_bad++;
  if (rst_n && |ovw) ovw_n++;
 end
 always @(posedge ck) if (rst_n && run) begin
  if (va0) $display("RM_LANE a_rx  copyA rec_rank%0d edge+%0d", fr0[7:4], cyc - res_cyc[nfin]);
  if (vb0) $display("RM_LANE a_rx  copyB rec_rank%0d edge+%0d", fr0[7:4], cyc - res_cyc[nfin]);
  if (va1) $display("RM_LANE b7_rx copyA rec_rank%0d edge+%0d", fr1[7:4], cyc - res_cyc[nfin]);
  if (vb1) $display("RM_LANE b7_rx copyB rec_rank%0d edge+%0d", fr1[7:4], cyc - res_cyc[nfin]);
  if (va2) $display("RM_LANE n_rx  copyA rec_rank%0d edge+%0d", fr2[7:4], cyc - res_cyc[nfin]);
  if (vb2) $display("RM_LANE n_rx  copyB rec_rank%0d edge+%0d", fr2[7:4], cyc - res_cyc[nfin]);
  if (chkv && (tagf || cpyf || nanf)) begin fbad++; $display("RM_CHECK_FAULT tag%0d copy%0d nan%0d", tagf, cpyf, nanf); end
  if (mv) begin
   $display("RANK_MERGE_RESULT pos%0d row%0d bits%08h pos_id%0d result_edge_to_merge%0d go_to_merge%0d", nfin, mrb[16:0], mrb[48:17],
            mid[30:10], cyc - res_cyc[nfin], cyc - go_cyc[nfin]);
   if (mrb[16:0] !== fin_row[16:0] || mrb[48:17] !== fin_bits || mid[30:10] !== 21'(nfin)) begin fbad++; $display("RANK_MERGE_MISMATCH pos%0d", nfin); end
   nfin++;
  end
 end
 final begin
  if (nres == npos && bad == 0) $display("DIE_SPINE PASS positions%0d", npos);
  else $display("DIE_SPINE FAIL results%0d of%0d bad%0d", nres, npos, bad);
  if (nfin == npos && fbad == 0 && cpy_bad == 0 && ovw_n == 0 && !(rf0|rf1|rf2|fa|fb7|fn) && (ep0|ep1|ep2) == 0)
   $display("RANK_MERGE PASS positions%0d", npos);
  else $display("RANK_MERGE FAIL merges%0d of%0d bad%0d copy_bad%0d ovw%0d rxf%0d%0d%0d txf%0d%0d%0d ep%03h/%03h/%03h", nfin, npos, fbad,
                cpy_bad, ovw_n, rf0, rf1, rf2, fa, fb7, fn, ep0, ep1, ep2);
 end
endmodule
`default_nettype wire
