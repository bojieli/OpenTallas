`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// TW-HBM-PGLG 2026-10-19: the STREAM service of one LIGHT SU port-group slice, split out of the slice so the landed slice
// parent (ot_hbm_su_static_pgslice_rgf_lp, kit hbm_su_pgslice_lg_light_d4g) is a single-frequency parent (PL-KIT landed
// clusters are related_same_frequency only). Contents = exactly the pg_clk logic of ot_hbm_su_static_pgslice_lg
// (STRAP / RSYNC / MULTIRATE / COLLPORT forms): the two VM bank leaves (pg_clk), their serial<->stream multirate bridges,
// the PG_RSYNC leaf reset synchroniser, the LG tap pair (ot_hbm_su_static_pg_lg_tap) and the COLLPORT inject slot capture +
// decode. A two-root (serial clk_ctl / stream pg_clk, 4:3 same-PLL) LEAF tile like hbm_su_pg_lgtap_1017; it abuts the
// slice's S band (E face), all its serial-side ports are flop-first / flop-last on clk_ctl except ij_* (decoded from the
// pg_clk slot registers, timed as the related 4:3 crossing) and the request bits taken straight from vmr_cmd.
// Behaviour and edges are unchanged against pgslice_lg (lockstep: tb_hbm_su_pgslice_rg through ot_hbm_su_static_pgslice_rg).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_static_pg_stream #(
 parameter integer QID=1,G=2,READ_RETURN=10,WRITE_RETURN=7,MUT=0,MULTIRATE=1,COLLPORT=1,B39_NOOP=(QID==0),
 parameter integer RSYNC=1,RSYNC_MUT=0,STRAP=1,IJ_REG=1
)(
 input wire clk_ctl,
 input wire pg_clk,
 input wire rst_n,
 input wire bridge_rst_n,
 input wire [3:0] pos,
 // serial side (slice S band)
 input wire [2*30-1:0] vmr_cmd,          // fill requests: {v, sector16} = vmr_cmd[h][29:13]
 input wire [2*281-1:0] su_wq,           // drain VM writes (slice S registers)
 output wire [2*257-1:0] su_rr,          // fill returns (serial, registered in the bridge)
 output wire [3:0] ij_v, output wire [35:0] ij_row, output wire ij_bad,   // inject port-5 reads per store group
 output wire pg_fault,                   // VM leaf / bridge checks (pg_clk registers)
 // COLLPORT inject (stream pin slots)
 input wire [1:0] inj_rd,
 input wire [159:0] inj_addr,
 // LG side
 output wire [33:0] lg_rq,
 output wire [561:0] lg_wq,
 input wire [513:0] lg_rr,
 input wire [1:0] lg_w_done,
 input wire [1:0] lg_read,lg_write,
 input wire [33:0] far_rq,
 input wire [561:0] far_wq,
 output wire [513:0] far_rr,
 output wire [1:0] far_w_done,
 output wire lg_fault
);
 wire [1:0] q_id=(STRAP!=0)?pos[3:2]:2'(QID);
 wire [1:0] g_id=(STRAP!=0&&MUT!=11)?pos[1:0]:2'(G);
 wire b39_on=(STRAP!=0)?(q_id==2'd0):(B39_NOOP!=0);
 // serial reset relay copy (as pgslice region 9: 2 sync + 1 tree) -> PG_RSYNC
 wire rst_s;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk_ctl),.rst_n_in(rst_n),.rst_n(rst_s));
 wire [33:0] s_rq; wire [561:0] s_wq; wire [513:0] s_rr; wire [1:0] s_done;
 wire [2*17-1:0] su_rq; wire [1:0] su_w_done,leaf_fault,bridge_fault;
 wire [33:0] leaf_rq; wire [561:0] leaf_wq; wire [513:0] leaf_rr; wire [1:0] leaf_done;
 wire leaf_rst_n;
 if(RSYNC)begin:g_pg_rsync
  reg rc; reg [1:0] rq;
  always @(posedge clk_ctl) rc <= rst_s;
  always @(posedge pg_clk) rq <= {rq[0], rc};
  assign leaf_rst_n = rq[1];
 end else begin:g_pg_rst_raw
  assign leaf_rst_n = rst_s;
 end
 for(genvar h=0;h<2;h=h+1)begin:g_leaf
  assign su_rq[h*17+:17]={vmr_cmd[h*30+29],vmr_cmd[h*30+13+:16]};
  if(MULTIRATE)begin:g_multirate
   ot_hbm_su_multirate_bridge #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN)) u_bridge(
    .serial_clk(clk_ctl),.stream_clk(pg_clk),.rst_n(bridge_rst_n),
    .serial_rq(su_rq[h*17+:17]),.serial_wq(su_wq[h*281+:281]),
    .serial_rr(su_rr[h*257+:257]),.serial_done(su_w_done[h]),
    .stream_rq(leaf_rq[h*17+:17]),.stream_wq(leaf_wq[h*281+:281]),
    .stream_rr(leaf_rr[h*257+:257]),.stream_done(leaf_done[h]),.fault(bridge_fault[h]));
  end else begin:g_same_clock
   assign leaf_rq[h*17+:17]=su_rq[h*17+:17]; assign leaf_wq[h*281+:281]=su_wq[h*281+:281];
   assign su_rr[h*257+:257]=leaf_rr[h*257+:257]; assign su_w_done[h]=leaf_done[h]; assign bridge_fault[h]=1'b0;
  end
  if(STRAP!=0)begin:g_leaf_s
  ot_hbm_su_static_vm_bank_leaf_s #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN)) u_leaf(
   .clk(pg_clk),.rst_n(leaf_rst_n),.qid(q_id),.b({g_id,1'(h)}),.su_rq(leaf_rq[h*17+:17]),.su_wq(leaf_wq[h*281+:281]),
   .su_rr(leaf_rr[h*257+:257]),.su_w_done(leaf_done[h]),.lg_rq(s_rq[h*17+:17]),.lg_wq(s_wq[h*281+:281]),
   .lg_rr(s_rr[h*257+:257]),.lg_w_done(s_done[h]),.fault(leaf_fault[h]));
  end else begin:g_leaf_p
  ot_hbm_su_static_vm_bank_leaf #(.QID(QID),.B(2*G+h),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN)) u_leaf(
   .clk(pg_clk),.rst_n(leaf_rst_n),.su_rq(leaf_rq[h*17+:17]),.su_wq(leaf_wq[h*281+:281]),.su_rr(leaf_rr[h*257+:257]),
   .su_w_done(leaf_done[h]),.lg_rq(s_rq[h*17+:17]),.lg_wq(s_wq[h*281+:281]),.lg_rr(s_rr[h*257+:257]),
   .lg_w_done(s_done[h]),.fault(leaf_fault[h]));
  end
 end
 assign pg_fault=(|leaf_fault)||(|bridge_fault);
 if(RSYNC)begin:g_tap
  ot_hbm_su_static_pg_lg_tap #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.RSYNC_MUT(RSYNC_MUT)) u_tap(
   .clk_ctl(clk_ctl),.pg_clk(pg_clk),.rst_n(rst_n),.local_rq(s_rq),.far_rq(far_rq),.local_wq(s_wq),.far_wq(far_wq),
   .local_read(lg_read),.local_write(lg_write),.near_rq(lg_rq),.near_wq(lg_wq),.near_rr(lg_rr),.near_w_done(lg_w_done),
   .local_rr(s_rr),.far_rr(far_rr),.local_w_done(s_done),.far_w_done(far_w_done),.fault(lg_fault));
 end else begin:g_tap_r8b
  (* keep = "true" *) reg lg_rst; always @(posedge pg_clk) lg_rst <= rst_n;
  ot_hbm_vm_lg_pair_tap #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN)) u_tap(
   .clk(pg_clk),.rst_n(lg_rst),.local_rq(s_rq),.far_rq(far_rq),.local_wq(s_wq),.far_wq(far_wq),
   .local_read(lg_read),.local_write(lg_write),.near_rq(lg_rq),.near_wq(lg_wq),.near_rr(lg_rr),.near_w_done(lg_w_done),
   .local_rr(s_rr),.far_rr(far_rr),.local_w_done(s_done),.far_w_done(far_w_done),.fault(lg_fault));
 end
 // ---- COLLPORT inject slot capture + decode (as pgslice)
 if(COLLPORT!=0)begin:g_inj
  reg [1:0] sp; reg [1:0] sq;
  always @(posedge pg_clk or negedge bridge_rst_n) if(!bridge_rst_n) sp<=2'd0; else sp<=sp+2'd1;
  always @(posedge clk_ctl or negedge bridge_rst_n) if(!bridge_rst_n) sq<=2'd0; else sq<=(sq==2'd2)?2'd0:sq+2'd1;
  reg [161:0] slot [0:3];
  always @(posedge pg_clk) slot[sp] <= {inj_rd, inj_addr};
  wire [1:0] rsl = ((sq==2'd1)?2'd0:(sq==2'd2)?2'd1:2'd3) + ((MUT==8)?2'd1:2'd0);
  // IJ_REG 1 (TW-HBM-PGLG 10-19, kit gate OT_MULTI_ROOT: a tile output must come from registers of ONE declared domain):
  // the decode is registered on pg_clk. Every serial cycle [t, t+T_s) holds exactly one pg_clk edge e strictly inside it
  // (3:4 common epoch: serial 0/1111/2222, stream 833/1667/2500), and no pg_clk edge lies between e and the slice's
  // capture at t+T_s, so registering decode(slot[rsl(sq_t)]) at e -- with the slot written at e itself bypassed --
  // gives the slice exactly the value the comb form (IJ_REG 0) presented at t+T_s. 0 added edges.
  wire [161:0] ij = (IJ_REG!=0 && rsl==sp) ? {inj_rd, inj_addr} : slot[rsl];
  reg [3:0] v; reg [35:0] row; reg bad; integer k;
  always @* begin
   v=0; row=0; bad=0;
   for(k=0;k<4;k=k+1) begin : dec
    reg [39:0] a, lo; reg on; reg [1:0] grp;
    a = ij[40*k+:40]; lo = ij[80*(k/2)+:40];
    on = ij[160+(k/2)] && !(b39_on && lo[39] && MUT!=9) && a[5:4]==g_id;
    grp = {a[6],a[3]};
    if(on) begin
     if(v[grp] && row[9*grp+:9]!=a[15:7]) bad=1'b1;
     v[grp]=1'b1; row[9*grp+:9]=a[15:7];
    end
   end
  end
  if(IJ_REG!=0)begin:g_ij_reg
   reg [3:0] v_q; reg [35:0] row_q; reg bad_q;
   always @(posedge pg_clk) begin v_q<=v; row_q<=row; bad_q<=bad; end
   assign ij_v=v_q; assign ij_row=row_q; assign ij_bad=bad_q;
  end else begin:g_ij_comb
   assign ij_v=v; assign ij_row=row; assign ij_bad=bad;
  end
 end else begin:g_no_inj
  assign ij_v=4'd0; assign ij_row=36'd0; assign ij_bad=1'b0;
 end
endmodule
`default_nettype wire
