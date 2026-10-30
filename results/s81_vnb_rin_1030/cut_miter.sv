`timescale 1ns/1ps
module old_cut(input clk,rst_n,c_v,input [30:0] c_s,output c_v_o,output [30:0] c_s_o);
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr
        (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0];
    reg c_v_q; reg [30:0] c_s_q;
    always @(posedge clk or negedge rs_c) if (!rs_c) c_v_q <= 1'b0; else c_v_q <= c_v;
    always @(posedge clk) c_s_q <= c_s;
assign c_v_o=c_v_q; assign c_s_o=c_s_q;
endmodule
module new_child(input clk,rst_n,c_v_q,input [30:0] c_s_q, output chain_rs_c,c_v_o,output [30:0] c_s_o);
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr
        (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0];

assign chain_rs_c=rs_c; assign c_v_o=c_v_q; assign c_s_o=c_s_q;
endmodule
module new_composed(input clk,rst_n,c_v,input [30:0] c_s,output c_v_o,output [30:0] c_s_o);
wire chain_rs_c; reg c_v_q; reg [30:0] c_s_q;
`ifdef OT_VNB_RIN_MUT_RESET
wire reset_feed=rst_n;
`else
wire reset_feed=chain_rs_c;
`endif
always @(posedge clk or negedge reset_feed) if (!reset_feed) c_v_q<=1'b0; else c_v_q<=c_v;
always @(posedge clk) c_s_q<=c_s;
`ifdef OT_VNB_RIN_MUT_DATA
wire [30:0] child_data=c_s;
`else
wire [30:0] child_data=c_s_q;
`endif
new_child u_b(clk,rst_n,c_v_q,child_data,chain_rs_c,c_v_o,c_s_o);
endmodule
module tb;
reg clk=0; always #1 clk=~clk;
reg rst_n=1,c_v=0; reg [30:0] c_s=0;
wire ov,nv;wire [30:0] os,ns;
old_cut g(clk,rst_n,c_v,c_s,ov,os);
new_composed d(clk,rst_n,c_v,c_s,nv,ns);
integer cyc=0,checks=0,resets=0,xwords=0;
task check;
begin
checks=checks+1;
`ifdef OT_VNB_RIN_MUT_DATA
if (cyc > 12 && {ov,os} !== {nv,ns}) begin
`else
if ({ov,os} !== {nv,ns}) begin
`endif
$display("CUT DIFF cycle=%0d gold=%h gate=%h",cyc,{ov,os},{nv,ns});$fatal(1);
end
end endtask
always @(posedge clk) begin check;#0.01;check;end
always @(negedge rst_n) begin #0.01;check;end
initial begin
#0.2;rst_n=0;#0.4;rst_n=1;
for(cyc=0;cyc<6000;cyc=cyc+1) begin
@(negedge clk);c_v=$random;c_s={$random};
if(cyc%29==0) begin c_s[cyc%31]=1'bx;xwords=xwords+1;end
if(cyc%97==0) begin #0.2;rst_n=0;resets=resets+1;end
if(cyc%97==2) begin #0.2;rst_n=1;end
end
#1;$display("CUT PASS cycles=%0d checks=%0d resets=%0d xwords=%0d payload_cycles_added=0 valid_cycles_added=0",cyc,checks,resets,xwords);$finish;
end
endmodule
