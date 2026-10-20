`timescale 1ns/1ps
// QW-N59-4 (10-19): lockstep SHADOW of the hardened split (qfd_native59_split_flat, or its landed form with -DN59_SPLIT_LP)
// against the flat native59 block (qfd_native59_dv_service[_r1]) that a bench already drives.  Connect the same input
// expressions as the reference DUT and the reference's outputs.  The shadow presents the bank ports (dd_i,
// layer_context_v, command_stage, q_slot, q_slot_beat) BOFF edges and every other input SOFF edges after the reference
// (flat split: BOFF 0 / SOFF 1 / ROFF 1; landed form: + the lp record's port offsets), and requires every output of the
// split to equal the reference's output ROFF edges earlier, on every edge from CMP0 + ROFF on while cmp_en.  mism = number of mismatching
// edges (first 8 printed as N59SPLIT_ERR).  The bench fails on mism != 0 (N59DV_FAIL / N59MU_FAIL).
module n59_split_shadow #(parameter integer NU=4,parameter [13:0] MU_SEQ0=14'd0,parameter integer MCTX=1,EMBR=1,MUT=0,
                          QB_MUT=0,LP_MUT=0,SOFF=1,BOFF=0,ROFF=1,CMP0=8)(
 input wire ck,rst_n,cmp_en,
 input wire host_epoch_valid,host_fused_capability,input wire[15:0]host_epoch,
 input wire[58:0]host_tag,input wire[1:0]host_generation,
 input wire layer_context_v,input wire[5:0]command_stage,
 input wire[17:0]native_token,native_position,input wire[379:0]native_cmd,
 input wire[547:0]dd_i,
 input wire kv_word_slot,input wire[1:0]kv_word_index,input wire kv_x3_slot,
 input wire q_slot,input wire[4:0]q_slot_beat,
 input wire tx_slot,input wire[3:0]tx_slot_kind,input wire[4:0]tx_slot_beat,
 input wire native_rx_v,input wire[547:0]native_rx_payload,
 input wire rx_slot,input wire[3:0]rx_slot_kind,input wire[4:0]rx_slot_beat,
 input wire[511:0]emb_code_q,input wire[15:0]emb_scale_q,
 input wire visibility_slot,complete_slot,
 // reference outputs
 input wire[523:0]r_x3,input wire[58:0]r_x3_identity,input wire[1:0]r_x3_generation,
 input wire r_native_tx_v,input wire[547:0]r_native_tx_payload,input wire[519:0]r_dr_o,
 input wire r_emb_code_re,input wire[23:0]r_emb_code_addr,input wire r_emb_scale_re,input wire[17:0]r_emb_scale_addr,
 input wire r_completed,input wire[94:0]r_native_ret,input wire r_fault,
 output integer mism,output integer compared
);
 // service-side inputs SOFF edges later
 localparam integer SW=1+1+16+59+2+18+18+380+1+2+1+1+4+5+1+548+1+4+5+512+16+1+1;
 wire[SW-1:0]s_now={host_epoch_valid,host_fused_capability,host_epoch,host_tag,host_generation,native_token,native_position,
  native_cmd,kv_word_slot,kv_word_index,kv_x3_slot,tx_slot,tx_slot_kind,tx_slot_beat,native_rx_v,native_rx_payload,rx_slot,
  rx_slot_kind,rx_slot_beat,emb_code_q,emb_scale_q,visibility_slot,complete_slot};
 integer i;
 reg[SW-1:0]s_p[1:SOFF];
 always @(posedge ck)begin s_p[1]<=s_now;for(i=2;i<=SOFF;i=i+1)s_p[i]<=s_p[i-1];end
 wire[SW-1:0]s=s_p[SOFF];
 wire d_hev,d_hfc;wire[15:0]d_he;wire[58:0]d_ht;wire[1:0]d_hg;wire[17:0]d_tok,d_pos;wire[379:0]d_cmd;
 wire d_kvs;wire[1:0]d_kvi;wire d_x3s,d_ts;wire[3:0]d_tk;wire[4:0]d_tb;wire d_rv;wire[547:0]d_rp;wire d_rs;wire[3:0]d_rk;
 wire[4:0]d_rb;wire[511:0]d_ecq;wire[15:0]d_esq;wire d_vis,d_cs;
 assign {d_hev,d_hfc,d_he,d_ht,d_hg,d_tok,d_pos,d_cmd,d_kvs,d_kvi,d_x3s,d_ts,d_tk,d_tb,d_rv,d_rp,d_rs,d_rk,d_rb,d_ecq,d_esq,d_vis,d_cs}=s;
 // bank-side inputs BOFF edges later
 localparam integer BW=548+1+6+1+5;
 wire[BW-1:0]b_now={dd_i,layer_context_v,command_stage,q_slot,q_slot_beat};
 wire[BW-1:0]b_sel;
 generate if(BOFF==0)begin:g_b0 assign b_sel=b_now; end else begin:g_bd
  reg[BW-1:0]b_p[1:BOFF];
  always @(posedge ck)begin b_p[1]<=b_now;for(integer j=2;j<=BOFF;j=j+1)b_p[j]<=b_p[j-1];end
  assign b_sel=b_p[BOFF];
 end endgenerate
 wire[547:0]b_dd;wire b_lcv;wire[5:0]b_st;wire b_qs;wire[4:0]b_qb;
 assign {b_dd,b_lcv,b_st,b_qs,b_qb}=b_sel;
 wire[523:0]x3;wire[58:0]xid;wire[1:0]xg;wire tv;wire[547:0]td;wire[519:0]dr;wire cre,sre;wire[23:0]caddr;wire[17:0]saddr;
 wire done,flt;wire[94:0]ret;
`ifdef N59_SPLIT_LP
 qfd_native59_split_flat_lp #(.MUT(LP_MUT),.SMUT(MUT),.QB_MUT(QB_MUT),.NU(NU),.MU_SEQ0(MU_SEQ0),.MCTX(MCTX),.EMB_RELAY(EMBR)) u_split(
  .ck_qb(ck),.ck_svc(ck),.rst_n(rst_n),
