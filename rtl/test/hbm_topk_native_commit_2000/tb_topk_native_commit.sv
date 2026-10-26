`timescale 1ns/1ps
`default_nettype none
// Selected source rootctl (VM_RT65/CR_RT36/FAN32) emits actual TOPK CQ.
// Eight current native faces banks, 24 real SRAMs, and actual SW shared glue.
// The 64-edge RR transport is source-budget stimulus only. No routed input
// producer age is qualified. Output ages are anchored at the real CQ pin.
module tb_topk_native_commit;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,go=0;integer cycle=0,go_edge=0,active_case=0,case_id=0,mut=0;
 integer errors=0,checks=0,cq_edge=-1,commit_edge=-1,pq_edge=-1,first_new=-1;
 integer nprobe=0,nreturn=0,req_edges[0:63];
 reg[31:0] scores[0:1151],expected[0:17];reg[17:0]bases[0:2];
 reg[17:0]outbase=0;reg[255:0]want=0,oldword=0;
 reg[2247:0]dq=0;reg[135:0]probe=0;
 reg[7:0]rslot_v=0,wslot_v=0;reg[23:0]rslot=0,wslot=0;
 wire[135:0]vm_rq;wire[2055:0]rr4,rr0;reg[2055:0]rr_delay[0:63];
 always @(posedge clk)begin
  if(!rst_n)for(integer i=0;i<64;i=i+1)rr_delay[i]<=0;
  else begin rr_delay[0]<=rr4;for(integer i=1;i<64;i=i+1)rr_delay[i]<=rr_delay[i-1];end
 end
 wire[337:0]cq;wire[1:0]cqs;wire busy,done,fault,share_fault;
 wire[675:0]cq_all={cq,338'd0};wire[547:0]cr;
 reg[7:0]bank_enable=0;reg[15:0]bank_client=0;reg[2:0]response_enable=0;
 wire[5:0]client_seq={2'd0,cqs,2'd0};reg[5:0]response_seq=0;
 wire[2:0]hub_status,ring_fault;wire[1:0]mirror_busy;wire[18:0]vmstat;
 wire[143:0]status;wire[2223:0]cw_out,ccw_out;
 wire[2207:0]xq,xq2,eg;wire[7:0]xd,xd2;wire[2279:0]pq;wire[2127:0]pr;
 ot_hbm_idx_rootctl_static_am #(.VM_RT(65),.CR_RT(36),.SEL_LAT(30),.RSTL(1),.FAN32(1)) topk(
  .clk(clk),.rst_n(rst_n),.program_we(1'b0),.program_addr(8'd0),.program_data(256'd0),.start(1'b0),.length(12'd0),
  .sel_op(),.sel_pass(),.sel_addr(),.link_flush(),.link_emit(),.link_group(),.link_clear(),.selected_v(4'd0),
  .ingest_v(),.tree_ev(4'd0),.qfault(4'd0),.sf(1'b0),.lf(1'b0),.done(),.fault(),
  .topk_go(go),.topk_k(4'd6),.topk_order(1'b1),.topk_n(20'd384),.topk_m(20'd1),
  .topk_a_mirror(1'b0),.topk_a_base(18'd0),.topk_a_str(18'd384),.topk_o_mirror(1'b0),
  .topk_o_base(outbase),.topk_o_str(18'd6),.topk_has_r(1'b0),.topk_r_base(18'd0),.topk_r_str(18'd0),
  .cq(cq),.cq_seq(cqs),.cr(cr[274+:274]),.topk_busy(busy),.topk_done(done),.topk_fault(fault),
  .index_rq(136'd0),.index_rr(),.argmax_rq(136'd0),.argmax_m(),.vm_rq(vm_rq),.vm_rr(rr_delay[63]),.share_fault(share_fault));
 hfd_hgi_vms_glue_sw_t hub(.clk(clk),.rst_n(rst_n),.cq(cq_all),.cr(cr),.client_seq(client_seq),
  .response_enable(response_enable),.response_seq(response_seq),.bank_enable(bank_enable),.bank_client(bank_client),
  .hub_ring_enable(2'd0),.hub_ring_client(4'd0),.cw_in(2224'd0),.ccw_in(2224'd0),.cw_out(cw_out),.ccw_out(ccw_out),
  .ring_tx_enable(2'd0),.ring_tx_source(6'd0),.replay_enable(1'b0),.replay_source(1'b0),
  .b0_xq(xq[0+:276]),.b0_xq2(xq2[0+:276]),.b0_xq_done(xd[0]),.b0_xq2_done(xd2[0]),.b0_eg(eg[0+:276]),
  .b0_pq(pq[0+:285]),.b0_pr(pr[0+:266]),.b0_status(status[0+:18]),
  .b1_xq(xq[276+:276]),.b1_xq2(xq2[276+:276]),.b1_xq_done(xd[1]),.b1_xq2_done(xd2[1]),.b1_eg(eg[276+:276]),
  .b1_pq(pq[285+:285]),.b1_pr(pr[266+:266]),.b1_status(status[18+:18]),
  .b2_xq(xq[552+:276]),.b2_xq2(xq2[552+:276]),.b2_xq_done(xd[2]),.b2_xq2_done(xd2[2]),.b2_eg(eg[552+:276]),
  .b2_pq(pq[570+:285]),.b2_pr(pr[532+:266]),.b2_status(status[36+:18]),
  .b3_xq(xq[828+:276]),.b3_xq2(xq2[828+:276]),.b3_xq_done(xd[3]),.b3_xq2_done(xd2[3]),.b3_eg(eg[828+:276]),
  .b3_pq(pq[855+:285]),.b3_pr(pr[798+:266]),.b3_status(status[54+:18]),
  .b4_xq(xq[1104+:276]),.b4_xq2(xq2[1104+:276]),.b4_xq_done(xd[4]),.b4_xq2_done(xd2[4]),.b4_eg(eg[1104+:276]),
  .b4_pq(pq[1140+:285]),.b4_pr(pr[1064+:266]),.b4_status(status[72+:18]),
  .b5_xq(xq[1380+:276]),.b5_xq2(xq2[1380+:276]),.b5_xq_done(xd[5]),.b5_xq2_done(xd2[5]),.b5_eg(eg[1380+:276]),
  .b5_pq(pq[1425+:285]),.b5_pr(pr[1330+:266]),.b5_status(status[90+:18]),
  .b6_xq(xq[1656+:276]),.b6_xq2(xq2[1656+:276]),.b6_xq_done(xd[6]),.b6_xq2_done(xd2[6]),.b6_eg(eg[1656+:276]),
  .b6_pq(pq[1710+:285]),.b6_pr(pr[1596+:266]),.b6_status(status[108+:18]),
  .b7_xq(xq[1932+:276]),.b7_xq2(xq2[1932+:276]),.b7_xq_done(xd[7]),.b7_xq2_done(xd2[7]),.b7_eg(eg[1932+:276]),
  .b7_pq(pq[1995+:285]),.b7_pr(pr[1862+:266]),.b7_status(status[126+:18]),
  .hub_status(hub_status),.mirror_busy(mirror_busy),.vmstat(vmstat),.ring_fault(ring_fault));
 for(genvar b=0;b<8;b=b+1)begin:bank
  hfd_vms_bank_native_q0_faces memory(.clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),
   .clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),
   .rq0(probe[b*17+:17]),.rr0(rr0[b*257+:257]),.rq1(17'd0),.rr1(),.rq2(17'd0),.rr2(),.rq3(17'd0),.rr3(),
   .rq4(vm_rq[b*17+:17]),.rr4(rr4[b*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),
   .rslot_v(rslot_v[b]),.rslot(rslot[b*3+:3]),.wslot_v(wslot_v[b]),.wslot(wslot[b*3+:3]),
   .dq(dq[b*281+:281]),.dq_done(),.kq(281'd0),.kq_done(),.xq(xq[b*276+:276]),.xq_done(xd[b]),
   .xq2(xq2[b*276+:276]),.xq2_done(xd2[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]));
  always @(posedge clk)if(active_case && b==0 && memory.u_ot_pr_core.bank.m_wA && memory.u_ot_pr_core.bank.m_wa==outbase[15:6])begin
   commit_edge=cycle;
   $display("NATIVE_COMMIT case=%0d cycle=%0d cq_delta=%0d row=%0d mask=%h",case_id,cycle,cycle-cq_edge,memory.u_ot_pr_core.bank.m_wa,memory.u_ot_pr_core.bank.m_mA);
   if(cycle-cq_edge!=6 || memory.u_ot_pr_core.bank.m_mA!=8'h3f)errors=errors+1;
  end
 end
 always @(posedge clk)begin:observe
  integer stamp;reg[255:0]seen;stamp=cycle;cycle<=cycle+1;
  if(active_case)begin
   if(cq[337])begin
    cq_edge=stamp;
    $display("TOPK_CQ case=%0d cycle=%0d go_delta=%0d tag=%h seq=%h address=%h mask=%h",case_id,stamp,stamp-go_edge,cq[15:0],cqs,cq[335:304],cq[47:16]);
    if(stamp-go_edge!=207 || cq[48+:192]!=want[0+:192] || cq[47:16]!=32'h00ffffff)errors=errors+1;
   end
   if(pq[284])begin pq_edge=stamp;$display("NATIVE_PQ case=%0d cycle=%0d cq_delta=%0d tag=%h",case_id,stamp,stamp-cq_edge,pq[7:0]);end
   if(probe[16])begin req_edges[nprobe]=stamp;nprobe=nprobe+1;end
   if(fault||share_fault||hub_status||ring_fault||status)begin
    if(errors<8)$display("STATUS case=%0d rel=%0d core=%b share=%b hub=%h bank=%h",case_id,stamp-go_edge,fault,share_fault,hub_status,status);
    errors=errors+1;
   end
   #1;
   if(rr0[256])begin
    seen=rr0[255:0];checks=checks+1;
    if(seen===want && first_new<0)first_new=req_edges[nreturn];
    if(seen!==(req_edges[nreturn]>=cq_edge+(mut==3?2:3)?want:oldword))begin
     errors=errors+1;
     if(errors<12)$display("READ_MISMATCH case=%0d request=%0d cq_delta=%0d response=%0d value=%h want=%h old=%h",case_id,req_edges[nreturn],req_edges[nreturn]-cq_edge,stamp,seen,want,oldword);
    end
    if(stamp-req_edges[nreturn]!=7)errors=errors+1;
    nreturn=nreturn+1;
   end
  end
 end
 task automatic preload(input integer sector,input[255:0]data);
  integer b;begin b=sector%8;@(negedge clk);dq=0;dq[b*281+:281]={1'b1,16'(sector),data,8'hff};
   @(negedge clk);dq=0;repeat(5)@(negedge clk);end
 endtask
 integer c,j,w,rel;reg[255:0]payload;string dir;
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"missing fixture DIR");
  if(!$value$plusargs("MUT=%d",mut))mut=0;
  $readmemh({dir,"/scores.mem"},scores);$readmemh({dir,"/expected.mem"},expected);$readmemh({dir,"/bases.mem"},bases);
  for(c=0;c<3;c=c+1)begin
   active_case=0;rst_n=0;go=0;probe=0;dq=0;bank_enable=0;response_enable=0;rslot_v=0;wslot_v=0;
   repeat(8)@(negedge clk);rst_n=1;repeat(24)@(negedge clk);
   outbase=bases[c];case_id=c;wslot_v=255;wslot={8{3'd6}};
   for(j=0;j<48;j=j+1)begin
    for(w=0;w<8;w=w+1)payload[w*32+:32]=scores[c*384+j*8+w];preload(j,payload);
   end
   for(w=0;w<8;w=w+1)oldword[w*32+:32]=32'hdeadbeef ^ 32'(c*256+w);
   preload(int'(outbase>>3),oldword);repeat(12)@(negedge clk);
   want=oldword;for(w=0;w<6;w=w+1)want[w*32+:32]=expected[c*6+w];
   nprobe=0;nreturn=0;first_new=-1;cq_edge=-1;commit_edge=-1;pq_edge=-1;
   rslot_v=255;rslot={8{3'd4}};wslot={8{3'(mut==1?0:4)}};
   @(negedge clk);go=1;go_edge=cycle;active_case=1;
   for(rel=1;rel<=320;rel=rel+1)begin
    @(negedge clk);go=0;probe=0;bank_enable=0;bank_client=0;response_enable=0;
    if(rel>=180)rslot=0;
    if(rel==207)begin bank_enable=1;bank_client[0+:2]=2'(mut==2?0:1);end
    if(rel==252)response_enable=3'b010;
    if((rel>=207&&rel<=220)||rel==247)probe[0+:17]={1'b1,16'(outbase>>3)};
   end
   active_case=0;
   if(cq_edge<0||commit_edge<0||nprobe!=15||nreturn!=15||first_new-cq_edge!=3)errors=errors+1;
   $display("CASE_END case=%0d cq=%0d pq=%0d commit=%0d first_readable_request=%0d probes=%0d responses=%0d",c,cq_edge,pq_edge,commit_edge,first_new,nprobe,nreturn);
  end
  if(errors)$fatal(1,"TOPK_NATIVE_COMMIT FAIL errors=%0d checks=%0d mut=%0d",errors,checks,mut);
  $display("TOPK_NATIVE_COMMIT PASS cases=3 checks=%0d cq_to_macro_commit=6 first_readable_pin=3 native_read_return=7 finite_retention_request=40 mut=%0d",checks,mut);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
`default_nettype wire
