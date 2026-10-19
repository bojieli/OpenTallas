`timescale 1ps/1fs
module tb;
reg clk=0;always #512 clk=~clk;
reg rst_n=0;reg [63:0] resets=0;
reg slot_parity=0;reg [7:0] refresh_reload=122;
reg wr_v=0;reg[4:0]wr_bank=0,wr_col=0;reg[18:0]wr_row=0;reg wr_rd=0;
wire[89:0] a,b;wire ready;
ot_hbm_r14_aq_pc_safe u_new(.clk(clk),.rst_n(rst_n),.reset_regions(resets),.slot_parity(slot_parity),.refresh_reload(refresh_reload),.row_v(a[0]),.row_op(a[3:1]),.row_bank(a[8:4]),.row_row(a[27:9]),.col_v(a[28]),.col_bank(a[33:29]),.col_col(a[38:34]),.ref_fault(a[39]),.wr_v(wr_v),.wr_bank(wr_bank),.wr_col(wr_col),.wr_row(wr_row),.wr_rd(wr_rd),.wr_r(a[40]),.col_we(a[41]),.col_aq(a[42]),.dbg_held(a[74:43]));
ref_ot_hbm_r14_aq_pc_safe_18bd u_ref(.clk(clk),.rst_n(rst_n),.reset_regions(resets),.slot_parity(slot_parity),.refresh_reload(refresh_reload),.row_v(b[0]),.row_op(b[3:1]),.row_bank(b[8:4]),.row_row(b[27:9]),.col_v(b[28]),.col_bank(b[33:29]),.col_col(b[38:34]),.ref_fault(b[39]),.wr_v(wr_v),.wr_bank(wr_bank),.wr_col(wr_col),.wr_row(wr_row),.wr_rd(wr_rd),.wr_r(b[40]),.col_we(b[41]),.col_aq(b[42]),.dbg_held(b[74:43]));
integer n,checks=0,pushes=0,cols=0,rows=0;reg[31:0]rng=32'hcafe1234;
initial begin
for(n=0;n<24000;n=n+1)begin
 @(negedge clk);
 rng=(rng<<1)^((rng[31])?32'h04c11db7:0);
 rst_n=(n%3001)>=4;resets={64{rst_n}};
 wr_v=rst_n&&b[40]&&rng[2:0]!=0;
 wr_bank=rng[9:5];wr_col=rng[14:10];wr_row={12'd0,rng[21:15]};wr_rd=rng[22];
 if(n%1500<900)begin wr_bank=5'((n/64)%32);wr_row=19'(n/2048);end
 @(posedge clk);#1;
 if(rst_n)begin
 checks=checks+1;pushes=pushes+wr_v;cols=cols+b[28];rows=rows+b[0];
 if(a[74:0]!==b[74:0])$fatal(1,"AQ_EQ_MISMATCH n=%0d a=%h b=%h",n,a[74:0],b[74:0]);
 end
end
if(cols<100||rows<100||pushes<100)$fatal(1,"AQ_EQ_COVERAGE");
$display("AQ_EQ_PASS checks=%0d pushes=%0d cols=%0d rows=%0d",checks,pushes,cols,rows);$finish;
end
endmodule
