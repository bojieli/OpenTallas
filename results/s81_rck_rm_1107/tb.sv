`timescale 1ns/1ps
module tb;
reg wclk=0,rclk=0,wen=1,ren=1,rst=0,wv=0; reg[511:0]wd=2;
always #0.417 if(wen)wclk=~wclk;else wclk=0;
initial begin #0.137;forever #0.4165 if(ren)rclk=~rclk;else rclk=0;end
wire[511:0]q,qo,qg,qu,qs,qd,qp,qr;wire f,fo,fg,fu,fs,fd,fp,fr;
rm_dut d(wclk,rst,wv,wd,rclk,rst,q,f);
rm_off offd(wclk,rst,wv,wd,rclk,rst,qo,fo);
rm_gold gold(wclk,rst,wv,wd,rclk,rst,qg,fg);
rm_unstaged ug(wclk,rst,wv,wd,rclk,rst,qu,fu);
rm_badsel ms(wclk,rst,wv,wd,rclk,rst,qs,fs);
rm_baddata md(wclk,rst,wv,wd,rclk,rst,qd,fd);
rm_badpub mp(wclk,rst,wv,wd,rclk,rst,qp,fp);
rm_badrelay mr(wclk,rst,wv,wd,rclk,rst,qr,fr);
reg[511:0]queue[0:32767];integer wi=0,ri=0,checks=0,err=0,selhits=0,datahits=0,pubhits=0,relayhits=0,epochs=0,id=1;reg checkon=0;
reg[511:0]oldpipe,oldmutpipe;reg[3:0]oldpub,oldwp,badoldpub;reg[7:0]oldsel;integer z;
function automatic[511:0] payload(input integer n);integer k;begin for(k=0;k<64;k=k+1)payload[k*8+:8]=(n*73+k*29+(n>>(k%11)));payload[0]=1;end endfunction
always@(posedge wclk)begin
 oldwp=d.wp_g;
 if(rst&&checkon&&d.push&&!d.idle)begin queue[wi]=wd;wi=wi+1;end
 #0.001;
 if(rst&&checkon)begin checks++;if(d.wp_g_pub!==oldwp)begin err++;$display("BAD publication");end end
end
always@(posedge rclk)begin
 oldpipe=d.r_pipe;oldmutpipe=mr.r_pipe;oldpub=d.wp_g_pub;badoldpub=mp.wp_g_pub;oldsel=d.empty?0:(8'd1<<d.rp[2:0]);
 #0.001;
 if(checkon&&rst)begin
 checks++;
 if(qo!==qg||fo!==fg)begin err++;$display("BAD off identity");end
 if(d.wp_g1!==oldpub)begin err++;$display("BAD sync");end
 if(mp.wp_g1!==badoldpub)pubhits++;
 if(q!==oldpipe)begin err++;$display("BAD relay");end
 if(qr!==oldmutpipe)relayhits++;
 for(z=0;z<64;z++)if(d.rsel[z]!==oldsel)begin err++;$display("BAD selector");end
 if(q[0]===1'b1)begin
 if(ri>=wi||q!==queue[ri])begin err++;if(err<8)$display("BAD stream ri%0d wi%0d",ri,wi);end
 ri++;
 end
 if(qs!==q)selhits++;
 if(qd!==q)datahits++;
 end
end
task reset_epoch;begin
 @(negedge wclk);rst=0;wv=0;wd=2;checkon=0;wi=0;ri=0;
 repeat(70)@(negedge rclk);rst=1;repeat(8)@(negedge rclk);checkon=1;epochs++;
end endtask
task send(input integer n);begin @(negedge wclk);wv=1;wd=payload(n);end endtask
task drain;begin @(negedge wclk);wv=0;wd=2;repeat(40)@(negedge rclk);if(wi!=ri)begin err++;$display("BAD drain %0d %0d",wi,ri);end end endtask
integer i;
initial begin
 reset_epoch;
 for(i=0;i<1600;i++)begin
 @(negedge wclk);wd=payload(id);id++;wv=(($urandom%4)!=0)&&(d.fill_w<4);
 end
 drain;
 // Pending staged write must not be published while its commit clock is stopped.
 reset_epoch;send(9001);@(negedge wclk);wv=0;wen=0;
 repeat(20)@(negedge rclk);if(ri!=0||d.wp_g2!=0)begin err++;$display("BAD pending publication");end
 wen=1;drain;
 // Paused reader: eight payloads accepted, ninth payload signals sticky overflow.
 reset_epoch;@(negedge rclk);ren=0;
 for(i=0;i<9;i++)send(10000+i);
 @(negedge wclk);wv=0;repeat(4)@(negedge wclk);
 if(wi!=8||!d.flt)begin err++;$display("BAD overflow wi%0d flt%b",wi,d.flt);end
 ren=1;drain;
 // Idle shedding at occupancy six preserves accepted payloads and stays fault-free.
 reset_epoch;@(negedge rclk);ren=0;
 for(i=0;i<6;i++)send(11000+i);
 @(negedge wclk);wd=2;wv=1;repeat(8)@(negedge wclk);wv=0;
 if(wi!=6||d.wp!=6||d.flt)begin err++;$display("BAD idle shed");end
 ren=1;drain;
 $display("RM_LOCAL4_RESULT checks=%0d errors=%0d epochs=%0d sel_mutant=%0d data_mutant=%0d pub_mutant=%0d relay_mutant=%0d",checks,err,epochs,selhits,datahits,pubhits,relayhits);
 if(err||!selhits||!datahits||!pubhits||!relayhits)$fatal(1,"RM fallback miter failed");$finish;
end
initial begin #10000;$fatal(1,"timeout");end
endmodule
