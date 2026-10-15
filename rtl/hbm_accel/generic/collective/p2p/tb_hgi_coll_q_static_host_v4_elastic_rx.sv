`timescale 1ns/1ps
module tb_hgi_coll_q_static_host_v4_elastic_rx;
 parameter integer MUT=0,PINGPONG=0;
 reg arm=0,pv=0;wire [1:0] br,pr;wire [3:0] br2;wire bf;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cv=0,dv_cfg=0,launch=0;
 reg [11:0] cfg_addr=0;reg [255:0] cfg_data=0;
 wire configured,init_busy,program_fault;
 wire busy,done,fault;
 wire [1:0] inj_rd;wire [31:0] inj_idx;wire [159:0] inj_addr;
 wire [1023:0] inj_data;
 wire [3:0] dv;wire [2179:0] dd;wire [159:0] ob;
 wire [1:0] txv,retry;wire [1223:0] txd;
 wire [279:0] cwo,ccwo;wire [135:0] rq;wire [2247:0] kq;
 wire rv;wire [2:0] rt;wire [255:0] rdata;wire [31:0] cycles;
 reg [1535:0] code[0:37];reg [54:0] ar;
 reg [15:0] source_index[0:10];
 integer outputs=0,done_count=0;
 // Declared external SU boundary: requests are observed at P+1 and data is
 // stable before P+12. It supplies input vectors, never an internal DUT result.
 always @(posedge clk)begin
  source_index[0]<=inj_idx[15:0];
  for(integer p=1;p<11;p=p+1)source_index[p]<=source_index[p-1];
 end
 function automatic [511:0] source_word(input [15:0] index);
  begin
   for(integer l=0;l<16;l=l+1)source_word[l*32+:32]=(index==0?32'h3f800000:32'h40000000)+32'(l<<23);
  end
 endfunction
 assign inj_data={512'd0,source_word(source_index[10])};
 generate if(PINGPONG==0)begin:g_single
 ot_hfd_coll_q2_static_host_v4_elastic_rx #(.QID(2'd1)) dut(.clk_rx_boundary({2{clk}}),.rx_arm_v({1'b0,arm}),.rx_block_words({7'd1,7'd1}),
  .rx_required(2'b01),.rx_pin_ready(pr),.rx_block_ready(br),.rx_release_v(2'b0),
  .rx_slot_v(2'b0),.rx_slot_index(12'd0),.rx_boundary_fault(bf),.rst_n(rst_n),.clk_program(clk),.clk_control(clk),.clk_issue({4{clk}}),
  .clk_qslots({2{clk}}),.clk_ring({17{clk}}),.clk_reduce({33{clk}}),.clk_vmwrite(clk),.clk_link({10{clk}}),
   .cfg_v(cv),.cfg_target(8'd53),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(dv_cfg),.desc_base(12'd0),.desc_limit(13'd1),.desc_loops(16'd1),.launch_v(launch),
  .program_configured(configured),.program_init_busy(init_busy),.program_fault(program_fault),.hgi_busy(busy),.hgi_done(done),.hgi_fault(),
  .inj_rd(inj_rd),.inj_idx(inj_idx),.hgi_inj_addr(inj_addr),.inj_d(inj_data),
  .del_valid(dv),.del_flit(dd),.hgi_del_obase(ob),.rc_v(1'b0),.rc_tag(3'd0),.rc_d(256'd0),
  .rr_v(rv),.rr_tag(rt),.rr_d(rdata),.phy_up(2'b11),.tx_pin_v(txv),.tx_pin_flit(txd),
  .rx_pin_v({1'b0,pv}),.rx_pin_flit(1224'd0),.retry_requested(retry),
  .pr_cw_i(280'd0),.pr_ccw_i(280'd0),.pr_cw_o(cwo),.pr_ccw_o(ccwo),
  .vm_rq(rq),.vm_rr(2056'd0),.vm_kq(kq),.fault(fault),.done(),.stat_cycles(cycles));
 end else begin:g_double
 ot_hfd_coll_q2_static_host_v4_elastic_rx_pingpong #(.QID(2'd1)) dut(.clk_rx_boundary({2{clk}}),.rx_arm_v({1'b0,arm}),.rx_arm_bank(2'b01),.rx_release_bank(2'b0),.rx_slot_bank(2'b0),.rx_required_bank(2'b01),.rx_block_words({7'd1,7'd1}),
  .rx_required(2'b01),.rx_pin_ready(pr),.rx_block_ready(br2),.rx_release_v(2'b0),
  .rx_slot_v(2'b0),.rx_slot_index(12'd0),.rx_boundary_fault(bf),.rst_n(rst_n),.clk_program(clk),.clk_control(clk),.clk_issue({4{clk}}),
  .clk_qslots({2{clk}}),.clk_ring({17{clk}}),.clk_reduce({33{clk}}),.clk_vmwrite(clk),.clk_link({10{clk}}),
   .cfg_v(cv),.cfg_target(8'd53),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(dv_cfg),.desc_base(12'd0),.desc_limit(13'd1),.desc_loops(16'd1),.launch_v(launch),
  .program_configured(configured),.program_init_busy(init_busy),.program_fault(program_fault),.hgi_busy(busy),.hgi_done(done),.hgi_fault(),
  .inj_rd(inj_rd),.inj_idx(inj_idx),.hgi_inj_addr(inj_addr),.inj_d(inj_data),
  .del_valid(dv),.del_flit(dd),.hgi_del_obase(ob),.rc_v(1'b0),.rc_tag(3'd0),.rc_d(256'd0),
  .rr_v(rv),.rr_tag(rt),.rr_d(rdata),.phy_up(2'b11),.tx_pin_v(txv),.tx_pin_flit(txd),
  .rx_pin_v({1'b0,pv}),.rx_pin_flit(1224'd0),.retry_requested(retry),
  .pr_cw_i(280'd0),.pr_ccw_i(280'd0),.pr_cw_o(cwo),.pr_ccw_o(ccwo),
  .vm_rq(rq),.vm_rr(2056'd0),.vm_kq(kq),.fault(fault),.done(),.stat_cycles(cycles));
 end endgenerate
 task frame(input integer segment,input [255:0] value);
  begin @(negedge clk);cv=1;cfg_addr=12'(segment);cfg_data=value;end
 endtask
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  for(integer segment=0;segment<6;segment=segment+1)frame(segment,256'd0);
  frame(6,256'(64'd1<<44));
  @(negedge clk);cv=0;repeat(55)@(negedge clk);
  @(negedge clk);dv_cfg=1;
  @(negedge clk);dv_cfg=0;repeat(66)@(negedge clk);
  if(!configured||program_fault)$fatal(1,"native HOST halt descriptor");
  if(MUT==0)begin
   @(negedge clk);arm=1;
   @(negedge clk);arm=0;pv=1;
   @(negedge clk);pv=0;
   repeat(3)@(negedge clk);
   if((PINGPONG==0 && br!==2'b01)||(PINGPONG!=0 && br2!==4'b0010)||bf)$fatal(1,"native wrapper block admission");
  end
  @(negedge clk);launch=1;@(posedge clk);#1;
  for(integer c=1;c<12;c=c+1)begin
   @(negedge clk);launch=0;@(posedge clk);#1;
   if(MUT==0)begin
    if(fault||program_fault||bf)$fatal(1,"admitted native halt parent fault");
    if(done!==(c==5))$fatal(1,"native halt edge%0d done%b",c,done);
    if(done)done_count=done_count+1;
   end else if(!bf||!fault||busy||done||program_fault)$fatal(1,"missing block launched native host");
  end
  if(MUT==0 && done_count!=1)$fatal(1,"missing native halt");
  $display("HCOLL_OFFDIE_RX_HOST_ADMISSION_PASS PINGPONG%0d MUT%0d real_HOST_target53_programSRAM3_halt5",PINGPONG,MUT);
  $finish;
 end
endmodule
