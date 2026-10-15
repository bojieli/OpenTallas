`timescale 1ps/1fs
module phy_window_case #(parameter [63:0] BASE=0)(output reg complete=0);
reg clk=0;always #512 clk=~clk;reg rst_n=0;
reg [31:0] k_v=0,k_we=0;wire [31:0] k_rdy,k_wr_done,kr_v;
reg [959:0] k_addr=0;reg [127:0] k_len=0;reg [543:0] k_tag=0;
reg [8191:0] k_wdata=0;reg [1023:0] k_wstrb=0;wire [8191:0] kr_data;wire k_oor,w_oor;
ot_chip_v41x_hbm3e_phy #(.K_AW(30),.K_MEM(65536),.K_BASE(BASE),.KTAGW(17),.CLK_PS(1024)) phy(.clk(clk),.rst_n(rst_n),.k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),
.kr_v(kr_v),.kr_rdy(32'hffffffff),.kr_tag(),.kr_beat(),.kr_data(kr_data),.w_v(1'b0),.w_rdy(),.w_addr(24'd0),.w_len(6'd0),.w_tag(10'd0),.w_room(),.wr_v(),.wr_rdy(8'd0),.wr_tag(),.wr_beat(),.wr_data(),.k_oor(k_oor),.w_oor(w_oor),.refreshes(),.w_reads());
integer ack_count=0,reads=0,accept_count=0;reg [255:0] payload=256'h123456789abcdef00fedcba9876543210;
always @(posedge clk)if(rst_n)for(integer p=0;p<32;p=p+1)begin
if(k_v[p]&&k_rdy[p])accept_count=accept_count+1;
if(k_wr_done[p])ack_count=ack_count+1;
if(kr_v[p])begin if(kr_data[p*256+:256]!==payload)$fatal(1,"window read data");reads=reads+1;end
end
function automatic integer pc(input [29:0] s);pc=(s[6:2]^s[11:7]^s[16:12]);endfunction
task automatic send(input [29:0] addr,input bit write_en,input integer len,input bit valid_request);
integer p,guard;begin
p=pc(addr);k_addr=0;k_len=0;k_we=0;k_wdata=0;k_wstrb=0;k_v=0;
k_addr[p*30+:30]=addr;k_len[p*4+:4]=4'(len);k_we[p]=write_en;k_wdata[p*256+:256]=payload;k_wstrb[p*32+:32]=32'hffffffff;k_v[p]=1;
#1;
if(!valid_request)begin
if(k_rdy[p]!==0||phy.u_k.req_v[p]!==0)$fatal(1,"invalid window request reached model");
@(negedge clk);if(!k_oor)$fatal(1,"invalid request not sticky while ready0");
end else begin
guard=0;while(!k_rdy[p])begin @(negedge clk);guard=guard+1;if(guard>2000)$fatal(1,"valid request blocked");end
@(negedge clk);
end
k_v=0;
end endtask
initial begin
repeat(4)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
send(30'(BASE+3),1,1,1);while(ack_count<1)@(negedge clk);
send(30'(BASE+3),0,1,1);while(reads<1)@(negedge clk);
if(accept_count!=2||k_oor)$fatal(1,"valid default/high window changed");
// Below-window write (or zero-length base0), above-window write, and crossing read.
send(BASE==0?30'd0:30'(BASE-1),1,BASE==0?0:1,0);
send(30'(BASE+65536),1,1,0);
send(30'(BASE+65535),0,2,0);
repeat(100)@(negedge clk);
if(accept_count!=2||ack_count!=1||reads!=1||phy.u_k.mem[(BASE+3)%65536]!==payload||phy.u_k.mem[0]!==0||phy.u_k.mem[65535]!==0)$fatal(1,"invalid aperture aliased mutable HBM");
complete=1;$display("PHY_K_WINDOW_CASE PASS base=%h accepts2 trueACK1 readback1 rejected3 noalias1",BASE);
end
endmodule
module tb_phy_k_window;
wire a,b;
phy_window_case #(.BASE(0)) low(a);
phy_window_case #(.BASE(64'h28800000)) high(b);
initial begin wait(a&&b);$display("PHY_K_WINDOW PASS default and actualCOLB full30bit address+hash, below/above/crossing invalid blocked before model modulo");$finish;end
initial begin #100000000;$fatal(1,"window test timeout");end
endmodule
module tb_phy_k_window_overflow;
ot_chip_v41x_hbm3e_phy #(.K_AW(30),.K_MEM(65536),.K_BASE(64'h3fffffff)) invalid();
endmodule
