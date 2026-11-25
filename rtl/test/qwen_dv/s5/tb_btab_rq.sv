`timescale 1ns/1ps
// QC-STA-BTLAT3 11-25: qfd_dv_s5_btab_s4 with OT_BTAB_S4R + OT_BTAB_RQ (request-leg register + registered read) ==
// qfd_dv_s5_btab_safe delayed two edges.  Writes of every table kind and idle read cycles are mixed in; a same-cycle
// read/write of one row is avoided as in tb_btab_safe_r (the SRAM model asserts on it; the request and write legs take
// the same edge, so the RTL keeps that order).  -DTB_ONE_DELAY compares against the one-edge (BT_LAT 2) form and must
// FAIL (the bench sees the added request edge).
module tb_btab_rq;
reg ck=0;always #0.5 ck=~ck;
reg bt_re=0,tw_we=0;reg [8:0]bt_word=0;reg[1:0]tw_kind=0;reg[23:0]tw_addr=0;reg[1023:0]tw_data=0;
wire[255:0]a,b;reg[255:0]a1=0,a2=0;
qfd_dv_s5_btab_safe u_a(.ck(ck),.bt_re(bt_re),.bt_word(bt_word),.bt_q(a),.tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data(tw_data));
qfd_dv_s5_btab_s4 u_b(.ck(ck),.bt_re(bt_re),.bt_word(bt_word),.bt_ql(b[127:0]),.bt_qh(b[255:128]),.tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_lo(tw_data[511:0]),.tw_hi(tw_data[1023:512]));
always @(posedge ck) begin a1 <= a; a2 <= a1; end
integer c,j,nz=0;
initial begin
for(c=0;c<12000;c=c+1) begin
@(negedge ck);
bt_re=(c>=132)&&($urandom%8!=0);tw_we=(c<128)||(c%4==0);tw_kind=(c<128)?2:($urandom%4);tw_addr=(c<128)?(c*4):(($urandom%128)*4);
bt_word=$urandom%512;
if(tw_we && bt_word[8:2]==tw_addr[8:2])bt_word[8:2]=bt_word[8:2]+1;
for(j=0;j<32;j=j+1)tw_data[32*j+:32]=(c<128)?((c<<16)|j):$urandom;
@(posedge ck);#0.1;
if(c>138)begin
`ifdef TB_ONE_DELAY
if(a1!==b)$fatal(1,"BTABRQ_EQ FAIL cycle=%0d ref_d1=%h got=%h",c,a1,b);
`else
if(a2!==b)$fatal(1,"BTABRQ_EQ FAIL cycle=%0d ref_d2=%h got=%h",c,a2,b);
`endif
if(|b)nz=nz+1;
end
end
if(nz<9000)$fatal(1,"BTABRQ_EQ FAIL no data coverage nz=%0d",nz);
$display("BTABRQ_EQ PASS cycles=%0d nonzero=%0d",c,nz);$finish;
end
endmodule
