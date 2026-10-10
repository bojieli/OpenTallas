`timescale 1ns/1ps
// Minimal PHY/core composition. Landing array is a test-only finite TU FIFO;
// production landing storage remains owned by the native protected endpoint.
module tb_hbm_tu_retry_phy_port;
 reg pclk=0,clk=0;
 always #0.416667 pclk=~pclk;
 initial begin #0.173;forever #0.416667 clk=~clk;end
 reg rst=0,up=0;reg[23:0]epoch=1;
 reg iv=0,rv=0,ue=0,fv=0,pop=0;reg[544:0]id=0,rd=0;
 reg[11:0]rs=0,fs=0;reg[23:0]re=1,fe=1;reg fn=0;reg[9:0]fp=0;
 wire ov,tv,rr,cr,fault,nak;wire[544:0]od,td;
 wire[11:0]ts,ack,retained,ingress;wire[23:0]te,ae;wire[9:0]ap,debt;
 wire tr=!rv||rr;
`ifdef OT_TU_LINK
`ifdef OT_TU_LINK_MUT
 ot_hbm_tu_retry_phy_port_lk #(.ENABLE(1),.MUT_CRED(1)) dut(
`else
 ot_hbm_tu_retry_phy_port_lk #(.ENABLE(1)) dut(
`endif
`else
 ot_hbm_tu_retry_phy_port #(.ENABLE(1)) dut(
`endif
 .pclk(pclk),.prst_n(rst),.phy_link_up(up),.phy_session(epoch),.clk(clk),.rst_n(rst),.core_link_up(up),
 .ph_tx_v(iv),.ph_tx_flit(id),.ph_rx_v(ov),.ph_rx_flit(od),.rx_credit(pop),.sw_cr_ret(cr),
 .fec_tx_v(tv),.fec_tx_ready(tr),.fec_tx_data(td),.fec_tx_seq(ts),.fec_tx_session(te),
 .fec_rx_v(rv),.fec_rx_ready(rr),.fec_rx_ue(ue),.fec_rx_data(rd),.fec_rx_seq(rs),.fec_rx_session(re),
 .ack_seq(ack),.ack_nak(nak),.ack_session(ae),.ack_pop(ap),
 .fb_valid(fv),.fb_good(1'b1),.fb_nak(fn),.fb_seq(fs),.fb_session(fe),.fb_pop(fp),
 .fault(fault),.retained(retained),.ingress_debt(ingress),.rx_debt(debt));
 wire off_tx,off_rx,off_ready,off_credit,off_fault;
 ot_hbm_tu_retry_phy_port off_dut(.pclk(pclk),.prst_n(rst),.phy_link_up(up),.phy_session(epoch),
 .clk(clk),.rst_n(rst),.core_link_up(up),.ph_tx_v(iv),.ph_tx_flit(id),.rx_credit(pop),
 .fec_rx_v(rv),.fec_tx_ready(1'b1),.ph_rx_v(off_rx),.fec_tx_v(off_tx),.fec_rx_ready(off_ready),.sw_cr_ret(off_credit),.fault(off_fault));
 function[544:0]payload(input integer n);integer j;begin
 for(j=0;j<545;j=j+1)payload[j]=((j*17+n*31)^(n>>(j%7)))&1;payload[31:0]=n;end endfunction
 reg[544:0]landing[0:255];
 integer sent=0,landed=0,consumed=0,returned=0,pc=0,cc=0,inject=0;
 reg run=0,allow_pop=0,corrupt=0;
 always@(negedge pclk)if(run)begin
 pc=pc+1;iv=sent<1300 && sent-returned<256;id=payload(sent);
 fv=1;fs=ack;fn=nak;fe=epoch;fp=ap;
 end
 always@(posedge pclk)if(run&&rst&&up)begin
 if(iv)sent<=sent+1;
 if(tr)begin rv<=tv;rd<=td;rs<=ts;re<=te;ue<=0;
 if(corrupt&&tv&&ts==5&&inject==0)begin ue<=1;inject<=1;end end
 if(ov)begin
 if(landed-consumed>=256)$fatal(1,"actual landing FIFO overflow");
 if(od!==payload(landed))$fatal(1,"PHY545 order expected%0d got%0d",landed,od[31:0]);
 landing[landed%256]<=od;landed<=landed+1;end
 if(fault)$fatal(1,"PHY/core composition fault pc%0d",pc);
 if(off_tx||off_rx||off_ready||off_credit||off_fault)$fatal(1,"default-off leaf active");
 end
 always@(negedge clk)begin cc=cc+1;pop=run&&allow_pop&&consumed<landed&&cc%7!=0;end
 always@(posedge clk)if(run&&rst&&up)begin
 if(pop)begin
 if(landing[consumed%256]!==payload(consumed))$fatal(1,"core capture mismatch");
 consumed<=consumed+1;end
 if(cr)begin if(returned>=consumed)$fatal(1,"credit before actual pop");returned<=returned+1;end
 if(sent-returned>256)$fatal(1,"TU source credit debt exceeded");
 end
 task tick;begin @(posedge pclk);#0.02;end endtask
 task reset_link;begin
 run=0;@(negedge pclk);rst=0;up=0;iv=0;rv=0;fv=0;pop=0;
 repeat(6)tick;sent=0;landed=0;consumed=0;returned=0;inject=0;pc=0;
 @(negedge pclk);rst=1;up=1;repeat(6)tick;run=1;
 end endtask
 integer i;
 initial begin
 reset_link;
 for(i=0;i<3000&&landed<256;i=i+1)tick;
 repeat(30)tick;
 if(sent!=256||landed!=256||returned!=0||debt!=256||fault)$fatal(1,"ACK returned source credit without core pop");
 $display("PASS real545 two-clock full256 landing debt, ACK alone returns no sourcecredit");
 allow_pop=1;for(i=0;i<7000&&returned<1300;i=i+1)tick;
 if(sent!=1300||landed!=1300||consumed!=1300||returned!=1300||ingress!=0||debt!=0)$fatal(1,"normal PHY/core drain");
 $display("PASS 1300 full545 protected ingress/replay records, phase-shifted core pops, cumulative wrap");
 epoch=2;corrupt=1;reset_link;
 for(i=0;i<10000&&returned<1300;i=i+1)tick;
 if(sent!=1300||landed!=1300||consumed!=1300||returned!=1300||inject!=1)$fatal(1,"FEC replay PHY/core drain");
 $display("PASS FECUE replay delivers once and returns one core credit per actual pop");
 run=0;@(negedge pclk);up=0;iv=1;repeat(4)tick;
 if(tv||ov||cr)$fatal(1,"linkdown escaped");
 epoch=3;reset_link;run=0;fv=1;fe=2;fs=1300;fp=1300;fn=1;repeat(8)tick;
 if(fault||retained||ingress||debt)$fatal(1,"old session controls crossed reset");
 $display("PASS coordinated reset/linkdown and stale24bit session; defaultoff has no storage/outputs");
 $display("PASS_ALL");$finish;
 end
 initial begin#30000;$fatal(1,"watchdog");end
endmodule
