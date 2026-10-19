`timescale 1ns/1ps
module lane_case #(parameter W=1,N=1,K=2,AGE=2)(input ck,rst, output reg done=0);
reg [W-1:0] src=0; integer sequence_no=0; integer bit_no; wire[W-1:0] b, mid, mid2; wire ep,ep2,c1,c2;
reg [W-1:0] hist[0:255]; integer t=0;
`ifdef MUT_PHASE
always @(negedge ck) begin
 sequence_no<=sequence_no+1;
 for(bit_no=0;bit_no<W;bit_no=bit_no+1)src[bit_no]<=((sequence_no >> (bit_no%8)) & 1)^((bit_no/8)%2);
end
`else
always @(posedge ck) begin
 sequence_no<=sequence_no+1;
 for(bit_no=0;bit_no<W;bit_no=bit_no+1)src[bit_no]<=((sequence_no >> (bit_no%8)) & 1)^((bit_no/8)%2);
end
`endif
`ifdef MUT_K
wire[2:0] strap=K[2:0]^3'd1;
`else
wire[2:0] strap=K[2:0];
`endif
reg [W-1:0] field_q=0; always @(posedge ck)field_q<=src;
`ifdef MUT_FIELD
wire[W-1:0] launch=(W==548 && N==2) ? field_q : src;
`else
wire[W-1:0] launch=src;
`endif
generate if(N==1) begin
 ot_qfd_land #(.W(W),.FIRST(1)) l(.ckf(ck),.ea(rst),.i(launch),.ck(ck),.rs(rst),.k(strap),.o(b),.fault());
end else begin
 ot_qfd_lane_st #(.W(W),.FIRST(1)) a(.ck(ck),.en(rst),.a(launch),.b(mid),.eb(ep),.ck_o(c1));
 if(N==2) begin
 ot_qfd_land #(.W(W),.FIRST(0)) l(.ckf(c1),.ea(ep),.i(mid),.ck(ck),.rs(rst),.k(strap),.o(b),.fault());
 end else begin
 ot_qfd_lane_st #(.W(W),.FIRST(0)) a1(.ck(c1),.en(ep),.a(mid),.b(mid2),.eb(ep2),.ck_o(c2));
 ot_qfd_land #(.W(W),.FIRST(0)) l(.ckf(c2),.ea(ep2),.i(mid2),.ck(ck),.rs(rst),.k(strap),.o(b),.fault());
 end
end endgenerate
always @(posedge ck) begin
 #0.1; hist[t]=src;
 if(t>=32 && t<200 && b!==hist[t-AGE]) $fatal(1,"SOURCE_AGE_FAIL W=%0d N=%0d K=%0d AGE=%0d t=%0d b=%h expected=%h",W,N,K,AGE,t,b,hist[t-AGE]);
 if(t==200) done=1;
 t=t+1;
end
endmodule
module lane_age_tb;
reg ck=0; always #5 ck=~ck; reg rst=0;
initial begin #12; rst=1; end
wire[13:0]done;
lane_case #(.W(1),.N(1),.K(2),.AGE(2)) c0(.ck(ck),.rst(rst),.done(done[0]));
lane_case #(.W(4),.N(1),.K(2),.AGE(2)) c1(.ck(ck),.rst(rst),.done(done[1]));
lane_case #(.W(5),.N(1),.K(2),.AGE(2)) c2(.ck(ck),.rst(rst),.done(done[2]));
lane_case #(.W(1),.N(1),.K(2),.AGE(2)) c3(.ck(ck),.rst(rst),.done(done[3]));
lane_case #(.W(1),.N(1),.K(2),.AGE(2)) c4(.ck(ck),.rst(rst),.done(done[4]));
lane_case #(.W(4),.N(1),.K(2),.AGE(2)) c5(.ck(ck),.rst(rst),.done(done[5]));
lane_case #(.W(5),.N(1),.K(2),.AGE(2)) c6(.ck(ck),.rst(rst),.done(done[6]));
lane_case #(.W(548),.N(2),.K(2),.AGE(2)) c7(.ck(ck),.rst(rst),.done(done[7]));
lane_case #(.W(1),.N(3),.K(3),.AGE(3)) c8(.ck(ck),.rst(rst),.done(done[8]));
lane_case #(.W(1),.N(1),.K(2),.AGE(2)) c9(.ck(ck),.rst(rst),.done(done[9]));
lane_case #(.W(548),.N(1),.K(2),.AGE(2)) c10(.ck(ck),.rst(rst),.done(done[10]));
lane_case #(.W(524),.N(2),.K(2),.AGE(2)) c11(.ck(ck),.rst(rst),.done(done[11]));
lane_case #(.W(59),.N(2),.K(2),.AGE(2)) c12(.ck(ck),.rst(rst),.done(done[12]));
lane_case #(.W(2),.N(2),.K(2),.AGE(2)) c13(.ck(ck),.rst(rst),.done(done[13]));
initial begin wait(&done); $display("SOURCE_AGE_PASS fields=14 edges=168 resets=1 ideal_roots=1"); $finish; end
endmodule
