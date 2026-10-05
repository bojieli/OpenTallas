module tb_dsrom_edge_kwr;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,go=0,rdy=0,installed=1;
reg [24:0] n=17;
reg [23:0] row=16;
reg [7:0] we=0;
reg [8*24-1:0] addr=0;
reg [8*32-1:0] data=0;
wire v,fault; wire [3:0] mask; wire [27:0] cs,ss;wire [2:0] slot;wire [511:0] codes;wire [31:0] scales;
ot_dsrom_edge_kwr dut(.clk(clk),.rst_n(rst_n),.cfg_ik_base(24'd0),.i_user_base_sec(28'd0),.layout_n(n),
.layout_installed(installed),.su_go(go),.i_dst(2'd3),.i_obase(24'd0),.i_orow(row),.i_nout(16'd1),.i_kdim(16'd128),
.kv_we(we),.kv_waddr(addr),.kv_wdata(data),.w_v(v),.w_rdy(rdy),.w_stack_mask(mask),.w_csec(cs),.w_ssec(ss),
.w_sslot(slot),.w_codes(codes),.w_scales(scales),.fault(fault),.dbg_keys());
integer b,i,faults=0;
always @(posedge clk) if(rst_n && fault) faults=faults+1;
task store(input reg bad_payload);
 begin
  n=17;row=16;installed=1;
  go=1;@(negedge clk);go=0;
  for(b=0;b<16;b=b+1) begin
   we=255;data=0;
   if(b==0 && bad_payload) data[16+:16]=16'h7f80;
   for(i=0;i<8;i=i+1) addr[24*i+:24]=2048+(b*8+i)*16;
   @(negedge clk);
  end
  we=0;data=0;
 end
endtask
initial begin
 repeat(3) @(negedge clk);rst_n=1;
 @(negedge clk);go=1;
 @(negedge clk);go=0;
 for(b=0;b<16;b=b+1) begin
  we=255;
  for(i=0;i<8;i=i+1)addr[24*i+:24]=2048+(b*8+i)*16;
  @(negedge clk);
 end
 we=0;
 wait(v);@(negedge clk);
 if(mask!==8 || cs!==128 || ss!==0 || slot!==0 || codes!==0 || scales!==0 || fault) $fatal(1,"wrong writer map/payload");
 n=50000;row=999;installed=0;
 repeat(5) begin @(negedge clk);if(!v || mask!==8 || cs!==128) $fatal(1,"held descriptor changed");end
 go=1;@(negedge clk);go=0;
 if(!fault || !v || mask!==8 || cs!==128) $fatal(1,"collision must refuse without changing held record");
 rdy=1;@(negedge clk);rdy=0;
 repeat(2) @(negedge clk);
 faults=0;
 store(1'b1);
 repeat(5) begin @(negedge clk);if(v) $fatal(1,"faulted encoding escaped");end
 if(faults==0) $fatal(1,"encoding fault not reported");
 store(1'b0);
 repeat(3) @(negedge clk);
 if(!v || fault || mask!==8 || cs!==128 || ss!==0 || codes!==0 || scales!==0) $fatal(1,"good record did not recover");
 $display("EDGE_WRITER held-map/payload/collision/encoding-fault/recovery PASS");$finish;
end
endmodule
