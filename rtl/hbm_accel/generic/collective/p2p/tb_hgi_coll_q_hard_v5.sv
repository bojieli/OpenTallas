`timescale 1ns/1ps
// H-NETLIST/COLL 1045: lockstep proof of the hard-hierarchy COLL quadrant (ot_hfd_coll_q{2,3}_hard_v5) against the
// production host_v4 parent, plus the aggregate fault / visibility / containment ABI.
// Both parents run the SAME actual HOST F20 programme (the host_v4 native reduction programme: 2 SU injects, FP32
// reduce, publication at host-launch cycle 36, halt 40) from the same stimulus. Every cycle, every non-fault output
// of the two must be identical -- the hard parent's issue-path outputs 2 edges later (V5 issue timing: the uop
// stream is delayed 2 edges for the pipelined iteration products, HOST frames captured +1 at the fj pins; the hard
// parent's SU boundary and injected stimuli follow its own requests / 3 edges later; programme target +1;
// every child fault additionally +1 at the fj pin registers) -- (normal path exact AND containment: an injected fault never changes a reservation,
// valid or payload). Fault ABI per scenario (+SCEN=n): first host-visible fault edge of the hard parent minus that
// of host_v4 must equal the documented delta, and fault_cause must name the faulting child at its first edge:
//   0 none (fault never; foreign-target frames ignored by both)  delta -, cause 0
//   1 unexpected RX on rail 0                                     delta 0, cause bit 6
//   2 unexpected RED_CARRY rc_v                                   delta +1, cause bit 2 (V7: rc_v pin-captured)
//   3 q2 illegal tkm reservation                                  delta 0, cause bit 13
//   4 qslots capture reservation without source (VM0)             delta +1, cause bit 3 (pin_v2)
//   5 q2 arg capture reservation (no arg source in q2)            delta -1, cause bit 12
//   6 programme frame fault on own target                         delta 0, cause bit 0
// Define Q3 for the SW q3 parent (QID 0, target 52, 3 rails); default q2 (QID 1, target 53, 2 rails).
module tb_hgi_coll_q_hard_v5;
// d4f: -DOT_TB_NLINK=n (link lanes; default 3 for Q3, 2 for q2) and -DOT_TB_TP=t (ARGMAX/TKM ranks, default 96) set
// the SAME parameters on the host_v4 reference and the hard parent.
`ifdef OT_TB_TP
 localparam integer TPV=`OT_TB_TP;
`else
 localparam integer TPV=96;
`endif
`ifdef Q3
`ifdef OT_TB_NLINK
 localparam integer NPT=`OT_TB_NLINK;
`else
 localparam integer NPT=3;
`endif
 localparam integer QID=0,NCKQ=NPT+8+18,NR=36;
`else
`ifdef OT_TB_NLINK
 localparam integer NPT=`OT_TB_NLINK;
`else
 localparam integer NPT=2;
