`timescale 1ns/1ps
// H-NETLIST D4F 2026-10-16: the q2 host V4 native reduce bench at a parameterised link count NL (= the DUT NLINK).
// Slot indices follow the core: sink 'ring-partial' = ND-1 = NL+12, delivery 0 = NL, source 'reduce out' = NL+6.
// MUT 1..3 as the original bench; MUT 4: the programme writes link lane NL (absent at this NLINK) -> must fault;
// MUT 5: the NL=2 slot encoding run on this DUT (wrong slot map) -> must fail when NL != 2.
module tb_hgi_coll_q_static_host_v4_reduce_nl;
 parameter integer MUT=0;
 parameter integer NL=2;
 localparam integer EL=(MUT==5)?2:NL;   // slot encoding used by the programme
 // INJLAT (H-NETLIST/coll 2026-10-16): the DUT's SU inject latency; every compiled row from the inject
 // capture (row 12 at INJLAT 12) onwards shifts by D=INJLAT-12. MUT 3: the SU answers one edge early.
 parameter integer INJLAT=12;
 localparam integer D=INJLAT-12, NR=36+D, SUL=(MUT==3)?INJLAT-2:INJLAT-1;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cv=0,dv_cfg=0,launch=0;
 reg [11:0] cfg_addr=0;reg [255:0] cfg_data=0;
 wire configured,init_busy,program_fault;
 wire busy,done,fault;
 wire [1:0] inj_rd;wire [31:0] inj_idx;wire [159:0] inj_addr;
 wire [1023:0] inj_data;
 wire [3:0] dv;wire [2179:0] dd;wire [159:0] ob;
 wire [NL-1:0] txv,retry;wire [NL*612-1:0] txd;
 wire [279:0] cwo,ccwo;wire [135:0] rq;wire [2247:0] kq;
 wire rv;wire [2:0] rt;wire [255:0] rdata;wire [31:0] cycles;
 reg [1535:0] code[0:NR-1];reg [54:0] ar;
 reg [15:0] source_index[0:SUL-1];
 reg source_rd[0:SUL-1];  // the SU drives data only for an issued request (0 otherwise)
 integer outputs=0,done_count=0;
 // Declared external SU boundary: requests are observed at P+1 and data is
 // stable before P+12. It supplies input vectors, never an internal DUT result.
 always @(posedge clk)begin
  source_index[0]<=inj_idx[15:0];source_rd[0]<=inj_rd[0];
  for(integer p=1;p<SUL;p=p+1)begin source_index[p]<=source_index[p-1];source_rd[p]<=source_rd[p-1];end
 end
 function automatic [511:0] source_word(input [15:0] index);
  begin
   for(integer l=0;l<16;l=l+1)source_word[l*32+:32]=(index==0?32'h3f800000:32'h40000000)+32'(l<<23);
  end
 endfunction
 assign inj_data={512'd0,source_rd[SUL-1]?source_word(source_index[SUL-1]):512'd0};
 ot_hfd_coll_q2_static_host_v4 #(.NLINK(NL),.QID(2'd1),.INJLAT(INJLAT)) dut(.rst_n(rst_n),.clk_program(clk),.clk_control(clk),.clk_issue({4{clk}}),
  .clk_qslots({2{clk}}),.clk_ring({17{clk}}),.clk_reduce({33{clk}}),.clk_vmwrite(clk),.clk_link({(5*NL){clk}}),
   .cfg_v(cv),.cfg_target(8'd53),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(dv_cfg),.desc_base(12'd0),.desc_limit(13'(NR)),.desc_loops(16'd1),.launch_v(launch),
  .program_configured(configured),.program_init_busy(init_busy),.program_fault(program_fault),.hgi_busy(busy),.hgi_done(done),.hgi_fault(),
  .inj_rd(inj_rd),.inj_idx(inj_idx),.hgi_inj_addr(inj_addr),.inj_d(inj_data),
  .del_valid(dv),.del_flit(dd),.hgi_del_obase(ob),.rc_v(1'b0),.rc_tag(3'd0),.rc_d(256'd0),
  .rr_v(rv),.rr_tag(rt),.rr_d(rdata),.phy_up({NL{1'b1}}),.tx_pin_v(txv),.tx_pin_flit(txd),
  .rx_pin_v({NL{1'b0}}),.rx_pin_flit({(NL*612){1'b0}}),.retry_requested(retry),
  .pr_cw_i(280'd0),.pr_ccw_i(280'd0),.pr_cw_o(cwo),.pr_ccw_o(ccwo),
  .vm_rq(rq),.vm_rr(2056'd0),.vm_kq(kq),.fault(fault),.done(),.stat_cycles(cycles));
 task host_frame(input integer row,input integer segment,input [255:0] value);
  begin @(negedge clk);cv=1;cfg_addr=12'(row*8+segment);cfg_data=value;end
 endtask
 task pack_ar(input integer row,input [54:0] control);
  begin code[row][1505+:31]=control[30:0];code[row][688+:24]=control[54:31];end
 endtask
 initial begin
  for(integer n=0;n<NR;n=n+1)code[n]=0;
  code[0][90]=1;code[0][284+:33]={1'b1,8'hff,8'd0,16'd0};
  code[1][90]=1;code[1][92+:16]=16'd1;code[1][284+:33]={1'b1,8'hff,8'd1,16'd1};
  code[12+D][0]=1;code[13+D][0]=1;
  code[13+D][10+EL+12]=1;code[13+D][26+(EL+12)*4+:4]=0;
  code[14+D][10+EL+12]=1;code[14+D][26+(EL+12)*4+:4]=0;
  ar=0;ar[0]=1;ar[1+:4]=0;pack_ar(15+D,ar);
  ar=0;ar[5]=1;ar[6+:4]=0;pack_ar(16+D,ar);
  ar=0;ar[10]=1;pack_ar(MUT==2?18+D:17+D,ar);
  ar=0;ar[11]=1;ar[12+:4]=0;ar[21]=1;ar[23+:8]=8'd7;ar[31+:16]=16'd13;pack_ar(26+D,ar);
  ar=0;ar[22]=1;pack_ar(27+D,ar);
  code[28+D][EL+6]=1; // reduce producer capture slot follows the link count
  code[29+D][10+EL]=1;code[29+D][26+EL*4+:4]=(MUT==1?4'(EL+5):4'(EL+6));
  if(MUT==4)code[20+D][350+NL]=1;   // p_lk_wr_v[NL]: an absent link lane
  repeat(4)@(negedge clk);rst_n=1;
  for(integer row=0;row<NR;row=row+1)begin
   reg [63:0] metadata;
   metadata=64'(row+1);if(row==NR-1)metadata[44]=1;
   for(integer segment=0;segment<6;segment=segment+1)
    host_frame(row,segment,code[row][segment*256+:256]);
   host_frame(row,6,{192'b0,metadata});
   @(negedge clk);cv=0;
   // Fixed reservation: no polling init_busy and no dynamic ready.
   repeat(55)@(negedge clk);
   if(init_busy || program_fault)$fatal(1,"actualhost row drain did not finish on reserved edge");
  end
  @(negedge clk);dv_cfg=1;
  @(negedge clk);dv_cfg=0;repeat(66)@(negedge clk);
  if(!configured || program_fault)$fatal(1,"descriptor did not validate");
  @(negedge clk);launch=1;@(posedge clk);#1;
  for(integer c=1;c<47+D;c=c+1)begin
   @(negedge clk);launch=0;@(posedge clk);#1;
   if(fault)$fatal(1,"native host V4 parent fault at compiled cycle%0d",c);
   if(dv!==(c==36+D?4'b0001:4'b0000))$fatal(1,"native reduction publication cycle%0d got%h",c,dv);
   if(c==36+D)begin
    if(dd[544:512]!=={1'b1,8'hff,8'd7,16'd13})$fatal(1,"native reduce metadata");
    for(integer l=0;l<16;l=l+1)if(dd[l*32+:32]!==32'h40400000+32'(l<<23))$fatal(1,"native FP32 sum lane%0d",l);
    outputs=outputs+1;
   end
   if(done!==(c==40+D))$fatal(1,"native issuer halt cycle%0d",c);
   if(done)done_count=done_count+1;
  end
  if(outputs!=1||done_count!=1)$fatal(1,"coverage");
  $display("HCOLL_Q2_HOST_V4_NATIVE_REDUCE_NL%0d PASS INJLAT%0d lanes16 FP32 sum_at_hostlaunch36 halt40 links%0dx612_idle",NL,INJLAT,NL);
  $finish;
 end
endmodule
