`timescale 1ps/1fs
module tb_static_phase_core #(parameter integer MUT=0);
 reg ck=0,rst_n=0;
 always #416.5 ck=~ck;
 reg[2:0]go=0;
 reg[35:0]metadata=0;
 wire[2:0]outgo;
 wire[35:0]outmeta;
 wire fc,fh,ic,ih;
 qkd_static_kv_phase_launch #(.SAME_CLOCK(1),.META_HOLD_CORE(8),.MUT(MUT)) dut(
 .ck(ck),.hck(ck),.rst_n(rst_n),.hrst_n(rst_n),
 .ctrl_go(go[0]),.kgo(go[1]),.vgo(go[2]),
 .ctx_t(metadata[35:22]),.epoch(metadata[21:6]),.layer(metadata[5:0]),
 .ctrl_go_h(outgo[0]),.kgo_h(outgo[1]),.vgo_h(outgo[2]),
 .ctx_t_h(outmeta[35:22]),.epoch_h(outmeta[21:6]),.layer_h(outmeta[5:0]),
 .fault_core(fc),.fault_hbm(fh),.idle_core(ic),.idle_hbm(ih));
 reg[2:0]expected_go[0:4];
 reg[35:0]expected_meta[0:4];
 integer i,count=0,sent=0;
 always @(posedge ck) begin
  for(integer j=4;j>0;j=j-1)begin expected_go[j]=expected_go[j-1];expected_meta[j]=expected_meta[j-1];end
  expected_go[0]=rst_n ? go : 0;expected_meta[0]=metadata;
  #1;
  if(rst_n) begin
   if(outgo!==expected_go[4])$fatal(1,"core miter cycle mismatch got%h want%h",outgo,expected_go[4]);
   if(outgo!=0)begin
    if(outmeta!==expected_meta[4])$fatal(1,"core miter metadata mismatch got%h want%h",outmeta,expected_meta[4]);
    count=count+1;
   end
   if(fc||fh)$fatal(1,"valid same-clock packet faulted");
  end
 end
 initial begin
  for(i=0;i<5;i=i+1)begin expected_go[i]=0;expected_meta[i]=0;end
  repeat(10)@(negedge ck);rst_n=1;
  repeat(10)@(negedge ck);
  for(i=0;i<70;i=i+1) begin
   metadata={14'(1+i*103),16'(1000+i),6'(i%36)};
   go=3'(1+i%7);sent=sent+1;
   @(negedge ck);go=0;
   repeat(16)@(negedge ck);
  end
  repeat(12)@(negedge ck);
  if(count!=sent||!ic||!ih)$fatal(1,"native transport debt count%0d sent%0d",count,sent);
  $display("PASS same-clock lockstep70packets all7masks metadata four-cycle latency MUT=%0d",MUT);$finish;
 end
endmodule
