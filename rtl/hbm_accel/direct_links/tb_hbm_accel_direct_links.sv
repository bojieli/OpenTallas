`timescale 1ns/1ps
module tb_hbm_accel_direct_links;
 localparam integer N=96,FW=512,PW=551;
 reg clk=0; always #0.416666667 clk=~clk;
 reg rst_n=0;
 reg [N-1:0] start=0;
 wire [N-1:0] ready,fault,ov,last;
 wire [N*FW-1:0] output_data;
 wire [N*7-1:0] rank;
 wire [N*32-1:0] tag;
 wire [19:0] tv[0:N-1],tr[0:N-1],rv[0:N-1],rr[0:N-1];
 wire [20*PW-1:0] tx[0:N-1],rx[0:N-1];
 integer cycle=0,round=0,checks=0,mismatches=0;
 integer got[0:N-1],first[0:N-1],finish[0:N-1];
 reg stalled=0;
 always @(posedge clk) cycle<=cycle+1;
 function automatic integer peer(input integer r,p);
 integer group,lane,t;
 begin group=r/16; lane=r%16;
 if(p<15) peer=group*16+p+(p>=lane);
 else begin t=p-15; peer=(t+(t>=group))*16+lane; end
 end endfunction
 function automatic integer reverse_port(input integer r,p);
 integer dest;
 begin dest=peer(r,p);
 if(p<15) reverse_port=r%16-((r%16)>(dest%16));
 else reverse_port=15+r/16-((r/16)>(dest/16));
 end endfunction
 for(genvar r=0;r<N;r=r+1) begin:die
 wire consume=!stalled || ((cycle+r)%7!=0);
 ot_hbm_accel_gather_die #(.ENABLE(1),.RANK(r)) u_die(
 .clk(clk),.rst_n(rst_n),.in_valid(start[r]),.in_ready(ready[r]),
 .in_data({16{32'(r+round*256)}}),.in_tag(32'(round)),
 .tx_valid(tv[r]),.tx_ready(tr[r]),.tx_record(tx[r]),
 .rx_valid(rv[r]),.rx_ready(rr[r]),.rx_record(rx[r]),
 .out_valid(ov[r]),.out_ready(consume),.out_data(output_data[r*FW+:FW]),
 .out_rank(rank[r*7+:7]),.out_tag(tag[r*32+:32]),.out_last(last[r]),.fault(fault[r]));
 for(genvar p=0;p<20;p=p+1) begin:port
 localparam integer DEST=peer(r,p),DP=reverse_port(r,p);
 ot_hbm_accel_link_stage_model u_link(.clk(clk),.rst_n(rst_n),
 .in_valid(tv[r][p]),.in_ready(tr[r][p]),.in_data(tx[r][p*PW+:PW]),
 .out_valid(rv[DEST][DP]),.out_ready(rr[DEST][DP]),.out_data(rx[DEST][DP*PW+:PW]));
 end
 always @(negedge clk) if(rst_n && ov[r] && consume) begin
 if(got[r]==0) first[r]=cycle;
 checks=checks+1;
 if(rank[r*7+:7]!=got[r] || tag[r*32+:32]!=round ||
 output_data[r*FW+:FW]!={16{32'(got[r]+round*256)}} || last[r]!=(got[r]==95)) mismatches=mismatches+1;
 got[r]=got[r]+1; finish[r]=cycle;
 end
 end
 // default-off check at full shape
 wire offready,offv,offlast,offfault; wire [19:0] offrx,offtv;
 wire [20*PW-1:0] offtx; wire [FW-1:0] offdata; wire [6:0] offrank; wire [31:0] offtag;
 ot_hbm_accel_gather_die off(.clk(clk),.rst_n(rst_n),.in_valid(1'b1),.in_ready(offready),
 .in_data({FW{1'b1}}),.in_tag(32'hdeadbeef),.tx_valid(offtv),.tx_ready(20'hfffff),.tx_record(offtx),
 .rx_valid(20'hfffff),.rx_ready(offrx),.rx_record({20*PW{1'b1}}),.out_valid(offv),.out_ready(1'b1),
 .out_data(offdata),.out_rank(offrank),.out_tag(offtag),.out_last(offlast),.fault(offfault));
 integer issue,worst_first,worst_last;
 initial begin
 for(integer r=0;r<N;r=r+1) begin got[r]=0; first[r]=0; finish[r]=0; end
 repeat(4) @(negedge clk); rst_n=1;
 for(round=0;round<3;round=round+1) begin
 stalled=round==1;
 wait(&ready); @(negedge clk); issue=cycle; start='1;
 @(negedge clk); start=0;
 wait(&ready); @(negedge clk);
 worst_first=0; worst_last=0;
 for(integer r=0;r<N;r=r+1) begin
 if(got[r]!=96) mismatches=mismatches+1;
 if(first[r]-issue>worst_first) worst_first=first[r]-issue;
 if(finish[r]-issue>worst_last) worst_last=finish[r]-issue;
 got[r]=0;
 end
 $display("HA2_GATHER round=%0d first_cycles=%0d last_cycles=%0d",round,worst_first,worst_last);
 end
 if(|fault || offready || offv || offfault || |offtv || |offrx || |offtx) mismatches=mismatches+1;
 $display("HA2_TERMINAL checks=%0d mismatches=%0d",checks,mismatches);
 if(mismatches!=0) $fatal(1,"mismatch");
 $finish;
 end
endmodule
