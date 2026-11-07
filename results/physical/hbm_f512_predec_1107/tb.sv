`timescale 1ns/1ps
module tb; parameter MUT=0; reg clk=0; always #5 clk=~clk; reg rst_n=0; integer cyc=0,bad=0,reads=0,writes=0,faults=0;
reg [2:0] i_bid=0;
reg [280:0] i_dq=0;
reg [280:0] i_kq=0;
reg [284:0] i_pq=0;
reg [16:0] i_rq0=0;
reg [16:0] i_rq1=0;
reg [16:0] i_rq2=0;
reg [16:0] i_rq3=0;
reg [16:0] i_rq4=0;
reg [2:0] i_rslot=0;
reg [0:0] i_rslot_v=0;
reg [1:0] i_sid=0;
reg [280:0] i_wq0=0;
reg [280:0] i_wq1=0;
reg [2:0] i_wslot=0;
reg [0:0] i_wslot_v=0;
reg [275:0] i_xq=0;
reg [275:0] i_xq2=0;
wire[0:0] a_dq_done,b_dq_done; reg[0:0] prev_dq_done; always @(posedge clk)prev_dq_done<=a_dq_done;
wire[275:0] a_eg,b_eg; reg[275:0] prev_eg; always @(posedge clk)prev_eg<=a_eg;
wire[0:0] a_kq_done,b_kq_done; reg[0:0] prev_kq_done; always @(posedge clk)prev_kq_done<=a_kq_done;
wire[265:0] a_pr,b_pr; reg[265:0] prev_pr; always @(posedge clk)prev_pr<=a_pr;
wire[256:0] a_rr0,b_rr0; reg[256:0] prev_rr0; always @(posedge clk)prev_rr0<=a_rr0;
wire[256:0] a_rr1,b_rr1; reg[256:0] prev_rr1; always @(posedge clk)prev_rr1<=a_rr1;
wire[256:0] a_rr2,b_rr2; reg[256:0] prev_rr2; always @(posedge clk)prev_rr2<=a_rr2;
wire[256:0] a_rr3,b_rr3; reg[256:0] prev_rr3; always @(posedge clk)prev_rr3<=a_rr3;
wire[256:0] a_rr4,b_rr4; reg[256:0] prev_rr4; always @(posedge clk)prev_rr4<=a_rr4;
wire[17:0] a_status,b_status; reg[17:0] prev_status; always @(posedge clk)prev_status<=a_status;
wire[0:0] a_wq_done0,b_wq_done0; reg[0:0] prev_wq_done0; always @(posedge clk)prev_wq_done0<=a_wq_done0;
wire[0:0] a_wq_done1,b_wq_done1; reg[0:0] prev_wq_done1; always @(posedge clk)prev_wq_done1<=a_wq_done1;
wire[0:0] a_xq2_done,b_xq2_done; reg[0:0] prev_xq2_done; always @(posedge clk)prev_xq2_done<=a_xq2_done;
wire[0:0] a_xq_done,b_xq_done; reg[0:0] prev_xq_done; always @(posedge clk)prev_xq_done<=a_xq_done;
G_hnx_vms_bank_q0_faces__vecd4ae gold(.bid(i_bid),.clk(clk),.clk_e(clk),.clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.clk_n(clk),.clk_s(clk),.clk_w(clk),.dq(i_dq),.dq_done(a_dq_done),.eg(a_eg),.kq(i_kq),.kq_done(a_kq_done),.pq(i_pq),.pr(a_pr),.rq0(i_rq0),.rq1(i_rq1),.rq2(i_rq2),.rq3(i_rq3),.rq4(i_rq4),.rr0(a_rr0),.rr1(a_rr1),.rr2(a_rr2),.rr3(a_rr3),.rr4(a_rr4),.rslot(i_rslot),.rslot_v(i_rslot_v),.rst_n(rst_n),.sid(i_sid),.status(a_status),.wq0(i_wq0),.wq1(i_wq1),.wq_done0(a_wq_done0),.wq_done1(a_wq_done1),.wslot(i_wslot),.wslot_v(i_wslot_v),.xq(i_xq),.xq2(i_xq2),.xq2_done(a_xq2_done),.xq_done(a_xq_done));
generate if(MUT==0)begin N_hnx_vms_bank_q0_faces__vecd4ae dut(.bid(i_bid),.clk(clk),.clk_e(clk),.clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.clk_n(clk),.clk_s(clk),.clk_w(clk),.dq(i_dq),.dq_done(b_dq_done),.eg(b_eg),.kq(i_kq),.kq_done(b_kq_done),.pq(i_pq),.pr(b_pr),.rq0(i_rq0),.rq1(i_rq1),.rq2(i_rq2),.rq3(i_rq3),.rq4(i_rq4),.rr0(b_rr0),.rr1(b_rr1),.rr2(b_rr2),.rr3(b_rr3),.rr4(b_rr4),.rslot(i_rslot),.rslot_v(i_rslot_v),.rst_n(rst_n),.sid(i_sid),.status(b_status),.wq0(i_wq0),.wq1(i_wq1),.wq_done0(b_wq_done0),.wq_done1(b_wq_done1),.wslot(i_wslot),.wslot_v(i_wslot_v),.xq(i_xq),.xq2(i_xq2),.xq2_done(b_xq2_done),.xq_done(b_xq_done));end else begin M_hnx_vms_bank_q0_faces__vecd4ae dut(.bid(i_bid),.clk(clk),.clk_e(clk),.clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.clk_n(clk),.clk_s(clk),.clk_w(clk),.dq(i_dq),.dq_done(b_dq_done),.eg(b_eg),.kq(i_kq),.kq_done(b_kq_done),.pq(i_pq),.pr(b_pr),.rq0(i_rq0),.rq1(i_rq1),.rq2(i_rq2),.rq3(i_rq3),.rq4(i_rq4),.rr0(b_rr0),.rr1(b_rr1),.rr2(b_rr2),.rr3(b_rr3),.rr4(b_rr4),.rslot(i_rslot),.rslot_v(i_rslot_v),.rst_n(rst_n),.sid(i_sid),.status(b_status),.wq0(i_wq0),.wq1(i_wq1),.wq_done0(b_wq_done0),.wq_done1(b_wq_done1),.wslot(i_wslot),.wslot_v(i_wslot_v),.xq(i_xq),.xq2(i_xq2),.xq2_done(b_xq2_done),.xq_done(b_xq_done));end endgenerate
function automatic[255:0] data(input integer row,round); for(integer w=0;w<8;w=w+1)data[32*w+:32]=32'hbeaf1280 ^ (row<<9) ^ (w*31) ^ (round<<24); endfunction
initial begin integer t,row,g,round; for(cyc=0;cyc<4096;cyc=cyc+1)begin @(negedge clk); t=cyc%1024;round=cyc/1024; rst_n=(t>=16 && !(t>=850&&t<860));
i_bid=0;
i_dq=0;
i_kq=0;
i_pq=0;
i_rq0=0;
i_rq1=0;
i_rq2=0;
i_rq3=0;
i_rq4=0;
i_rslot=0;
i_rslot_v=0;
i_sid=0;
i_wq0=0;
i_wq1=0;
i_wslot=0;
i_wslot_v=0;
i_xq=0;
i_xq2=0;
if(t>=32&&t<160)begin row=t-32;i_wslot_v=1;i_wslot=row%2; if(row%2==0)i_wq0={1'b1,1'b0,2'd0,10'(row),3'd0,data(row,round),8'hff}; else i_wq1={1'b1,1'b0,2'd0,10'(row),3'd0,data(row,round),8'hff};end
if(t>=160&&t<168)begin row=t-160;i_wslot_v=1;if(t%2==0)begin i_wslot=2;i_kq={1'b1,1'b0,2'd0,10'(row),3'd0,data(row,round),8'hff};end else begin i_wslot=6;i_dq={1'b1,1'b0,2'd0,10'(row),3'd0,data(row,round),8'hff};end end
if(t>=168&&t<176)begin i_wslot_v=1;i_wslot=0;i_wq0={1'b1,1'b0,2'd0,10'(t),3'd1,data(t,round),8'hff};end
if(t>=176&&t<816)begin row=(t-176)/5;g=(t-176)%5;i_rslot_v=1;i_rslot=g;case(g)
0:i_rq0={1'b1,1'b0,2'd0,10'(row),3'd0};
1:i_rq1={1'b1,1'b0,2'd0,10'(row),3'd0};
2:i_rq2={1'b1,1'b0,2'd0,10'(row),3'd0};
3:i_rq3={1'b1,1'b0,2'd0,10'(row),3'd0};
4:i_rq4={1'b1,1'b0,2'd0,10'(row),3'd0};
endcase end
if(t>=816&&t<824)begin i_rslot_v=1;i_rslot=5;i_pq={1'b1,1'b0,1'b0,10'(t-816),256'd0,8'd0,8'(t)};end
if(t==830)begin i_rslot_v=1;i_rslot=0;i_rq0={1'b1,1'b0,2'd0,10'd7,3'd0};i_rq1={1'b1,1'b0,2'd0,10'd33,3'd0};end
@(posedge clk); #1; if(t>=64&&!(t>=850&&t<880))begin
if(b_dq_done!==a_dq_done)begin bad=bad+1;if(bad<8)$display("DIFF dq_done cyc%0d got%h want%h",cyc,b_dq_done,prev_dq_done);end
if(b_eg!==a_eg)begin bad=bad+1;if(bad<8)$display("DIFF eg cyc%0d got%h want%h",cyc,b_eg,prev_eg);end
if(b_kq_done!==a_kq_done)begin bad=bad+1;if(bad<8)$display("DIFF kq_done cyc%0d got%h want%h",cyc,b_kq_done,prev_kq_done);end
if(b_pr!==a_pr)begin bad=bad+1;if(bad<8)$display("DIFF pr cyc%0d got%h want%h",cyc,b_pr,prev_pr);end
if(b_rr0!==a_rr0)begin bad=bad+1;if(bad<8)$display("DIFF rr0 cyc%0d got%h want%h",cyc,b_rr0,prev_rr0);end
if(b_rr1!==a_rr1)begin bad=bad+1;if(bad<8)$display("DIFF rr1 cyc%0d got%h want%h",cyc,b_rr1,prev_rr1);end
if(b_rr2!==a_rr2)begin bad=bad+1;if(bad<8)$display("DIFF rr2 cyc%0d got%h want%h",cyc,b_rr2,prev_rr2);end
if(b_rr3!==a_rr3)begin bad=bad+1;if(bad<8)$display("DIFF rr3 cyc%0d got%h want%h",cyc,b_rr3,prev_rr3);end
if(b_rr4!==a_rr4)begin bad=bad+1;if(bad<8)$display("DIFF rr4 cyc%0d got%h want%h",cyc,b_rr4,prev_rr4);end
if(b_status!==a_status)begin bad=bad+1;if(bad<8)$display("DIFF status cyc%0d got%h want%h",cyc,b_status,prev_status);end
if(b_wq_done0!==a_wq_done0)begin bad=bad+1;if(bad<8)$display("DIFF wq_done0 cyc%0d got%h want%h",cyc,b_wq_done0,prev_wq_done0);end
if(b_wq_done1!==a_wq_done1)begin bad=bad+1;if(bad<8)$display("DIFF wq_done1 cyc%0d got%h want%h",cyc,b_wq_done1,prev_wq_done1);end
if(b_xq2_done!==a_xq2_done)begin bad=bad+1;if(bad<8)$display("DIFF xq2_done cyc%0d got%h want%h",cyc,b_xq2_done,prev_xq2_done);end
if(b_xq_done!==a_xq_done)begin bad=bad+1;if(bad<8)$display("DIFF xq_done cyc%0d got%h want%h",cyc,b_xq_done,prev_xq_done);end
reads=reads+b_rr0[256]+b_rr1[256]+b_rr2[256]+b_rr3[256]+b_rr4[256];writes=writes+b_wq_done0+b_wq_done1;faults=faults+b_status[17];end end
$display("F512_RELAY_RESULT MUT%0d bad%0d reads%0d writes%0d faults%0d",MUT,bad,reads,writes,faults);if(MUT==0&&bad!=0)$fatal(1,"lockstep mismatch");if(reads<2000||writes<300)$fatal(1,"coverage empty");if(MUT!=0&&bad==0)$fatal(1,"mutant escaped");$finish;end endmodule
