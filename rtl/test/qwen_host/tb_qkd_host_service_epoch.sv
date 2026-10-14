module tb_qkd_host_service_epoch;
 timeunit 1ns;timeprecision 1ps;
 parameter MUT=0;
 reg ck=0;always #0.4165 ck=~ck;
 reg cmdv=0;reg[181:0]cmdhc=0;wire[7:0]begin_avail;wire[181:0]hcout[0:7];integer metas[0:7];
 reg rst=0,begin_v=0;reg[15:0]begin_epoch=1;
 wire[7:0]txv;wire[511:0]txd[0:7];reg[7:0]rxv=0,txcr=0;reg[511:0]rxd[0:7];
 wire[7:0]fault,sbv,adv;wire[15:0]sbe[0:7],ape[0:7];wire[7:0]ready8[0:7],ack8[0:7];wire[127:0]epochs[0:7];wire[7:0]permission;
 wire[7:0]gr,gabort;wire[15:0]ge[0:7];wire[92:0]gt[0:7];
 reg[7:0]iv=0,bv=0;reg[15:0]ih[0:7];reg[31:0]bt[0:7];
 integer packets=0,checks=0;reg pause_link=0,drop7=0;reg[9:0]kst[0:7];reg[511:0]last7;
 genvar g;
 for(g=0;g<8;g=g+1)begin:d
 qkd_host_service_guard guard(.ck_guard(ck),.rst_n(rst),.service_protocol_fault(1'b0),.raw_faults(25'b0),.die_id(3'(g)),.physical_faults(8'b0),.transport_faults(8'b0),
 .accepted_ing_v(iv[g]),.accepted_ing_cls(2'b0),.accepted_ing_header(ih[g]),.done_v(1'b0),.done_d(64'b0),.boot_barrier_v(bv[g]),.boot_barrier_target(bt[g]),
 .begin_v(sbv[g]),.begin_epoch(sbe[g]),.pending_advertised(adv[g]),.pending_epoch(ape[g]),.local_tk(93'b0),.guarded_tk(gt[g]),.abort(gabort[g]),.service_ready(gr[g]),.service_epoch(ge[g]),.diag_raw(),.status(),.groups(),.physical_diag(),.transport_diag());
 qkd_host_ctrl_service_packet #(.DIE(g),.STRAPPED(1),.ENABLE_SERVICE(1),.MUT(MUT))ep(.ck(ck),.rst_n(rst),.die_id(3'(g)),.rx_v(rxv[g]),.rx_d(rxd[g]),.rx_cr(),.tx_v(txv[g]),.tx_d(txd[g]),.tx_cr(txcr[g]),
 .local_tk(gt[g]),.local_kst(kst[g]),.local_boot(2'b11),.cmd_v(g==0?cmdv:1'b0),.cmd_hc(cmdhc),.cmd_cr(),.hc(hcout[g]),.tk8(),.kst8(),.boot8(),.seen(),.fault(fault[g]),
 .startup_allowed(1'b1),.local_service_ready(gr[g]),.local_service_epoch(ge[g]),.begin_v(g==0?begin_v:1'b0),.begin_epoch(begin_epoch),.begin_cr(),.begin_available(begin_avail[g]),
 .service_begin_v(sbv[g]),.service_begin_epoch(sbe[g]),.pending_advertised(adv[g]),.pending_epoch(ape[g]),.service_ready8(ready8[g]),.pending_ack8(ack8[g]),.service_epoch8(epochs[g]),.ingest_permission(permission[g]));
 end
 always @(posedge ck)if(rst)for(integer m=1;m<8;m++)if(hcout[m][113])metas[m]++;
 // Actual addressed packets, every endpoint owns its own status sequence.
 // A central 32-entry test link schedules at most one sender per edge.
 reg[511:0]linkq[0:31];integer lw=0,lr=0,lc=0,j,target;
 always @(negedge ck)if(rst)begin
 rxv=0;txcr=0;
 if(lc>0&&!pause_link)begin
 target=linkq[lr][31:24];for(j=0;j<8;j=j+1)if(target==(1<<j))begin rxv[j]=1;rxd[j]=linkq[lr];end
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
 initial begin
 for(j=0;j<8;j++)begin ih[j]=0;bt[j]=0;rxd[j]=0;kst[j]=0;metas[j]=0;end
 edges(4);rst=1;edges(100);check(ready8[0]==255&&fault==0&&gabort==0,"genuine no-prefill all8 ready");
 @(posedge ck);#0.1;begin_v=1;@(posedge ck);#0.1;begin_v=0;edges(10);check(ready8[0]==0&&!permission[0],"BEGIN invalidation before ingress");
 edges(150);check(ack8[0]==255&&permission[0]&&ready8[0]==0&&fault==0,"actual all8 pending ACK permits ingress");
 for(integer k=0;k<7;k++)mark(k);edges(100);check(ready8[0]==127&&fault==0&&!gabort,"peer7 real barrier delays global ready");
 mark(7);edges(100);check(ready8[0]==255&&fault==0&&gabort==0,"all8 genuine barriers ready");
 // A genuine old-epoch status is retained in the link over the next BEGIN.
 pause_link=1;kst[7]=1;edges(15);check(lc>0,"genuine old status queued");
 begin_epoch=2;@(posedge ck);#0.1;begin_v=1;@(posedge ck);#0.1;begin_v=0;edges(8);
 check(ready8[0]==0,"new epoch clears all old readiness");pause_link=0;edges(160);
 check(ready8[0]==0&&ack8[0]==255&&permission[0]&&fault==0,"old epoch ready cannot reopen new epoch");
 for(integer k=0;k<8;k++)mark(k);edges(100);check(ready8[0]==255&&fault==0,"second epoch all genuine barriers");
 // HC retains its original four-entry bounded queue and seven-copy credits.
 @(posedge ck);#0.1;cmdv=1;
 for(integer k=0;k<4;k++)begin cmdhc=(182'(k+1)<<39)|(182'd1<<113);@(posedge ck);#0.1;end cmdv=0;
 edges(6);check(!begin_avail[0],"BEGIN unavailable while actual HC queue/broadcast active");
 edges(160);for(integer k=1;k<8;k++)check(metas[k]==4,"all four queued HC payload pulses retained");
 check(begin_avail[0]&&fault==0,"registered HC idle boundary restores BEGIN credit");
 // Replay an actual peer packet, retaining its original sequence and epoch.
 @(posedge ck);#0.1;linkq[lw]=last7;lw=(lw+1)%32;lc=lc+1;edges(20);
 check(fault[0]&&!permission[0],"duplicate genuine status fails closed");
 // Reset generation: old epoch0 pending snapshots can be in flight over BEGIN1.
 rst=0;pause_link=1;lw=0;lr=0;lc=0;kst[7]=0;edges(4);rst=1;edges(25);
 check(lc>=14,"real initial pending and ready snapshots buffered");
 begin_epoch=1;@(posedge ck);#0.1;begin_v=1;@(posedge ck);#0.1;begin_v=0;edges(25);
 pause_link=0;edges(10);check(ack8[0]==1&&!permission[0],"stale reset epoch pending cannot ACK new BEGIN");
 edges(200);check(ack8[0]==255&&!fault,"new reset epoch real ACKs");
 drop7=1;for(integer k=0;k<8;k++)mark(k);edges(100);
 check(ready8[0]==127&&!fault,"lost peer ready keeps package blocked");
 kst[7]=1;edges(50);check(fault[0]&&!permission[0],"lost status sequence gap faults");
 $display("PASS service epoch checks=%0d packets=%0d",checks,packets);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