`endif
 localparam integer QID=1,NCKQ=NPT+7+18,NR=36;
`endif
 localparam [7:0] TGT=8'd52+8'(QID);
 localparam integer ND=NPT+13,REDSRC=NPT+6;
 integer scen=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cv=0,dv_cfg=0,launch=0;
 reg [7:0] cfg_target=TGT;reg [11:0] cfg_addr=0;reg [255:0] cfg_data=0;
 reg rcv=0;reg [NPT-1:0] rxv=0;
 // ---- reference (host_v4) and hard (v5) outputs
 wire r_conf,r_init,r_pf,r_busy,r_done,r_hf,r_fault,r_done2,r_rv;
 wire n_conf,n_init,n_pf,n_busy,n_done,n_hf,n_fault,n_done2,n_rv;
 wire [1:0] r_ird,n_ird;wire [31:0] r_iidx,n_iidx,r_cyc,n_cyc;wire [159:0] r_iad,n_iad,r_ob,n_ob;
 wire [3:0] r_dv,n_dv;wire [2179:0] r_dd,n_dd;wire [2:0] r_rt,n_rt;wire [255:0] r_rd,n_rd;
 wire [NPT-1:0] r_txv,n_txv,r_rty,n_rty;wire [NPT*612-1:0] r_txd,n_txd;
 wire [279:0] r_cw,n_cw,r_ccw,n_ccw;wire [135:0] r_rq,n_rq;wire [2247:0] r_kq,n_kq;
 wire [15:0] n_cause;
 // ---- SU boundary (requests observed P+1, answer captured P+12), driven from the reference requests
 localparam integer SUL=11;
 reg [15:0] source_index[0:SUL-1];reg source_rd[0:SUL-1];
 always @(posedge clk)begin
  source_index[0]<=r_iidx[15:0];source_rd[0]<=r_ird[0];
  for(integer p=1;p<SUL;p=p+1)begin source_index[p]<=source_index[p-1];source_rd[p]<=source_rd[p-1];end
 end
 function automatic [511:0] source_word(input [15:0] index);
  for(integer l=0;l<16;l=l+1)source_word[l*32+:32]=(index==0?32'h3f800000:32'h40000000)+32'(l<<23);
 endfunction
 // Declared external VM read boundary, fixed seven-edge return after the pin request.
 reg [7:0] r_vm_valid[0:6],n_vm_valid[0:6];
 wire [2055:0] r_vm_response,n_vm_response;
 function automatic [255:0] vm_payload(input integer bank);
  for(integer w=0;w<8;w=w+1)vm_payload[w*32+:32]=32'h564d0000+32'(bank*256+w);
 endfunction
 initial for(integer t=0;t<7;t=t+1)begin r_vm_valid[t]=0;n_vm_valid[t]=0;end
 always @(posedge clk)begin
  for(integer bank=0;bank<8;bank=bank+1)begin
   r_vm_valid[0][bank]<=r_rq[bank*17+16];n_vm_valid[0][bank]<=n_rq[bank*17+16];
  end
  for(integer t=1;t<7;t=t+1)begin r_vm_valid[t]<=r_vm_valid[t-1];n_vm_valid[t]<=n_vm_valid[t-1];end
 end
 for(genvar bank=0;bank<8;bank=bank+1)begin:VM_INPUT
  assign r_vm_response[bank*257+:257]={r_vm_valid[6][bank],vm_payload(bank)};
  assign n_vm_response[bank*257+:257]={n_vm_valid[6][bank],vm_payload(bank)};
 end
 wire [1023:0] inj_data={512'd0,source_rd[SUL-1]?source_word(source_index[SUL-1]):512'd0};
 // hard parent: its own SU boundary (driven by its own requests) and the same stimuli 2 edges later
 localparam integer SH=4,SHP=1;  // V6 issue path +4 (frame capture +1, uop delay +3); programme target +1
 reg [15:0] n_source_index[0:SUL-1];reg n_source_rd[0:SUL-1];
 always @(posedge clk)begin
  n_source_index[0]<=n_iidx[15:0];n_source_rd[0]<=n_ird[0];
  for(integer p=1;p<SUL;p=p+1)begin n_source_index[p]<=n_source_index[p-1];n_source_rd[p]<=n_source_rd[p-1];end
 end
 wire [1023:0] n_inj_data={512'd0,n_source_rd[SUL-1]?source_word(n_source_index[SUL-1]):512'd0};
 // injected die inputs reach the hard parent SH edges after the reference (its whole schedule is shifted by SH)
 reg [NPT-1:0] rxv_h[1:SH];reg rcv_h[1:SH];
 initial for(integer h=1;h<=SH;h=h+1)begin rxv_h[h]=0;rcv_h[h]=0;end
 always @(posedge clk)begin rxv_h[1]<=rxv;rcv_h[1]<=rcv;for(integer h=2;h<=SH;h=h+1)begin rxv_h[h]<=rxv_h[h-1];rcv_h[h]<=rcv_h[h-1];end end
 wire [NPT-1:0] rxv_d3=rxv_h[SH];wire rcv_d3=rcv_h[SH];
`ifdef Q3
 ot_hfd_coll_q3_static_host_v4 #(.NLINK(NPT),.TP(TPV),.QID(2'(QID))) ref_q(.rst_n(rst_n),.clk_program(clk),.clk_control(clk),
  .clk_issue({4{clk}}),.clk_qslots({2{clk}}),.clk_ring({17{clk}}),.clk_reduce({33{clk}}),.clk_arg(clk),
  .clk_tkm({34{clk}}),.clk_vmwrite(clk),.clk_link({5*NPT{clk}}),
`else
 ot_hfd_coll_q2_static_host_v4 #(.NLINK(NPT),.TP(TPV),.QID(2'(QID))) ref_q(.rst_n(rst_n),.clk_program(clk),.clk_control(clk),
  .clk_issue({4{clk}}),.clk_qslots({2{clk}}),.clk_ring({17{clk}}),.clk_reduce({33{clk}}),
  .clk_vmwrite(clk),.clk_link({5*NPT{clk}}),
