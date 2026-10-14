module tb_qkd_host_service_guard;
 timeunit 1ns;timeprecision 1ps;
 parameter MUT=0;
 reg ck=0;always #0.4165 ck=~ck;
 reg rst=0;reg[24:0]raw=0;reg[2:0]role=7;reg[7:0]pf=1,tf=2;
 reg iv=0,dv=0,bv=0,ev=0,av=0;reg[1:0]cls=0;reg[15:0]hdr=0,ep=0,ap=0;
 reg[63:0]dd=0;reg[31:0]bt=0;reg[92:0]tk=93'h123456789abcdef;
 wire[92:0]gt;wire abort,ready;wire[15:0]epoch;wire[25:0]diag;
 wire[31:0]status;wire[3:0]groups;wire[7:0]pout,tout;
 qkd_host_service_guard #(.MUT(MUT)) dut(ck,rst,raw,role,pf,tf,iv,cls,hdr,dv,dd,bv,bt,ev,ep,av,ap,tk,gt,abort,ready,epoch,diag,status,groups,pout,tout,1'b0);
 integer checks=0,i;
 task edges(input integer n);repeat(n)begin @(posedge ck);#0.01;end endtask
 task check(input reg ok,input string why);begin checks=checks+1;if(!ok)$fatal(1,"guard %s status=%h diag=%h",why,status,diag);end endtask
 task reset;begin @(negedge ck);rst=0;iv=0;dv=0;bv=0;ev=0;av=0;raw=0;role=7;edges(3);@(negedge ck);rst=1;edges(2);check(!ready,"startup quiet minimum");edges(10);check(ready&&!abort,"no-prefill startup");end endtask
 task ingest(input reg[1:0]c,input reg[15:0]h);begin @(negedge ck);iv=1;cls=c;hdr=h;@(negedge ck);iv=0;end endtask
 task ack;begin @(negedge ck);av=1;ap=epoch;@(negedge ck);av=0;end endtask
 task done(input reg[7:0]tag,input reg[31:0]target);begin @(negedge ck);dv=1;dd={8'h01,8'h00,tag,8'h00,target};@(negedge ck);dv=0;end endtask
 task barrier(input reg[31:0]target);begin @(negedge ck);bv=1;bt=target;@(negedge ck);bv=0;end endtask
 initial begin
 reset();ingest(1,16'h0180);edges(12);check(!ready&&!abort,"pending fence blocks");
 done(1,0);edges(12);check(!ready&&!abort,"pending snapshot required");ack();edges(12);check(!ready&&!abort,"DONE plus ACK alone cannot reopen ingest");ingest(0,2);barrier(0);edges(15);check(ready&&!abort,"zero-sector DONE and actual BOOT_END");
 ingest(1,16'h0200);ack();ingest(0,2);ingest(1,16'h0300);barrier(0);edges(15);check(!ready&&!abort,"old barrier cannot close newer nonfenced");
 ingest(1,16'h0480);done(4,1);edges(15);check(!ready&&!abort,"later fence cannot close nonfenced");
 ingest(0,2);barrier(1);edges(15);check(ready&&!abort,"real latest prefix barrier");
 @(negedge ck);ev=1;ep=1;@(negedge ck);ev=0;edges(12);check(!ready&&epoch==1&&!abort,"begin revokes until pending ACK");
 @(negedge ck);av=1;ap=0;@(negedge ck);av=0;edges(12);check(!ready,"stale epoch ACK rejected");ack();edges(12);check(!ready,"ACK alone cannot complete new epoch");ingest(0,2);barrier(1);edges(15);check(ready,"matching epoch ACK and real barrier");
 reset();for(i=0;i<128;i=i+1)ingest(1,{i[7:0],8'h80});ack();edges(10);check(status[15:8]==128&&!ready&&!abort,"128 fenced entries");
 @(negedge ck);dv=1;for(i=0;i<128;i=i+1)begin dd={8'h01,8'h00,i[7:0],8'h00,i[31:0]};@(negedge ck);end dv=0;edges(20);check(!ready&&!abort,"128 DONEs do not fabricate prefix barrier");ingest(0,2);barrier(127);edges(15);check(ready&&!abort,"128 exact FIFO completions and true prefix barrier");
 ingest(1,16'h0080);done(0,127);edges(15);check(!abort,"tag wrap/reuse and equal target");ack();edges(12);check(!ready,"tag reuse DONE still needs BOOT_END");ingest(0,2);barrier(127);edges(15);check(ready,"reuse drains through real barrier");
 done(0,127);edges(8);check(abort&&diag[25]&&!ready,"duplicate no pending faults");
 reset();for(i=0;i<128;i=i+1)begin ingest(1,16'h0000);ingest(0,2);end ack();edges(10);check(status[31:24]==128&&!ready&&!abort,"128 marker checkpoints");@(negedge ck);bv=1;for(i=0;i<128;i=i+1)begin bt=i;@(negedge ck);end bv=0;edges(20);check(ready&&!abort,"128 checkpoint barriers full-rate");
 reset();ingest(1,16'h0580);done(6,1);edges(10);check(abort&&diag[25],"wrong tag faults");
 reset();@(negedge ck);iv=1;dv=1;cls=1;
 for(i=0;i<128;i=i+1)begin hdr={i[7:0],8'h80};dd={8'h01,8'h00,i[7:0],8'h00,i[31:0]};@(negedge ck);end
 iv=0;dv=0;ack();edges(25);check(!ready&&!abort,"cold full-rate DONE128 does not establish ownership");ingest(0,2);barrier(127);edges(20);check(ready&&!abort,"cold full-rate128 actual prefix barrier");
 reset();for(i=0;i<129;i=i+1)ingest(1,{i[7:0],8'h80});edges(10);check(abort&&diag[25],"fenced capacity129 fails closed");
 reset();for(i=0;i<129;i=i+1)ingest(0,2);edges(10);check(abort&&diag[25],"marker capacity129 fails closed");
 reset();ingest(1,16'h0180);ingest(1,16'h0280);done(1,1);done(2,0);edges(15);check(abort&&diag[25],"backward done target fails closed");
 reset();ingest(0,2);ingest(0,2);barrier(1);barrier(0);edges(15);check(abort&&diag[25],"backward actual retirement barrier fails closed");
 reset();ingest(2,0);ack();edges(20);check(!ready&&!abort,"orphan payload needs real prefix barrier");ingest(0,2);barrier(0);edges(20);check(ready&&!abort,"orphan payload closed by actual prefix barrier");
 reset();ingest(0,1);ack();edges(20);check(!ready&&!abort,"nonmarker ingest CSR needs prefix barrier");ingest(0,2);barrier(0);edges(20);check(ready&&!abort,"CSR closed by prefix barrier");
 reset();ingest(1,16'h0180);done(1,1);ingest(2,0);ack();edges(25);check(!ready&&!abort,"late payload after received DONE cannot be coalesced");ingest(0,2);barrier(1);edges(20);check(ready&&!abort,"late payload actual prefix barrier");
 reset();ingest(1,16'h0180);ingest(2,0);done(1,1);ack();edges(25);check(!ready&&!abort,"paired payload DONE alone requires explicit BOOT_END policy");ingest(0,2);barrier(1);edges(20);check(ready&&!abort,"paired payload actual BOOT_END ownership");
 reset();ingest(1,16'h0180);ingest(2,0);ingest(2,0);done(1,1);ack();edges(25);check(!ready&&!abort,"orphan PAY before old DONE cannot establish payload ownership");ingest(0,2);barrier(1);edges(20);check(ready&&!abort,"pre-DONE orphan requires actual ordered BOOT_END");
 for(i=0;i<25;i=i+1)begin reset();@(negedge ck);raw=25'b1<<i;edges(10);check(abort&&!ready&&diag[i],"raw fault abort done0");check(gt[88]&&gt[87:0]==tk[87:0]&&gt[92:89]==tk[92:89],"exact tk layout");@(negedge ck);raw=0;edges(10);check(abort&&diag[i],"fault sticky");end
 reset();@(negedge ck);raw=1;edges(10);check(pout==8'h81&&tout==2,"registered role diagnostic placement");
 reset();ingest(1,16'h0580);edges(5);reset();check(ready&&epoch==0&&!abort,"reset midprefill epoch flush");
 reset();@(negedge ck);role=6;edges(10);check(abort&&diag[25],"strap mutation");
 $display("PASS service guard checks=%0d",checks);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