`else
 qfd_native59_split_flat #(.SMUT(MUT),.QB_MUT(QB_MUT),.NU(NU),.MU_SEQ0(MU_SEQ0),.MCTX(MCTX),.EMB_RELAY(EMBR)) u_split(
  .ck(ck),.rst_n(rst_n),
`endif
  .host_epoch_valid(d_hev),.host_fused_capability(d_hfc),.host_epoch(d_he),.host_tag(d_ht),.host_generation(d_hg),
  .layer_context_v(b_lcv),.command_stage(b_st),.native_token(d_tok),.native_position(d_pos),.native_cmd(d_cmd),
  .dd_i(b_dd),.kv_word_slot(d_kvs),.kv_word_index(d_kvi),.kv_x3_slot(d_x3s),
  .x3(x3),.x3_identity(xid),.x3_generation(xg),.q_slot(b_qs),.q_slot_beat(b_qb),
  .tx_slot(d_ts),.tx_slot_kind(d_tk),.tx_slot_beat(d_tb),.native_tx_v(tv),.native_tx_payload(td),
  .native_rx_v(d_rv),.native_rx_payload(d_rp),.rx_slot(d_rs),.rx_slot_kind(d_rk),.rx_slot_beat(d_rb),.dr_o(dr),
  .emb_code_re(cre),.emb_code_addr(caddr),.emb_scale_re(sre),.emb_scale_addr(saddr),.emb_code_q(d_ecq),.emb_scale_q(d_esq),
  .visibility_slot(d_vis),.complete_slot(d_cs),.completed(done),.native_ret(ret),.fault(flt));
 // reference outputs ROFF edges later
 localparam integer OW=524+59+2+1+548+520+1+24+1+18+1+95+1;
 wire[OW-1:0]r_now={r_x3,r_x3_identity,r_x3_generation,r_native_tx_v,r_native_tx_payload,r_dr_o,r_emb_code_re,
  r_emb_code_addr,r_emb_scale_re,r_emb_scale_addr,r_completed,r_native_ret,r_fault};
 wire[OW-1:0]n_now={x3,xid,xg,tv,td,dr,cre,caddr,sre,saddr,done,ret,flt};
 reg[OW-1:0]r_p[1:ROFF];
 always @(posedge ck)begin r_p[1]<=r_now;for(i=2;i<=ROFF;i=i+1)r_p[i]<=r_p[i-1];end
 wire[OW-1:0]r_ref=r_p[ROFF];
 reg[31:0]cyc=0;
 always @(posedge ck)cyc<=cyc+1;
 initial begin mism=0;compared=0;end
 always @(posedge ck)if(cyc>=CMP0+ROFF&&cmp_en)begin
  compared<=compared+1;
  if(n_now!==r_ref)begin
   mism<=mism+1;
   if(mism<8)$display("N59SPLIT_ERR cycle %0d: split output != reference %0d edge(s) earlier (x3 %0d tx %0d dr %0d emb %0d done %0d ret %0d fault %0d)",
     cyc,ROFF,{x3,xid,xg}!=={r_ref[OW-1-:585]},{tv,td}!=={r_ref[OW-586-:549]},dr!==r_ref[OW-1135-:520],
     {cre,caddr,sre,saddr}!==r_ref[OW-1655-:44],done!==r_ref[96],ret!==r_ref[95:1],flt!==r_ref[0]);
  end
 end
endmodule