`endif
  .cfg_v(cv),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(dv_cfg),.desc_base(12'd0),.desc_limit(13'(NR)),.desc_loops(16'd1),.launch_v(launch),
  .program_configured(r_conf),.program_init_busy(r_init),.program_fault(r_pf),.hgi_busy(r_busy),.hgi_done(r_done),
  .hgi_fault(r_hf),.inj_rd(r_ird),.inj_idx(r_iidx),.hgi_inj_addr(r_iad),.inj_d(inj_data),
  .del_valid(r_dv),.del_flit(r_dd),.hgi_del_obase(r_ob),.rc_v(rcv),.rc_tag(3'd0),.rc_d(256'd0),
  .rr_v(r_rv),.rr_tag(r_rt),.rr_d(r_rd),.phy_up({NPT{1'b1}}),.tx_pin_v(r_txv),.tx_pin_flit(r_txd),
  .rx_pin_v(rxv),.rx_pin_flit({NPT*612{1'b0}}),.retry_requested(r_rty),
  .pr_cw_i(280'd0),.pr_ccw_i(280'd0),.pr_cw_o(r_cw),.pr_ccw_o(r_ccw),
  .vm_rq(r_rq),.vm_rr(r_vm_response),.vm_kq(r_kq),.fault(r_fault),.done(r_done2),.stat_cycles(r_cyc));
`ifdef OT_TB_TKX
 // d4f TKM hoist: the external-TKM parent q3_hard_v7x + the die-level TKM sub-cluster, wired here (zero-latency hop)
 wire tx_start,tx_mode,tx_has_r,tx_wv,tx_busy,tx_done,tx_fault;wire [11:0] tx_n;wire [12:0] tx_k,tx_nout;
 wire [7:0] tx_g,tx_gb;wire [15:0] tx_pf,tx_wm;wire [39:0] tx_ob,tx_rb,tx_wa;wire [3:0] tx_ds,tx_dv;wire [2179:0] tx_df;
 wire [511:0] tx_wd;
 ot_hgi_coll_tkm_m #(.TP(TPV)) u_tkx(.clk(clk),.tile_clk({32{clk}}),.buffer_clk(clk),.rst_n(rst_n),.start(tx_start),
  .arg_mode(tx_mode),.cfg_n(tx_n),.cfg_k(tx_k),.cfg_nout(tx_nout),.cfg_g(tx_g),.cfg_gbase(tx_gb),.cfg_pf(tx_pf),
  .cfg_obase(tx_ob),.cfg_rbase(tx_rb),.cfg_has_r(tx_has_r),.del_slot(tx_ds),.del_valid(tx_dv),.del_flit(tx_df),
  .w_v(tx_wv),.w_addr(tx_wa),.w_mask(tx_wm),.w_data(tx_wd),.busy(tx_busy),.done(tx_done),.fault(tx_fault),.stat_cycles());
 ot_hfd_coll_q3_hard_v7x #(.NLINK(NPT),.TP(TPV)) dut(.rst_n(rst_n),.qid(2'(QID)),.clk_program(clk),.clk_control(clk),.clk_vmasm({16{clk}}),.clk_upipe({16{clk}}),
  .clk_issue(clk),.clk_qslots({NCKQ{clk}}),.clk_ring({17{clk}}),.clk_reduce({33{clk}}),.clk_arg(clk),
  .clk_vmwrite({16{clk}}),.clk_link({5*NPT{clk}}),
  .tkx_start(tx_start),.tkx_arg_mode(tx_mode),.tkx_cfg_n(tx_n),.tkx_cfg_k(tx_k),.tkx_cfg_nout(tx_nout),.tkx_cfg_g(tx_g),
  .tkx_cfg_gbase(tx_gb),.tkx_cfg_pf(tx_pf),.tkx_cfg_obase(tx_ob),.tkx_cfg_rbase(tx_rb),.tkx_cfg_has_r(tx_has_r),
  .tkx_del_slot(tx_ds),.tkx_del_valid(tx_dv),.tkx_del_flit(tx_df),.tkx_w_v(tx_wv),.tkx_w_addr(tx_wa),.tkx_w_mask(tx_wm),
  .tkx_w_data(tx_wd),.tkx_busy(tx_busy),.tkx_done(tx_done),.tkx_fault(tx_fault),
