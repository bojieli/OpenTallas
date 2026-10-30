`timescale 1ps/1fs
module tb;
reg ck=0;always #416.5 ck=~ck;
reg rst_n=1,bs_re=0,tw_we=0;reg[23:0]bs_addr=0;reg[1:0]tw_kind=0;reg[8:2]tw_addr=0;reg[1023:0]tw_data=0;
wire[1:0]fg,fc;wire[255:0]qg[0:1],qc[0:1];integer checks=0,i,j;
genvar m;generate for(m=0;m<2;m=m+1)begin:G
qfd_dv_s8x_btab_original #(.MIF(m)) gold(.ck(ck),.rst_n(rst_n),.bs_re(bs_re),.bs_addr(bs_addr),.bs_q(qg[m]),.tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data(tw_data),.fault(fg[m]));
qfd_dv_s8x_btab #(.MIF(m),.FAULT_OUTPUT_CLONE(1)) cand(.ck(ck),.rst_n(rst_n),.bs_re(bs_re),.bs_addr(bs_addr),.bs_q(qc[m]),.tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data(tw_data),.fault(fc[m]));
end endgenerate
always @(posedge ck)begin #2;if(fg!==fc)$fatal(1,"FAULT_MISMATCH cycle%0d gold%b clone%b",checks,fg,fc);for(j=0;j<2;j=j+1)if(qg[j]!==qc[j])$fatal(1,"DATA_MISMATCH MIF%0d",j);checks=checks+1;end
initial begin
// Cold/warm asynchronous reset edges occur away from clocks, then long held reset.
#71;rst_n=0;repeat(6)@(negedge ck);rst_n=1;
for(i=0;i<900;i=i+1)begin
 @(negedge ck);bs_re=(i%4!=0);bs_addr=(i%29==11)?24'h080123:(i%511);tw_we=(i%3==0);tw_kind=(i%4);tw_addr=i%128;tw_data={32{32'h92cc0000 ^ i}};
 if(i==217 || i==479 || i==731)begin #93;rst_n=0;repeat(6)@(negedge ck);#53;rst_n=1;end
end
repeat(10)@(negedge ck);$display("LOCKSTEP_PASS cycles=%0d MIF0/1 cold+3warm reset full outputs",checks);$finish;
end
endmodule
