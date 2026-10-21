`timescale 1ns/1ps
module tb_arf1;
 reg ck=0;always #5 ck=~ck;
 reg rst=0;reg[115:0]cmd=0;reg[1094:0]own=0,pass=0;
 wire[1094:0]out;wire[115:0]cmd_q;wire bad;
 qfd_dv_s8_fdn_arf1 dut(.ck(ck),.rst_n(rst),.cmd_i(cmd),.cmd_q(cmd_q),.ch_dn_i(1038'd0),.chu_q(pass),.own_ch(own),.ch_dn_o(out),.pc_bad(bad),.agu_q(10'd0),.ag_own(10'd0));
 task tick;begin @(posedge ck);#1;@(negedge ck);end endtask
 integer k;
 initial begin
 repeat(2)tick();rst=1;repeat(5)tick();
 cmd[0]=1;cmd[3:1]=7;cmd[7:4]=3;tick();cmd=0;tick();tick();
 cmd[0]=1;cmd[115:112]=15;cmd[3:1]=0;cmd[5:4]=0;cmd[22:7]=3;cmd[54:23]=32'hcafe1234;tick();cmd=0;tick();
 for(k=0;k<3;k=k+1)begin
 own=0;own[1094:548]={1'b1,32'hdeadbeef,1'b0,1'b0,512'(k+100)};tick();
 if(out[1094:548]!=={1'b1,32'hcafe1234,1'b0,1'(k==2),512'(k+100)} || bad)$fatal(1,"ARF1 stamp k%0d actual%h bad%b",k,out[1094:548],bad);
 own=0;tick();
 end
 // A nonzero slice forwards an unarmed passed word byte-for-byte.
 pass[1094:548]={1'b1,32'hbeef5678,1'b1,1'b1,512'd999};tick();
 if(out[1094:548]!==pass[1094:548] || bad)$fatal(1,"ARF passthrough");
 pass=0;own=0;rst=0;repeat(3)tick();rst=1;repeat(5)tick();
 cmd=0;cmd[0]=1;cmd[3:1]=7;cmd[7:4]=3;tick();cmd=0;tick();tick();
 cmd[0]=1;cmd[115:112]=15;cmd[22:7]=1;cmd[54:23]=32'h5a5a1234;tick();cmd=0;tick();
 own[1094:548]={1'b1,32'hdeadbeef,1'b0,1'b0,512'd777};tick();
 if(out[1094:548]!=={1'b1,32'h5a5a1234,1'b0,1'b1,512'd777} || bad)$fatal(1,"ARF reset/rearm stale payload");
 $display("PASS ARF1 tag/data/last before original publication,3beats,no extra edge,nonzero slice unarmed passthrough, reset/rearm");$finish;
 end
endmodule