`elsif Q3
 ot_hfd_coll_q3_hard_v5 #(.NLINK(NPT),.TP(TPV)) dut(.rst_n(rst_n),.qid(2'(QID)),.clk_program(clk),.clk_control(clk),.clk_vmasm({16{clk}}),.clk_upipe({16{clk}}),
  .clk_issue(clk),.clk_qslots({NCKQ{clk}}),.clk_ring({17{clk}}),.clk_reduce({33{clk}}),.clk_arg(clk),
  .clk_tkm({34{clk}}),.clk_vmwrite({16{clk}}),.clk_link({5*NPT{clk}}),
`else
 ot_hfd_coll_q2_hard_v5 #(.NLINK(NPT),.TP(TPV)) dut(.rst_n(rst_n),.qid(2'(QID)),.clk_program(clk),.clk_control(clk),.clk_vmasm({16{clk}}),.clk_upipe({16{clk}}),
  .clk_issue(clk),.clk_qslots({NCKQ{clk}}),.clk_ring({17{clk}}),.clk_reduce({33{clk}}),
  .clk_vmwrite({16{clk}}),.clk_link({5*NPT{clk}}),
`endif
  .cfg_v(cv),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(dv_cfg),.desc_base(12'd0),.desc_limit(13'(NR)),.desc_loops(16'd1),.launch_v(launch),
  .program_configured(n_conf),.program_init_busy(n_init),.program_fault(n_pf),.hgi_busy(n_busy),.hgi_done(n_done),
  .hgi_fault(n_hf),.inj_rd(n_ird),.inj_idx(n_iidx),.hgi_inj_addr(n_iad),.inj_d(n_inj_data),
  .del_valid(n_dv),.del_flit(n_dd),.hgi_del_obase(n_ob),.rc_v(rcv_d3),.rc_tag(3'd0),.rc_d(256'd0),
  .rr_v(n_rv),.rr_tag(n_rt),.rr_d(n_rd),.phy_up({NPT{1'b1}}),.tx_pin_v(n_txv),.tx_pin_flit(n_txd),
  .rx_pin_v(rxv_d3),.rx_pin_flit({NPT*612{1'b0}}),.retry_requested(n_rty),
  .pr_cw_i(280'd0),.pr_ccw_i(280'd0),.pr_cw_o(n_cw),.pr_ccw_o(n_ccw),
  .vm_rq(n_rq),.vm_rr(n_vm_response),.vm_kq(n_kq),.fault(n_fault),.fault_cause(n_cause),.done(n_done2),.stat_cycles(n_cyc));
 // ---- lockstep monitor
 integer cyc=0,checks=0,rf=-1,nf=-1,mism=0,outputs=0,halts=0;
 reg [15:0] first_cause=0;
 wire [2:0] r_prog={r_conf,r_init,r_pf},n_prog={n_conf,n_init,n_pf};
 wire [8191:0] r_vec={r_busy,r_done,r_ird,r_iidx,r_iad,r_dv,r_dd,r_ob,r_rv,r_rt,r_rd,
  r_txv,r_txd,r_rty,r_cw,r_ccw,r_rq,r_kq,r_done2,r_cyc};
 wire [8191:0] n_vec={n_busy,n_done,n_ird,n_iidx,n_iad,n_dv,n_dd,n_ob,n_rv,n_rt,n_rd,
  n_txv,n_txd,n_rty,n_cw,n_ccw,n_rq,n_kq,n_done2,n_cyc};
 reg [8191:0] r_hist[0:SH];reg [2:0] p_hist[0:SHP];
 always @(negedge clk)if(rst_n)begin
  cyc<=cyc+1;checks<=checks+1;
  for(integer h=SH;h>0;h=h-1)r_hist[h]=r_hist[h-1];r_hist[0]=r_vec;
  for(integer h=SHP;h>0;h=h-1)p_hist[h]=p_hist[h-1];p_hist[0]=r_prog;
  if((cyc>=SHP && p_hist[SHP]!==n_prog) || (cyc>=SH && r_hist[SH]!==n_vec))begin
   mism=mism+1;
   if(mism<6)$display("MISMATCH cyc%0d conf%b/%b init%b/%b pf%b/%b busy%b/%b done%b/%b ird%h/%h dv%h/%h ob%h/%h txv%h/%h rq_eq%0d kq_eq%0d dd_eq%0d cyc%0d/%0d",
    cyc,r_conf,n_conf,r_init,n_init,r_pf,n_pf,r_busy,n_busy,r_done,n_done,r_ird,n_ird,r_dv,n_dv,r_ob[39:0],n_ob[39:0],
    r_txv,n_txv,r_rq==n_rq,r_kq==n_kq,r_dd==n_dd,r_cyc,n_cyc);
  end
  if(r_hf!==r_fault || n_hf!==n_fault)$fatal(1,"hgi_fault/fault alias broken");
  if(r_fault && rf<0)rf=cyc;
  if(n_fault && nf<0)begin nf=cyc;first_cause=n_cause;end
  if(nf>=0 && !n_fault)$fatal(1,"hard parent fault not sticky");
 end
 // ---- programme (host_v4 native reduce programme, actual F20 frames)
 reg [1535:0] code[0:NR-1];reg [54:0] ar;
 task host_frame(input [7:0] tgt,input integer row,input integer segment,input [255:0] value);
  begin @(negedge clk);cv=1;cfg_target=tgt;cfg_addr=12'(row*8+segment);cfg_data=value;end
 endtask
 task pack_ar(input integer row,input [54:0] control);
  begin code[row][1505+:31]=control[30:0];code[row][688+:24]=control[54:31];end
 endtask
 integer exp_delta,exp_bit,vm_outputs=0;
 initial begin
  if(!$value$plusargs("SCEN=%d",scen))scen=0;
  for(integer n=0;n<NR;n=n+1)code[n]=0;
  code[0][90]=1;code[0][284+:33]={1'b1,8'hff,8'd0,16'd0};
  code[1][90]=1;code[1][92+:16]=16'd1;code[1][284+:33]={1'b1,8'hff,8'd1,16'd1};
  code[12][0]=1;code[13][0]=1;
  code[13][10+ND-1]=1;code[13][26+(ND-1)*4+:4]=0;
  code[14][10+ND-1]=1;code[14][26+(ND-1)*4+:4]=0;
  ar=0;ar[0]=1;ar[1+:4]=0;pack_ar(15,ar);
  ar=0;ar[5]=1;ar[6+:4]=0;pack_ar(16,ar);
  ar=0;ar[10]=1;pack_ar(17,ar);
  ar=0;ar[11]=1;ar[12+:4]=0;ar[21]=1;ar[23+:8]=8'd7;ar[31+:16]=16'd13;pack_ar(26,ar);
  ar=0;ar[22]=1;pack_ar(27,ar);
  code[28][REDSRC]=1;
  code[29][10+NPT]=1;code[29][26+NPT*4+:4]=4'(REDSRC);
  // the halt row leaves a delivery base on the control pins: an unmasked issuer would keep republishing it
  code[NR-1][874+:40]=40'h12345;
  // A legal VM read, assembly, slot capture and delivery. Bank0 and bank7 differ in every word.
  if(scen==7)begin
   code[4][1034+16]=1;code[4][1034+7*17+16]=1;
   code[4][1383+:6]={3'd7,3'd0};
   code[4][1170+:33]={1'b1,8'h56,8'h4d,16'h0700};
   code[14][2+NPT]=1;
   code[15][10+NPT]=1;code[15][26+NPT*4+:4]=4'(2+NPT);
  end
  exp_delta=0;exp_bit=-1;
  case(scen)
   1:begin exp_delta=0;exp_bit=6;end
   2:begin exp_delta=1;exp_bit=2;end
   3:begin exp_delta=0;exp_bit=13;code[20][718]=1;end
   4:begin exp_delta=1;exp_bit=3;code[20][2+NPT]=1;end
   5:begin exp_delta=-1;exp_bit=12;code[20][NPT+7]=1;end   // q2 arg capture slot = NPT+7 (9 at NLINK 2)
   6:begin exp_delta=0;exp_bit=0;end
   default:;
  endcase
`ifdef Q3
  if(scen==3 || scen==5)$fatal(1,"scenario %0d is q2-only",scen);
