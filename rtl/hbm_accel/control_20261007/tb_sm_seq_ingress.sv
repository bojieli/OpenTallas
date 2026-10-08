module tb_sm_seq_ingress;
 parameter HOPS=8;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,seq_valid=0,operand_published=0,retired=0,start_ready=0;
 reg [319:0] seq_data=0;
 wire seq_ready,start,fault;wire[12:0]op_rows;wire[15:0]op_c;
 wire[7:0]op_g;wire op_gs;wire[1:0]op_fmt;wire[6:0]op_xb;
 ot_hbm_sm_seq_ingress #(.ENABLE(1),.HOPS(HOPS)) dut(.*);
 integer i,n=0,cycles=0;
 always @(posedge clk) begin
  cycles<=cycles+1;
  if(cycles>128*(2*HOPS+30)+100)$fatal(1,"timeout");
  if(start && start_ready)begin
   if({op_rows,op_c,op_g,op_gs,op_fmt,op_xb}!=={13'd17,16'd8,8'd3,1'b1,2'd2,7'(n*13)})
    $fatal(1,"descriptor or ring base mismatch n=%d xb=%d",n,op_xb);
   n<=n+1;
  end
 end
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  for(i=0;i<128;i=i+1)begin
   seq_data=0;seq_data[31:0]=17;seq_data[63:32]=8;seq_data[95:64]=3;
   seq_data[127:96]=2;seq_data[191:160]=1;seq_data[223:192]=1;
   seq_data[255:224]=24;seq_data[319:288]=(i*13)%128;
   seq_valid=1;operand_published=0; #1;
   if(seq_ready)$fatal(1,"unpublished operand admitted");
   repeat(3)begin @(negedge clk);if(seq_ready || start)$fatal(1,"unpublished operand issued");end
   operand_published=1; #1;
   while(!seq_ready)@(negedge clk);
   @(negedge clk);seq_valid=0;operand_published=0;
   while(!start)@(negedge clk);
   repeat(4)@(negedge clk);
   start_ready=1;@(negedge clk);start_ready=0;
   repeat(3)@(negedge clk);retired=1;@(negedge clk);retired=0;
   if(fault)$fatal(1,"fault");
  end
  if(n!=128)$fatal(1,"missing command");
  $display("PASS commands=%0d hops=%0d cycles=%0d",n,HOPS,cycles);$finish;
 end
endmodule
