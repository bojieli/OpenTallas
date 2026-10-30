`timescale 1ns/1ps
module tb;
reg ck=0;always #1 ck=~ck;
reg rst_n=0;reg rx_v=0;reg[146:0] rx_flit=0;reg tx_up=0;
wire [0:0] dc,df,dr;wire [127:0] dd;wire [146:0] dt;
wire [0:0] gc,gf,gr;wire [127:0] gd;wire [146:0] gt;
wire [0:0] mc,mf,mr;wire [127:0] md;wire [146:0] mt;
wire [0:0] bc,bf,br;wire [127:0] bd;wire [146:0] bt;
wire [0:0] zc,zf,zr;wire [127:0] zd;wire [146:0] zt;
wire dv,gv,mv,bv,zv,dtv,gtv,mtv,btv,ztv;
reg [7:0] return_pipe=0,base_pipe=0;reg credit_ref=0;
localparam N=256;
integer cyc=0,accepted=0,got=0,base_got=0,mut_diff=0,cmp=0,done_cycle=-1,base_done=-1;
reg [127:0] expect_data[0:N-1];
wire [0:0] r_cr=return_pipe[2];
wire [0:0] b_cr=base_pipe[2];
qkd_hr_phy_adp_capture #(.CREDIT_RETURN_CAPTURE(1)) dut(.ck(ck),.rst_n(rst_n),.c_v(1'b0),.c_d(128'b0),.c_cr(dc),.r_cr(r_cr),.r_d(dd),.r_v(dv),.fault(df),.rx_v(rx_v),.rx_flit(rx_flit),.tx_up(tx_up),.tx_flit(dt),.tx_v(dtv));
qkd_hr_phy_adp gold(.ck(ck),.rst_n(rst_n),.c_v(1'b0),.c_d(128'b0),.c_cr(gc),.r_cr(credit_ref),.r_d(gd),.r_v(gv),.fault(gf),.rx_v(rx_v),.rx_flit(rx_flit),.tx_up(tx_up),.tx_flit(gt),.tx_v(gtv));
qkd_hr_phy_adp_capture_mut #(.CREDIT_RETURN_CAPTURE(1)) mutant(.ck(ck),.rst_n(rst_n),.c_v(1'b0),.c_d(128'b0),.c_cr(mc),.r_cr(r_cr),.r_d(md),.r_v(mv),.fault(mf),.rx_v(rx_v),.rx_flit(rx_flit),.tx_up(tx_up),.tx_flit(mt),.tx_v(mtv));
qkd_hr_phy_adp baseline(.ck(ck),.rst_n(rst_n),.c_v(1'b0),.c_d(128'b0),.c_cr(bc),.r_cr(b_cr),.r_d(bd),.r_v(bv),.fault(bf),.rx_v(rx_v),.rx_flit(rx_flit),.tx_up(tx_up),.tx_flit(bt),.tx_v(btv));
qkd_hr_phy_adp_capture #(.CREDIT_RETURN_CAPTURE(0)) default_off(.ck(ck),.rst_n(rst_n),.c_v(1'b0),.c_d(128'b0),.c_cr(zc),.r_cr(b_cr),.r_d(zd),.r_v(zv),.fault(zf),.rx_v(rx_v),.rx_flit(rx_flit),.tx_up(tx_up),.tx_flit(zt),.tx_v(ztv));
always @(posedge ck or negedge rst_n)begin
 if(!rst_n)begin return_pipe<=0;base_pipe<=0;credit_ref<=0;end
 else begin return_pipe<={return_pipe[6:0],gv};base_pipe<={base_pipe[6:0],bv};credit_ref<=r_cr;end
end
always @(negedge ck)begin
 cyc=cyc+1;
 if(cyc==20)begin rst_n=1;tx_up=1;end
 if(cyc>=40&&cyc<40+N)begin
  rx_v=1;rx_flit={1'b1,expect_data[cyc-40],10'b0,8'(cyc-40)};accepted=accepted+1;
 end else begin rx_v=0;rx_flit=0;end
 #0.1;
 if(rst_n&&cyc>35)begin
  cmp=cmp+1;
  if({dc,df,dv,dd,dtv,dt}!=={gc,gf,gv,gd,gtv,gt})$fatal(1,"retimed lockstep cycle%0d",cyc);
  if({zc,zf,zv,zd,ztv,zt}!=={bc,bf,bv,bd,btv,bt})$fatal(1,"default-off lockstep cycle%0d",cyc);
  if({mf,mv,md}!={gf,gv,gd})mut_diff=mut_diff+1;
  if(df||gf||bf)$fatal(1,"legal credit trace fault cycle%0d",cyc);
  if(gv)begin if(got>=N||gd!==expect_data[got])$fatal(1,"capture word%0d",got);got=got+1;if(got==N)done_cycle=cyc;end
  if(bv)begin if(base_got>=N||bd!==expect_data[base_got])$fatal(1,"base word%0d",base_got);base_got=base_got+1;if(base_got==N)base_done=cyc;end
 end
 if(cyc==1800)begin
  if(got!=N||base_got!=N||mut_diff==0)$fatal(1,"incomplete got%0d base%0d mutant%0d",got,base_got,mut_diff);
  $display("HR_CREDIT_PASS cmp=%0d words=%0d base_words=%0d mutant_diffs=%0d added_return_edges=1 credit_capacity_delta=0 base_done=%0d capture_done=%0d delta=%0d",cmp,got,base_got,mut_diff,base_done,done_cycle,done_cycle-base_done);$finish;
 end
end
initial begin for(integer i=0;i<N;i=i+1)expect_data[i]={32'h1389abcd,32'(i),32'hdef03245,32'(i^'hbed0123)};end
endmodule
