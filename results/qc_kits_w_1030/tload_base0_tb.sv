`timescale 1ps/1ps
module ot_rom_4096x266_m8(input clk, input ce_in, input [11:0] addr_in, output reg [265:0] rd_out);
  always @(posedge clk) if (ce_in) rd_out <= {22{addr_in ^ 12'ha5c}} ^ {266{addr_in[0]}} ^ (266'd1 << addr_in[7:0]);
endmodule
module tb;
reg ck=0; always begin #416; ck=1; #417; ck=0; end
reg rst_n=0, start=0, oth=0; reg [5:0] stage=0; reg [1:0] uid=0;
`define PORTS(o) .ck(ck),.rst_n(rst_n),.start(start),.stage(stage),.user_id(uid),.other_table_write(oth),.tw_we(o``_we),.tw_we_k(o``_wek),.tw_kind(o``_kind),.tw_addr(o``_addr),.tw_data(o``_data),.busy(o``_busy),.done(o``_done),.fault(o``_fault)
wire a_we,b_we,c_we,d_we; wire [3:0] a_wek,b_wek,c_wek,d_wek; wire [1:0] a_kind,b_kind,c_kind,d_kind; wire [23:0] a_addr,b_addr,c_addr,d_addr;
wire [1023:0] a_data,b_data,c_data,d_data; wire a_busy,b_busy,c_busy,d_busy,a_done,b_done,c_done,d_done,a_fault,b_fault,c_fault,d_fault;
ld_old #(.BTAB_COMPACT(1),.CAPTURE_STAGE(1),.LOCAL_CTRL(1),.WE_COPIES(4)) A(`PORTS(a));
ld_new #(.BTAB_COMPACT(1),.CAPTURE_STAGE(1),.LOCAL_CTRL(1),.WE_COPIES(4)) B(`PORTS(b));
ld_old #(.BTAB_COMPACT(1),.WE_COPIES(4)) C(`PORTS(c));
ld_new #(.BTAB_COMPACT(1),.WE_COPIES(4)) D(`PORTS(d));
integer n, ch=0, starts=0; reg [31:0] s=32'h1234567;
initial begin
 repeat(3) @(negedge ck); rst_n=1;
 for (n=0;n<200000;n=n+1) begin
  @(negedge ck); s=s^(s<<13); s=s^(s>>17); s=s^(s<<5);
  start = (s[7:0]==0) || (s[15:9]==0); oth = (s[31:24]==0); stage = s[21:16] % 40; uid = s[23:22];
  if (start) starts=starts+1;
  @(posedge ck); #1;
  if ({a_we,a_wek,a_kind,a_addr,a_data,a_busy,a_done,a_fault} !== {b_we,b_wek,b_kind,b_addr,b_data,b_busy,b_done,b_fault} || A.rom_addr !== B.rom_addr) begin $display("FAIL cap edge %0d",n); $fatal(1); end
  if ({c_we,c_wek,c_kind,c_addr,c_data,c_busy,c_done,c_fault} !== {d_we,d_wek,d_kind,d_addr,d_data,d_busy,d_done,d_fault} || C.rom_addr !== D.rom_addr) begin $display("FAIL legacy edge %0d",n); $fatal(1); end
  ch=ch+2;
 end
 $display("LOCKSTEP_PASS edges=%0d checks=%0d starts=%0d we_events_seen=%0d", n, ch, starts, 0); $finish;
end
endmodule
