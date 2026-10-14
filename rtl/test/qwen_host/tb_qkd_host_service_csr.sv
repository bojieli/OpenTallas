module tb_qkd_host_service_csr;
 timeunit 1ns;timeprecision 1ps;
 parameter MUT=0;
 reg ck=0;always #0.4165 ck=~ck;
 reg rst=0,por=0,awv=0,wv=0,arv=0;reg[12:0]awa=0,ara=0;reg[31:0]wd=0;
 wire awr,wr,bvalid,arr,rvalid,irq;wire[31:0]rd;
 reg bcr=0,bavail=1,sfault=0,permission=0,req=0,start=0,done=1;
 reg[7:0]ready8=255,ack8=0;reg[127:0]epochs=0;
 wire bv,available,bfault,busy,cold;wire[15:0]epoch;
 reg[24:0]raw=0;reg iv=0;wire[25:0]diag;wire[31:0]status;wire gabort,gready;wire[92:0]gt;
 qkd_host_service_guard guard(.ck_guard(ck),.rst_n(rst),.service_protocol_fault(bfault),.raw_faults(raw),.die_id(3'b0),.physical_faults(8'b0),.transport_faults(8'b0),
 .accepted_ing_v(iv),.accepted_ing_cls(2'b1),.accepted_ing_header(16'h0780),.done_v(1'b0),.done_d(64'b0),.boot_barrier_v(1'b0),.boot_barrier_target(32'b0),.begin_v(1'b0),.begin_epoch(16'b0),.pending_advertised(1'b0),.pending_epoch(16'b0),.local_tk(93'b0),.guarded_tk(gt),.abort(gabort),.service_ready(gready),.service_epoch(),.diag_raw(diag),.status(status),.groups(),.physical_diag(),.transport_diag());
 wire[511:0]cnt={status,6'b0,diag,448'b0};
 qkd_host_csr_service_pins #(.ENABLE_SERVICE(1),.MUT_EPOCH(MUT))dut(.clk(ck),.rst_n(rst),.por_n(por),
 .s_awvalid(awv),.s_awready(awr),.s_awaddr(awa),.s_wvalid(wv),.s_wready(wr),.s_wdata(wd),.s_wstrb(4'hf),.s_bvalid(bvalid),.s_bready(1'b1),.s_bresp(),
 .s_arvalid(arv),.s_arready(arr),.s_araddr(ara),.s_rvalid(rvalid),.s_rready(1'b1),.s_rdata(rd),.s_rresp(),
 .h_awvalid(),.h_awready(1'b0),.h_awaddr(),.h_wvalid(),.h_wready(1'b0),.h_wdata(),.h_wstrb(),.h_bvalid(1'b0),.h_bready(),.h_arvalid(),.h_arready(1'b0),.h_araddr(),.h_rvalid(1'b0),.h_rready(),.h_rdata(32'b0),.h_irq(1'b0),
 .sys_ready(1'b1),.boot_fault(1'b0),.boot_state(4'b0),.boot_err(4'b0),.soft_rst(),.fault_src(32'b0),.die_fault_vec(32'h87654321),.die_kst(80'h123456789abcdef12345),.cnt(cnt),.irq(irq),
 .begin_tx_cr(bcr),.begin_tx_available(bavail),.service_ready8(ready8),.pending_ack8(ack8),.service_epoch8(epochs),.service_fault(gabort),.ingest_permission(permission),
 .begin_v(bv),.begin_epoch(epoch),.begin_available(available),.begin_fault(bfault),.decode_request(req),.decode_start(start),.decode_done(done),.epoch_busy(busy),.startup_allowed(cold));
 integer checks=0,begins=0;reg[15:0]last_epoch;
 always @(posedge ck)if(bv)begin begins++;last_epoch=epoch;end
 task edges(input integer n);repeat(n)begin @(posedge ck);#0.01;end endtask
 task check(input reg ok,input string why);begin checks++;if(!ok)$fatal(1,"CSR %s epoch=%d busy=%b fault=%b",why,epoch,busy,bfault);end endtask
 task writebar(input reg[12:0]a,input reg[31:0]v);integer n;begin
 @(negedge ck);awa=a;wd=v;awv=1;wv=1;n=0;
 while(!(awr&&wr)&&n<100)begin @(negedge ck);n++;end
 if(n==100)$fatal(1,"BAR write ready timeout");@(negedge ck);awv=0;wv=0;n=0;
 while(!bvalid&&n<100)begin @(negedge ck);n++;end
 if(n==100)$fatal(1,"BAR B timeout");edges(6);
 end endtask
 task readbar(input reg[12:0]a,output reg[31:0]v);integer n;begin
 @(negedge ck);ara=a;arv=1;n=0;while(!arr&&n<100)begin @(negedge ck);n++;end
 if(n==100)$fatal(1,"BAR AR timeout");@(negedge ck);arv=0;n=0;while(!rvalid&&n<100)begin @(negedge ck);n++;end
 if(n==100)$fatal(1,"BAR R timeout");v=rd;edges(6);
 end endtask
 reg[31:0]v;integer d;
 initial begin
 edges(4);por=1;rst=1;edges(20);check(available&&cold&&!bfault,"cold available");
 readbar(13'h1000,v);check(v==32'h51535953,"original global ID");readbar(13'h1088,v);check(v==32'h87654321,"original full die summary");readbar(13'h1090,v);check(v==32'hdef12345,"original raw KST bank");
 readbar(13'h1058,v);check(v==0,"original counter14 rawdiag");
 iv=1;edges(1);iv=0;edges(12);readbar(13'h105c,v);check(v[15:8]==1&&!v[1],"actual pending descriptor software status");
 raw=25'b1<<22;edges(12);readbar(13'h1058,v);check(v[22],"actual CTRL raw sticky fault BAR");readbar(13'h105c,v);check(v[2]&&!v[1],"actual sticky abort readyblocked BAR");raw=0;edges(12);readbar(13'h1058,v);check(v[22],"sticky raw diag after source low");
 rst=0;edges(4);rst=1;edges(20);writebar(13'h10a0,1);check(begins==1&&last_epoch==1&&busy&&!available&&!cold,"real BAR allocates epoch1 only");
 bcr=1;edges(1);bcr=0;ack8=255;ready8=255;epochs={8{16'd1}};edges(15);check(!busy&&available,"all8 matching completion returns command credit");
 // Host soft reset retains allocation, invalidates active state and cold bypass.
 rst=0;edges(4);rst=1;ready8=0;ack8=0;epochs=0;edges(20);check(!cold&&available&&!busy,"soft reset retained allocation forbids cold bypass");
 writebar(13'h10a0,1);check(begins==2&&last_epoch==2&&busy,"fresh retained next epoch2");
 bcr=1;edges(1);bcr=0;ack8=255;ready8=255;epochs={8{16'd1}};edges(15);check(busy&&!available,"old allocated epoch1 cannot complete epoch2");
 epochs={8{16'd2}};edges(15);check(!busy&&available,"matching real epoch2 completion");
 req=1;edges(1);req=0;edges(15);check(!available,"real host request blocks BEGIN despite stale done high");done=0;edges(5);done=1;edges(15);check(available,"done low rearm followed genuine done returns decode idle");
 start=1;edges(1);start=0;edges(10);writebar(13'h10a0,1);check(bfault&&begins==2,"BEGIN during genuine launched decode rejects");
 edges(12);readbar(13'h1058,v);check(v[25],"allocator protocol fault actual rawdiag25 BAR");
 rst=0;edges(4);rst=1;edges(20);
 force dut.u_core.allocated_epoch=16'hffff;edges(4);release dut.u_core.allocated_epoch;edges(10);
 check(!available,"epochFFFF requires real POR/link retraining");writebar(13'h10a0,1);check(bfault&&begins==2,"epoch wrap never aliases0");
 $display("PASS service CSR checks=%0d begins=%0d",checks,begins);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
