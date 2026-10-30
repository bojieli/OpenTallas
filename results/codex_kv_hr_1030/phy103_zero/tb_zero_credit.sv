`timescale 1ns/1ps
module tb;
reg ck=0;always #1 ck=~ck;
reg rst_n=0;reg rx_v=0;reg[146:0]rx_flit=0;reg tx_up=0;
wire[0:0]dc,df,gc,gf,mc,mf;wire[127:0]dd,gd,md;wire[146:0]dt,gt,mt;wire dv,gv,mv,dtv,gtv,mtv;
reg[7:0]credit_pipe=0;wire r_cr=credit_pipe[2];integer cyc=0,got=0,mutdiff=0,checks=0;localparam N=256;reg[127:0]expect_data[0:N-1];
qkd_hr_phy_adp_gold_zero #(.CREDIT_RETURN_CAPTURE(0)) gold(.ck(ck),.rst_n(rst_n),.c_v(1'b0),.c_d(128'b0),.c_cr(gc),.r_cr(r_cr),.r_d(gd),.r_v(gv),.fault(gf),.rx_v(rx_v),.rx_flit(rx_flit),.tx_up(tx_up),.tx_flit(gt),.tx_v(gtv));
qkd_hr_phy_adp_zero_m1 #(.CREDIT_RETURN_CAPTURE(0)) dut(.ck(ck),.rst_n(rst_n),.c_v(1'b0),.c_d(128'b0),.c_cr(dc),.r_cr(r_cr),.r_d(dd),.r_v(dv),.fault(df),.rx_v(rx_v),.rx_flit(rx_flit),.tx_up(tx_up),.tx_flit(dt),.tx_v(dtv));
qkd_hr_phy_adp_zero_m1_mut #(.CREDIT_RETURN_CAPTURE(0)) mutant(.ck(ck),.rst_n(rst_n),.c_v(1'b0),.c_d(128'b0),.c_cr(mc),.r_cr(r_cr),.r_d(md),.r_v(mv),.fault(mf),.rx_v(rx_v),.rx_flit(rx_flit),.tx_up(tx_up),.tx_flit(mt),.tx_v(mtv));
always @(posedge ck or negedge rst_n)if(!rst_n)credit_pipe<=0;else credit_pipe<={credit_pipe[6:0],gv};
always @(negedge ck)begin
 cyc=cyc+1;
 if(cyc==20)begin rst_n=1;tx_up=1;end
 if(cyc>=40&&cyc<40+N)begin rx_v=1;rx_flit={1'b1,expect_data[cyc-40],10'b0,8'(cyc-40)};end else begin rx_v=0;rx_flit=0;end
 #0.1;
 if(rst_n&&cyc>35)begin
  checks=checks+1;
  if({dc,df,dv,dd,dtv,dt}!=={gc,gf,gv,gd,gtv,gt})$fatal(1,"ZERO_CREDIT native lockstep mismatch cycle%0d",cyc);
  if({mc,mf,mv,md,mtv,mt}!=={gc,gf,gv,gd,gtv,gt})mutdiff=mutdiff+1;
  if(df||gf)$fatal(1,"legal native trace fault cycle%0d",cyc);
  if(gv)begin if(got>=N||gd!==expect_data[got])$fatal(1,"native word%0d",got);got=got+1;end
 end
 if(cyc==1800)begin
  if(got!=N||mutdiff==0)$fatal(1,"incomplete words%0d mutant%0d",got,mutdiff);
  $display("ZERO_CREDIT_NATIVE PASS checks%0d words%0d mutant_diffs%0d added_credit_cycles0 added_macro_cycles0",checks,got,mutdiff);$finish;
 end
end
initial for(integer i=0;i<N;i=i+1)expect_data[i]={32'h1389abcd,32'(i),32'hdef03245,32'(i^'hbed0123)};
endmodule