`endif
  repeat(4)@(negedge clk);rst_n=1;
  for(integer row=0;row<NR;row=row+1)begin
   reg [63:0] metadata;
   metadata=64'(row+1);if(row==NR-1)metadata[44]=1;
   for(integer segment=0;segment<6;segment=segment+1)host_frame(TGT,row,segment,code[row][segment*256+:256]);
   host_frame(TGT,row,6,{192'b0,metadata});
   @(negedge clk);cv=0;
   repeat(55)@(negedge clk);
   if(r_init || r_pf)$fatal(1,"reference row drain did not finish on reserved edge");
  end
  // identity strap: a malformed frame for ANOTHER quadrant's target must be ignored by both parents
  host_frame(TGT+8'd1,0,0,256'd0);host_frame(TGT+8'd1,0,7,256'd1);@(negedge clk);cv=0;
  repeat(4)@(negedge clk);
  @(negedge clk);dv_cfg=1;cfg_target=TGT;
  @(negedge clk);dv_cfg=0;repeat(66)@(negedge clk);
  if(!r_conf || r_pf)$fatal(1,"descriptor did not validate");
  if(scen==6)begin host_frame(TGT,0,7,256'd1);@(negedge clk);cv=0;end
  @(negedge clk);launch=1;@(posedge clk);#1;
  for(integer c=1;c<60;c=c+1)begin
   @(negedge clk);launch=0;
   rxv=(scen==1 && c==20)?{{(NPT-1){1'b0}},1'b1}:'0;
   rcv=(scen==2 && c==20);
   @(posedge clk);#1;
   if(scen==0 || scen==7)begin
    if(r_fault)$fatal(1,"reference fault in normal programme at cycle%0d",c);
    if(r_dv!==((c==36 || (scen==7 && c==22))?4'b0001:4'b0000))$fatal(1,"reference publication cycle%0d got%h",c,r_dv);
    if(scen==7 && c==22)begin
     if(r_dd[544:0]!=={1'b1,8'h56,8'h4d,16'h0700,vm_payload(7),vm_payload(0)})$fatal(1,"independent VM expected payload");
     vm_outputs=vm_outputs+1;
    end
    if(c==36)begin
     if(r_dd[544:512]!=={1'b1,8'hff,8'd7,16'd13})$fatal(1,"reduce metadata");
     for(integer l=0;l<16;l=l+1)if(r_dd[l*32+:32]!==32'h40400000+32'(l<<23))$fatal(1,"FP32 sum lane%0d",l);
     outputs=outputs+1;
    end
    if(r_done)halts=halts+1;
   end
  end
  rxv='0;rcv=0;repeat(8)@(negedge clk);
  if(mism!=0)$fatal(1,"lockstep: %0d cycles with a non-fault output difference (normal path/containment)",mism);
  if(scen==0 || scen==7)begin
   if(rf>=0 || nf>=0)$fatal(1,"normal programme fault ref%0d hard%0d",rf,nf);
   if(scen==7 && vm_outputs!=1)$fatal(1,"VM coverage outputs%0d",vm_outputs);
   if(outputs!=1 || halts!=1)$fatal(1,"coverage outputs%0d halts%0d",outputs,halts);
   if(n_cause!=0)$fatal(1,"fault_cause nonzero without fault");
  end else begin
   if(rf<0 || nf<0)$fatal(1,"scenario%0d fault missing: ref%0d hard%0d cause%h",scen,rf,nf,n_cause);
   if(nf-rf!=exp_delta+(scen==6?SHP:SH+1))$fatal(1,"scenario%0d fault edge: ref%0d hard%0d delta%0d expected%0d(+%0d issue shift)",scen,rf,nf,nf-rf,exp_delta,scen==6?SHP:SH+1);
   if(!first_cause[exp_bit])$fatal(1,"scenario%0d visibility: first cause %h lacks bit%0d",scen,first_cause,exp_bit);
  end
  $display("HCOLL_VM_COVERAGE outputs%0d bank0_to_low_bank7_to_high",vm_outputs);
  $display("HCOLL_Q_HARD_V5 PASS %s scen%0d checks%0d ref_fault%0d hard_fault%0d first_cause%h final_cause%h",
`ifdef Q3
   "q3",
`else
   "q2",
`endif
   scen,checks,rf,nf,first_cause,n_cause);
  $finish;
 end
endmodule
