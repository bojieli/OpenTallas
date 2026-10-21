`timescale 1ns/1ps
module tb_engine_cold;
 parameter integer ND=9,NP=1728,NS=1728;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,run=0; integer mut_clock=0;
 reg [255:0] desc[0:ND-1];reg[511:0]pay[0:NP-1];reg[287:0]golden[0:NS-1];
 reg seen[0:NS-1];reg[31:0]rnd=32'h13482971;
 integer di=0,pi=0,writes=0,dones=0,cyc=0,epochs=0,checks=0,found,i,idle=0,release_cycle=0;
 reg first_desc=0;
 wire dv=run&&rst_n&&di<ND&&(di==0||rnd[0]);wire iv=run&&rst_n&&pi<NP&&(pi==0||rnd[1]);
 wire[255:0]dd=di<ND?desc[di]:256'd0;wire[511:0]pd=pi<NP?pay[pi]:512'd0;
 wire ready=run&&rst_n&&rnd[2];
 wire gd,gi,gw,gr,gdone,gb,nd,ni,nw,nr,ndone,nb;
 wire[31:0]ga,gra,gns,gnb,na,nra,nns,nnb;wire[255:0]gwd,nwd;wire[7:0]gt,nt;
 wire dc1,dc2;wire candidate_out_clock=mut_clock?~clk:clk;
 qkd_host_native_engine #(.AW(32),.HDMAX(128),.KVHMAX(2),.QKV(1),.APIPE(0),.QPIPE(2),.NATIVE_ROWS(1),.QMUT(0)) gold(
 .clk(clk),.clk_bank({2{clk}}),.clk_out(clk),.rst_n(rst_n),
 .d_v(dv),.d_rdy(gd),.d_data(dd),.in_v(iv),.in_rdy(gi),.in_data(pd),
 .w_v(gw),.w_rdy(ready),.w_addr(ga),.w_data(gwd),
 .r_v(gr),.r_rdy(1'b0),.r_addr(gra),.rd_v(1'b0),.rd_data(256'd0),
 .done_v(gdone),.done_tag(gt),.busy(gb),.n_sectors(gns),.n_beats(gnb));
 qkd_host_native_engine_n32 dut(
 .clk(clk),.clk_bank({2{clk}}),.clk_out(candidate_out_clock),.rst_n(rst_n),
 .rst_n__c1(rst_n),
 .rst_n__c2(rst_n),
 .rst_n__c3(rst_n),
 .rst_n__c4(rst_n),
 .rst_n__c5(rst_n),
 .rst_n__c6(rst_n),
 .rst_n__c7(rst_n),
 .rst_n__c8(rst_n),
 .rst_n__c9(rst_n),
 .rst_n__c10(rst_n),
 .rst_n__c11(rst_n),
 .rst_n__c12(rst_n),
 .rst_n__c13(rst_n),
 .rst_n__c14(rst_n),
 .rst_n__c15(rst_n),
 .rst_n__c16(rst_n),
 .rst_n__c17(rst_n),
 .rst_n__c18(rst_n),
 .rst_n__c19(rst_n),
 .rst_n__c20(rst_n),
 .rst_n__c21(rst_n),
 .rst_n__c22(rst_n),
 .rst_n__c23(rst_n),
 .rst_n__c24(rst_n),
 .rst_n__c25(rst_n),
 .rst_n__c26(rst_n),
 .rst_n__c27(rst_n),
 .rst_n__c28(rst_n),
 .rst_n__c29(rst_n),
 .rst_n__c30(rst_n),
 .rst_n__c31(rst_n),
 .rst_n__c32(rst_n),
 .rst_n__c33(rst_n),
 .d_v(dv),.d_rdy(nd),.d_data(dd),.in_v(iv),.in_v__c1(iv),.in_rdy(ni),.in_data(pd),
 .w_v(nw),.w_rdy(ready),.w_addr(na),.w_data(nwd),
 .r_v(nr),.r_rdy(1'b0),.r_addr(nra),.rd_v(1'b0),.rd_data(256'd0),
 .done_v(ndone),.done_v__c1(dc1),.done_v__c2(dc2),.done_tag(nt),.busy(nb),.n_sectors(nns),.n_beats(nnb));
 task mismatch(input string reason);
  $display("ENGINE_COLD_MISMATCH cycle=%0d epoch=%0d di=%0d pi=%0d writes=%0d MUT_CLOCK=%0d reason=%s",cyc,epochs,di,pi,writes,mut_clock,reason);
  $fatal(1,"engine pair differs");
 endtask
 always @(negedge clk)rnd<={rnd[30:0],rnd[31]^rnd[21]^rnd[1]^rnd[0]};
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(!rst_n)begin
   di<=0;pi<=0;writes<=0;dones<=0;idle<=0;first_desc<=0;
   for(i=0;i<NS;i=i+1)seen[i]=0;
  end else if(run)begin
   checks<=checks+1;
   if({gd,gi,gw,gr,gdone,gb,gns,gnb}!=={nd,ni,nw,nr,ndone,nb,nns,nnb})mismatch("control/counters");
   if(gw&&(ga!==na||gwd!==nwd))mismatch("write valid address/data");
   if(gr&&gra!==nra)mismatch("read valid address");
   if(gdone&&(gt!==nt||!dc1||!dc2))mismatch("completion/copies");
   if(!first_desc&&gd&&!dv)mismatch("extra idle on first legal descriptor-ready edge");
   if(dv&&gd)begin
    di<=di+1;
    if(!first_desc)begin
     first_desc<=1;
     $display("ENGINE_FIRST_ACCEPT epoch=%0d release_cycle=%0d accepted_cycle=%0d ready_wait_edges=%0d postrelease_burnin_edges=0",epochs,release_cycle,cyc,cyc-release_cycle);
    end
   end
   if(iv&&gi)pi<=pi+1;
   if(gdone)dones<=dones+1;
   if(gw&&ready)begin
    writes<=writes+1;found=-1;
    for(i=0;i<NS;i=i+1)if(golden[i][31:0]==ga)found=i;
    if(found<0)mismatch("RTL output absent from independent native golden");
    else begin
     if(gwd!==golden[found][287:32])mismatch("RTL output differs from native golden");
     seen[found]=1;
    end
   end
   if(di==ND&&pi==NP&&!gb)idle<=idle+1;else idle<=0;
   if(epochs==1&&idle==8)begin
    if(writes!=NS||dones!=ND)mismatch("final transaction accounting");
    for(i=0;i<NS;i=i+1)if(!seen[i])mismatch("missing golden sector");
    $display("ENGINE_COLD_SAMPLE PASS checks=%0d writes=%0d descriptors=%0d occupied_resets=%0d MUT_CLOCK=%0d independent_random_init=1 SRAM_no_init=1",checks,writes,dones,epochs,mut_clock);
    $finish;
   end
  end
  if(cyc>200000)mismatch("functional completion timeout");
 end
 initial begin
  if(!$value$plusargs("MUT_CLOCK=%d",mut_clock))mut_clock=0;
  $readmemh("desc.mem",desc);$readmemh("pay.mem",pay);$readmemh("native.mem",golden);
  repeat(8)@(negedge clk);release_cycle=cyc;rst_n=1;run=1;
  $display("ENGINE_RESET_RELEASE epoch=%0d reset_held_edges=8 cycle=%0d",epochs,cyc);
  wait(pi>=64&&gb);@(negedge clk);
  $display("ENGINE_OCCUPIED_RESET cycle=%0d busy=%0d accepted_beats=%0d writes=%0d",cyc,gb,pi,writes);
  if(!gb)$fatal(1,"reset was not occupied");
  rst_n=0;run=0;epochs=1;
  repeat(8)@(negedge clk);release_cycle=cyc;rst_n=1;run=1;
  $display("ENGINE_RESET_RELEASE epoch=%0d reset_held_edges=8 cycle=%0d",epochs,cyc);
 end
endmodule
