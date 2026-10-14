module tb_qkd_host_service_epoch_csr;
 timeunit 1ns;timeprecision 1ps;
 parameter MUT=0;
 reg ck=0;always #0.4165 ck=~ck;
 reg rst=0,por=0;wire begin_v;wire[15:0]begin_epoch;
 reg awv=0,wv=0,arv=0;reg[12:0]awa=0,ara=0;reg[31:0]wd=0;wire awr,wr,bvalid,arr,rvalid,irq;wire[31:0]rd;
 wire csr_available,csr_fault,csr_busy,cold;wire[7:0]bcredits,bavail;
 wire[25:0]gd[0:7];wire[31:0]gs[0:7];
 wire[7:0]txv;wire[511:0]txd[0:7];reg[7:0]rxv=0,txcr=0;reg[511:0]rxd[0:7];
 wire[7:0]fault,sbv,adv;wire[15:0]sbe[0:7],ape[0:7];wire[7:0]ready8[0:7],ack8[0:7];wire[127:0]epochs[0:7];wire[7:0]permission;
 wire[7:0]gr,gabort;wire[15:0]ge[0:7];wire[92:0]gt[0:7];
 reg[7:0]iv=0,bv=0;reg[15:0]ih[0:7];reg[31:0]bt[0:7];
 qkd_host_csr_service_pins #(.ENABLE_SERVICE(1))csr(.clk(ck),.rst_n(rst),.por_n(por),
 .s_awvalid(awv),.s_awready(awr),.s_awaddr(awa),.s_wvalid(wv),.s_wready(wr),.s_wdata(wd),.s_wstrb(4'hf),.s_bvalid(bvalid),.s_bready(1'b1),.s_bresp(),
 .s_arvalid(arv),.s_arready(arr),.s_araddr(ara),.s_rvalid(rvalid),.s_rready(1'b1),.s_rdata(rd),.s_rresp(),
 .h_awvalid(),.h_awready(1'b0),.h_awaddr(),.h_wvalid(),.h_wready(1'b0),.h_wdata(),.h_wstrb(),.h_bvalid(1'b0),.h_bready(),.h_arvalid(),.h_arready(1'b0),.h_araddr(),.h_rvalid(1'b0),.h_rready(),.h_rdata(32'b0),.h_irq(1'b0),
 .sys_ready(1'b1),.boot_fault(1'b0),.boot_state(4'b0),.boot_err(4'b0),.soft_rst(),.fault_src(32'b0),.die_fault_vec(32'h87654321),.die_kst(80'h123456789abcdef12345),.cnt({gs[0],6'b0,gd[0],448'b0}),.irq(irq),
 .begin_tx_cr(bcredits[0]),.begin_tx_available(bavail[0]),.service_ready8(ready8[0]),.pending_ack8(ack8[0]),.service_epoch8(epochs[0]),.service_fault(gabort[0]||fault[0]),.ingest_permission(permission[0]),
 .begin_v(begin_v),.begin_epoch(begin_epoch),.begin_available(csr_available),.begin_fault(csr_fault),.decode_request(1'b0),.decode_start(1'b0),.decode_done(1'b1),.epoch_busy(csr_busy),.startup_allowed(cold));
 integer packets=0,checks=0;reg hold_begin7=0,held_valid=0;reg[511:0]held_begin7;reg pause_link=0,drop7=0;reg[9:0]kst[0:7];reg[511:0]last7;
 genvar g;
 for(g=0;g<8;g=g+1)begin:d
 qkd_host_service_guard guard(.ck_guard(ck),.rst_n(rst),.service_protocol_fault(g==0?csr_fault:1'b0),.raw_faults(25'b0),.die_id(3'(g)),.physical_faults(8'b0),.transport_faults(8'b0),
 .accepted_ing_v(iv[g]),.accepted_ing_cls(2'b0),.accepted_ing_header(ih[g]),.done_v(1'b0),.done_d(64'b0),.boot_barrier_v(bv[g]),.boot_barrier_target(bt[g]),
 .begin_v(sbv[g]),.begin_epoch(sbe[g]),.pending_advertised(adv[g]),.pending_epoch(ape[g]),.local_tk(93'b0),.guarded_tk(gt[g]),.abort(gabort[g]),.service_ready(gr[g]),.service_epoch(ge[g]),.diag_raw(gd[g]),.status(gs[g]),.groups(),.physical_diag(),.transport_diag());
 qkd_host_ctrl_service_packet #(.DIE(g),.STRAPPED(1),.ENABLE_SERVICE(1),.MUT(MUT))ep(.ck(ck),.rst_n(rst),.die_id(3'(g)),.rx_v(rxv[g]),.rx_d(rxd[g]),.rx_cr(),.tx_v(txv[g]),.tx_d(txd[g]),.tx_cr(txcr[g]),
 .local_tk(gt[g]),.local_kst(kst[g]),.local_boot(2'b11),.cmd_v(1'b0),.cmd_hc(182'b0),.cmd_cr(),.hc(),.tk8(),.kst8(),.boot8(),.seen(),.fault(fault[g]),
 .startup_allowed(g==0?cold:1'b1),.local_service_ready(gr[g]),.local_service_epoch(ge[g]),.begin_v(g==0?begin_v:1'b0),.begin_epoch(begin_epoch),.begin_cr(bcredits[g]),.begin_available(bavail[g]),
 .service_begin_v(sbv[g]),.service_begin_epoch(sbe[g]),.pending_advertised(adv[g]),.pending_epoch(ape[g]),.service_ready8(ready8[g]),.pending_ack8(ack8[g]),.service_epoch8(epochs[g]),.ingest_permission(permission[g]));
 end
 // Actual addressed packets, every endpoint owns its own status sequence.
 // A central 32-entry test link schedules at most one sender per edge.
 reg[511:0]linkq[0:31];integer lw=0,lr=0,lc=0,j,target;
 always @(negedge ck)if(rst)begin
 rxv=0;txcr=0;
 if(lc>0&&!pause_link)begin
 target=linkq[lr][31:24];if(hold_begin7&&target==128&&linkq[lr][7:0]==8'h23)begin held_begin7=linkq[lr];held_valid=1;end
 else for(j=0;j<8;j=j+1)if(target==(1<<j))begin rxv[j]=1;rxd[j]=linkq[lr];end
 lr=(lr+1)%32;lc=lc-1;
 end
 for(j=0;j<8;j=j+1)if(txv[j])begin
 if(j==7)last7=txd[j];
 if(j==7&&drop7)drop7=0;else begin if(lc==32)$fatal(1,"test link overflow");linkq[lw]=txd[j];lw=(lw+1)%32;lc=lc+1;end txcr[j]=1;packets=packets+1;
 end
 end
 task edges(input integer n);repeat(n)begin @(posedge ck);#0.01;end endtask
 task check(input reg ok,input string why);begin checks++;if(!ok)$fatal(1,"%s ready=%h ack=%h faults=%h guard=%h",why,ready8[0],ack8[0],fault,gabort);end endtask
 task mark(input integer die);begin @(posedge ck);#0.1;iv[die]=1;ih[die]=2;@(posedge ck);#0.1;iv[die]=0;edges(10);@(posedge ck);#0.1;bv[die]=1;bt[die]=0;@(posedge ck);#0.1;bv[die]=0;end endtask
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

 task allmarkers;begin for(integer k=0;k<8;k++)mark(k);edges(120);end endtask
 task stale(input reg readybit,input reg[15:0]seq);begin
 @(posedge ck);#0.1;linkq[lw]=512'h01070221|(512'(seq)<<32)|(512'd3<<151)|(512'(readybit)<<153)|(512'd1<<154);lw=(lw+1)%32;lc=lc+1;
 end endtask
 initial begin
 for(j=0;j<8;j++)begin ih[j]=0;bt[j]=0;rxd[j]=0;kst[j]=0;end
 edges(4);por=1;rst=1;edges(100);check(cold&&ready8[0]==255&&fault==0,"initial genuine POR cold ready");
 writebar(13'h10a0,1);edges(160);check(begin_epoch==1&&ack8[0]==255&&permission[0]&&ready8[0]==0&&csr_busy,"BAR epoch1 all8 actual ACK");
 allmarkers();check(ready8[0]==255&&!csr_busy&&csr_available&&!csr_fault,"actual all8 epoch1 barriers complete");
 // Host-reset contract: all eight endpoints and queue/CDC model flush; POR stays high.
 rst=0;lw=0;lr=0;lc=0;rxv=0;txcr=0;edges(4);rst=1;edges(60);
 check(!cold&&ready8[0]==0&&ack8[0]==0&&!permission[0],"soft reset retained allocator invalidates warm/cold readiness");
 hold_begin7=1;writebar(13'h10a0,1);edges(20);check(begin_epoch==2&&ready8[0]==0,"fresh retained BEGIN2");
 stale(0,0);stale(1,1);edges(20);
 check(d[0].ep.boot8[15:14]==0&&!ready8[0][7]&&!ack8[0][7]&&!permission[0]&&!fault,"old allocated epoch1 seq0/1 cannot prove boot/ACK/readiness");
 check(held_valid,"genuine peer7 BEGIN retained on link");hold_begin7=0;@(posedge ck);#0.1;linkq[lw]=held_begin7;lw=(lw+1)%32;lc=lc+1;held_valid=0;
 edges(160);check(ack8[0]==255&&permission[0]&&ready8[0]==0&&fault==0&&!csr_fault,"matching real2 pending ACK remains possible");
 allmarkers();check(ready8[0]==255&&!csr_busy&&fault==0&&!gabort&&!csr_fault,"matching real2 barriers complete");
 // Reset while prefill pending must reserve the next distinct epoch again.
 writebar(13'h10a0,1);edges(160);check(begin_epoch==3&&ready8[0]==0&&ack8[0]==255,"real epoch3 pending");
 rst=0;lw=0;lr=0;lc=0;rxv=0;txcr=0;edges(4);rst=1;edges(60);
 writebar(13'h10a0,1);edges(160);check(begin_epoch==4&&ack8[0]==255&&ready8[0]==0,"midprefill reset uses new epoch4");
 allmarkers();check(ready8[0]==255&&!csr_busy&&fault==0&&!gabort&&!csr_fault,"epoch4 genuine completion");
 $display("PASS service retained epoch CSR checks=%0d packets=%0d",checks,packets);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
