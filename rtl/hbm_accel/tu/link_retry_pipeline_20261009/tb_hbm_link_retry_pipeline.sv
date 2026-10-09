`timescale 1ns/1ps
module tb_hbm_link_retry_pipeline;
 localparam W=545,SW=12,EW=24,DEPTH=512;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst=0;reg [EW-1:0] epoch=1;
 reg iv=0;wire ir,tv;reg tr=1;reg [W-1:0] id=0;
 wire [W-1:0] td;wire [SW-1:0] ts;wire [EW-1:0] te;
 reg rv=0,ue=0,ordy=1;reg [W-1:0] rd=0;reg [SW-1:0] rs=0;
 reg [EW-1:0] re=1;wire rr,ov;wire [W-1:0] od;
 wire [SW-1:0] ack,debt;wire nak;wire [EW-1:0] ae;
 wire fault;wire [31:0] retries;
 reg fv=0,fg=1,fn=0;reg [SW-1:0] fs=0;reg [EW-1:0] fe=1;
 ot_hbm_link_retry_pipeline #(.ENABLE(1),.W(W),.SW(SW),.EW(EW),
 .DEPTH(DEPTH),.TIMEOUT(4096),.MAX_RETRY(3)) dut
 (.clk(clk),.rst_n(rst),.session(epoch),.in_valid(iv),.in_ready(ir),.in_data(id),
 .tx_valid(tv),.tx_ready(tr),.tx_data(td),.tx_seq(ts),.tx_session(te),
 .rx_valid(rv),.rx_ready(rr),.rx_ue(ue),.rx_data(rd),.rx_seq(rs),.rx_session(re),
 .out_valid(ov),.out_ready(ordy),.out_data(od),.ack_seq(ack),.ack_nak(nak),
 .ack_session(ae),.fb_valid(fv),.fb_good(fg),.fb_nak(fn),.fb_seq(fs),
 .fb_session(fe),.fault(fault),.retained(debt),.replay_count(retries));
 function [W-1:0] payload(input integer n);
 integer j;begin for(j=0;j<W;j=j+1)payload[j]=((j*17+n*31)^(n>>(j%7)))&1;payload[31:0]=n;end
 endfunction
 integer sent=0,seen=0,cycle=0,inject=0,k;
 reg run=0,corrupt=0;
 always @(negedge clk)if(run)begin
 cycle=cycle+1;iv=sent<1300;id=payload(sent);
 fv=1;fg=1;fe=epoch;fs=ack;fn=nak;
 ordy=cycle%7!=0;tr=(!rv||rr)&&cycle%11!=0;
 end
 always @(posedge clk)if(run&&rst)begin
 if(!rv||rr)begin
 rv<=tv&&tr;rd<=td;rs<=ts;re<=te;ue<=0;
 if(corrupt&&tv&&tr&&ts==5&&inject==0)begin ue<=1;inject<=1;end
 end
 if(iv&&ir)sent<=sent+1;
 if(ov&&ordy)begin
 if(od!==payload(seen))$fatal(1,"payload/order expected%0d got%0d",seen,od[31:0]);
 seen=seen+1;
 end
 if(debt>DEPTH)$fatal(1,"retained overflow");
 if(fault)$fatal(1,"unexpected fault");
 end
 task tick;begin @(posedge clk);#0.05;end endtask
 task wait4;begin repeat(12)tick;end endtask
 task reset_link;begin
 run=0;@(negedge clk);rst=0;iv=0;rv=0;fv=0;ue=0;ordy=1;tr=1;fg=1;fn=0;
 tick;@(negedge clk);rst=1;tick;
 end endtask
 task offer(input integer n);begin
 @(negedge clk);iv=1;id=payload(n);
 do begin @(posedge clk);end while(!ir);
 @(negedge clk);iv=0;
 end endtask
 initial begin
 reset_link;run=1;
 for(k=0;k<15000&&seen<1300;k=k+1)tick;
 run=0;iv=0;rv=0;
 if(seen!=1300||retries!=0)$fatal(1,"normal delivery seen%0d",seen);
 $display("PASS full545 1300 records, ring wrap, paced admission, independent stalls");
 reset_link;sent=0;seen=0;cycle=0;inject=0;corrupt=1;run=1;
 for(k=0;k<40000&&seen<1300;k=k+1)tick;
 run=0;iv=0;rv=0;
 if(seen!=1300||retries==0)$fatal(1,"UE replay seen%0d",seen);
 $display("PASS UE, coalesced NAK, duplicate removal, golden payload order");
 reset_link;epoch=2;fv=1;fe=1;fs=7;fn=1;rv=1;re=1;wait4;
 if(fault||ack!=0||debt!=0||ov)$fatal(1,"stale session");
 rv=0;fv=0;offer(0);wait4;
 fv=1;fe=2;fs=0;fn=0;wait4;if(debt!=1)$fatal(1,"duplicate ACK");
 fs=12'hfff;wait4;if(fault||debt!=1)$fatal(1,"stale ACK");
 fs=1;fg=0;wait4;if(debt!=1)$fatal(1,"bad FEC ACK");
 fg=1;wait4;if(debt!=0)$fatal(1,"good ACK");
 fs=3;wait4;if(!fault)$fatal(1,"future ACK");
 $display("PASS stale, duplicate, bad-FEC, future ACK and session filtering");
 reset_link;epoch=3;offer(0);
 for(k=0;k<20000&&!fault;k=k+1)tick;
 if(!fault||debt!=1||tv)$fatal(1,"retry exhaustion");
 $display("PASS bounded retries retain debt");
 reset_link;epoch=4;
 for(k=0;k<DEPTH;k=k+1)offer(k);
 wait4;if(debt!=DEPTH||ir)$fatal(1,"full512 debt");
 fv=1;fe=4;fs=0;fn=1;wait4;
 if(retries!=1)$fatal(1,"initial NAK");
 wait4;if(retries!=1)$fatal(1,"duplicate NAK");
 fs=12'hfff;wait4;if(fault||retries!=1||debt!=DEPTH)$fatal(1,"stale NAK");
 $display("PASS actual full512 retention and duplicate/reordered feedback");
 reset_link;epoch=5;offer(0);wait4;
 dut.g_on.u_storage.g_bank[0].g_macro[0].u_mem.arr[0][17]=~dut.g_on.u_storage.g_bank[0].g_macro[0].u_mem.arr[0][17];
 dut.g_on.u_storage.g_bank[0].g_macro[0].u_mem.arr[0][18]=~dut.g_on.u_storage.g_bank[0].g_macro[0].u_mem.arr[0][18];
 fv=1;fe=5;fs=0;fn=1;
 for(k=0;k<60&&!fault;k=k+1)begin tick;if(tv)$fatal(1,"poison emitted");end
 if(!fault||debt!=1)$fatal(1,"poison debt");
 $display("PASS real replay SRAM double-error poison blocks launch");
 reset_link;epoch=6;tr=0;offer(0);wait4;
 dut.g_on.txd[17]=~dut.g_on.txd[17];#0.01;
 if(tv||!fault||debt!=1)$fatal(1,"TX register poison");tick;
 reset_link;epoch=7;ordy=0;rv=1;re=7;rs=0;rd=payload(0);tick;
 @(negedge clk);rv=0;dut.g_on.rxd[17]=~dut.g_on.rxd[17];#0.01;
 if(ov||!fault)$fatal(1,"RX register poison");tick;
 reset_link;epoch=8;offer(0);wait4;
 @(negedge clk);fv=1;fe=8;fs=0;fn=0;tick;
 @(negedge clk);fv=0;dut.g_on.mail_seq[0]=~dut.g_on.mail_seq[0];
 wait4;if(!fault||debt!=1)$fatal(1,"feedback identity poison");
 $display("PASS TX/RX stage and feedback mailbox corruption detect/poison");
 $display("PASS_ALL");$finish;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
