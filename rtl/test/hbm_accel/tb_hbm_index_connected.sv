`timescale 1ns/1ps
// Retained native operands feed the DUT; captured scores are comparator ONLY.
// Component provider/memory models expose actual handshakes and synchronous
// 1R1W latency. They do not qualify production ownership/CDC/physical SRAM.
module tb_hbm_index_connected;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0,start=0;wire start_ready,retained,fault,done;
 wire[31:0] held_job;wire[3:0] held_gen;wire[19:0] held_pos;wire[6:0] held_rank;
 wire rv,rrsp;reg read_ready=0,rsp_valid=0;wire[31:0] ra,rjob;wire[7:0] rt;wire[5:0] rw;
 wire[3:0] rgen;wire[19:0] rpos;wire[6:0] rrank;
 reg[1023:0] rsp_data=0;reg[7:0] rsp_tag=0;
 reg kv=0;wire kr;reg klast=0;reg[63:0] klv=0,kref=0,kkeep=0;
 reg[1279:0] kidx=0;reg[34815:0] kd=0;
 wire sv;reg sr=0;wire[3:0] slast;wire[63:0] slv;wire[1023:0] score;wire[1279:0] idx;
 reg downstream_drained=0;
 wire[3:0] cv,clast,cwe,cre;reg[3:0] cr=0;wire[7:0] clv;wire[127:0] cscore;wire[135:0] cblock;
 wire[39:0] cwa,cra;wire[271:0] cwd;reg[271:0] crd=0;wire crep,covf;wire[131:0] cstats;
 wire[3:0] ov,olast,mwe,mre;reg[3:0] ordy=0;
 wire[63:0] olv,oninf;wire[1023:0] oval;wire[1279:0] oid;
 wire[31:0] mwa,mra;wire[2367:0] mwd;reg[2367:0] mrd=0;wire rep,ovf;wire[107:0] stats;
 ot_hbm_accel_index_path #(.ENABLE(1),.SOURCE_VM_ENABLE(1)) dut(
 .clk(clk),.por_n(por_n),.start(start),.start_ready(start_ready),
 .source_job(32'hfeed0123),.source_gen(4'ha),.source_pos(20'd1048575),.source_rank(7'd0),
 .held_job(held_job),.held_gen(held_gen),.held_pos(held_pos),.held_rank(held_rank),
 .q_block_v(1'b0),.q_block_r(),.q_head(5'd0),.q_block(2'd0),.q_data(1024'd0),.q_weight(16'd0),
 .original_q_base(32'd64),.rotated_q_base(32'd4160),.scaled_weight_base(32'd8288),.source_tail_words(8'd64),
 .vm_read_v(rv),.vm_read_r(read_ready),.vm_read_addr(ra),.vm_read_tag(rt),.vm_read_words(rw),
 .vm_read_job(rjob),.vm_read_gen(rgen),.vm_read_pos(rpos),.vm_read_rank(rrank),
 .vm_rsp_v(rsp_valid),.vm_rsp_r(rrsp),.vm_rsp_data(rsp_data),.vm_rsp_tag(rsp_tag),
 .vm_rsp_job(32'hfeed0123),.vm_rsp_gen(4'ha),.vm_rsp_pos(20'd1048575),.vm_rsp_rank(7'd0),
 .k_v(kv),.k_r(kr),.k_last(klast),.k_lv(klv),.k_ref(kref),.k_keep(kkeep),.k_idx(kidx),.k_data(kd),
 .candidate_v(sv),.candidate_r(sr),.candidate_last(slast),.candidate_lv(slv),.candidate_score(score),.candidate_idx(idx),
 .candidate_drained(downstream_drained),.cand_out_v(cv),.cand_out_r(cr),.cand_out_last(clast),.cand_out_lv(clv),
 .cand_out_score(cscore),.cand_out_block(cblock),.cand_mem_we(cwe),.cand_mem_re(cre),.cand_mem_waddr(cwa),
 .cand_mem_raddr(cra),.cand_mem_wdata(cwd),.cand_mem_rdata(crd),.cand_replay_required(crep),.cand_overflow(covf),.cand_stats(cstats),
 .out_v(ov),.out_r(ordy),.out_last(olast),.out_lv(olv),.out_score(oval),.out_idx(oid),.out_ninf(oninf),
 .mem_we(mwe),.mem_re(mre),.mem_waddr(mwa),.mem_raddr(mra),.mem_wdata(mwd),.mem_rdata(mrd),
 .replay_required(rep),.overflow(ovf),.retained(retained),.fault(fault),.done(done),.selector_stats(stats));
 reg[31:0] initial_vm[0:262143],native_vm[0:262143];
 reg[566:0] keys[0:10943];reg[15:0] expected[0:10927];
 reg[591:0] topmem[0:1023];reg[67:0] candmem[0:4095];
 reg[10927:0] scored_seen=0;
 string original_path,native_path,keys_path,scores_path;
 integer cycles=0,reads=0,accepted=0,checked=0,topcount=0,candcount=0;
 integer topfd,candfd,beat=0,q,l,j,gid,ordinal,address,delay_edges=0;
 reg pending=0,accepted_key=0;reg[7:0] tag=0;reg[3:0] topdone=0,canddone=0;
 always @(posedge clk)begin
  cycles<=cycles+1;accepted_key<=kv&&kr;
  for(integer t=0;t<4;t=t+1)begin
   if(mwe[t])topmem[t*256+mwa[8*t+:8]]<=mwd[592*t+:592];
   if(mre[t])mrd[592*t+:592]<=topmem[t*256+mra[8*t+:8]];
   if(cwe[t])candmem[t*1024+cwa[10*t+:10]]<=cwd[68*t+:68];
   if(cre[t])crd[68*t+:68]<=candmem[t*1024+cra[10*t+:10]];
  end
  if(por_n)begin
   if(fault||rep||ovf||crep||covf)$fatal(1,"actual connected parent fault cycles=%0d accepted=%0d checked=%0d",cycles,accepted,checked);
   if(retained&&(held_job!=32'hfeed0123||held_gen!=4'ha||held_pos!=1048575||held_rank!=0))$fatal(1,"actual frame changed before drain");
   if(rv&&read_ready)begin
    if(pending||rw!=32||rjob!=held_job||rgen!=held_gen||rpos!=held_pos||rrank!=held_rank)$fatal(1,"VM pre-paid slot/frame mismatch");
    if(rt==128)begin if(ra!=8288)$fatal(1,"weight view mismatch");end
    else if(ra!=((rt[1]?4160:64)+(rt/4)*128+(rt%4)*32))$fatal(1,"query native view mismatch");
    pending<=1;address<=ra;tag<=rt;delay_edges<=2+(rt%3);reads<=reads+1;
   end
   if(pending&&delay_edges>0)delay_edges<=delay_edges-1;
   if(rsp_valid&&rrsp)pending<=0;
   if(kv&&kr)begin beat<=beat+1;accepted<=accepted+1;end
   if(sv&&sr)begin
    for(integer t=0;t<64;t=t+1)if(slv[t])begin
     gid=idx[20*t+:20];ordinal=(gid/8/96)*8+gid%8;
     if(gid/8%96||ordinal>=10928||scored_seen[ordinal]||score[16*t+:16]!==expected[ordinal])
      $fatal(1,"actual score mismatch gid=%0d ordinal=%0d got=%h expected=%h duplicate=%0d",gid,ordinal,score[16*t+:16],expected[ordinal],scored_seen[ordinal]);
     scored_seen[ordinal]=1;checked=checked+1;
    end
    if(checked%1024==0||slast!=0)$display("INDEX_PROGRESS edge=%0d input_beats=%0d checked=%0d",cycles,accepted,checked);
   end
   for(integer t=0;t<4;t=t+1)begin
    if(ov[t]&&ordy[t])begin
     if(olast[t])topdone[t]=1;
     for(integer z=0;z<16;z=z+1)if(olv[16*t+z])begin
      $fdisplay(topfd,"%0d %04h",oid[20*(16*t+z)+:20],oval[16*(16*t+z)+:16]);topcount=topcount+1;
     end
    end
    if(cv[t]&&cr[t])begin
     if(clast[t])canddone[t]=1;
     for(integer z=0;z<2;z=z+1)if(clv[2*t+z])begin
      $fdisplay(candfd,"%0d %04h",cblock[17*(2*t+z)+:17],cscore[16*(2*t+z)+:16]);candcount=candcount+1;
     end
    end
   end
   if(done)begin
    if(retained||pending||reads!=129||accepted!=171||checked!=10928||scored_seen!={10928{1'b1}}||topdone!=15||canddone!=15||topcount!=512||candcount!=1366)
     $fatal(1,"actual connected drain/count mismatch reads%0d accepted%0d checked%0d top%0d cand%0d",reads,accepted,checked,topcount,candcount);
    $fclose(topfd);$fclose(candfd);
    $display("PASS_HBM_NATIVE_CONNECTED_INDEX rank=0 context=1048576 VM_reads=%0d score_compares=%0d topk=%0d candidates=%0d edges=%0d final_gather_bound=0 physical_qualified=0",reads,checked,topcount,candcount,cycles);$finish;
   end
  end
 end
 always @(negedge clk)begin
  read_ready=por_n&&!pending&&cycles%5!=0;rsp_valid=pending&&delay_edges==0;rsp_tag=tag;
  if(pending)for(integer t=0;t<32;t=t+1)begin
   if(tag!=128&&!tag[1])begin
    if(initial_vm[address+t]!==native_vm[address+t])$fatal(1,"retained entering query overwritten");
    rsp_data[32*t+:32]=initial_vm[address+t];
   end else rsp_data[32*t+:32]=native_vm[address+t];
  end
  sr=por_n&&cycles%7!=0;
  for(integer t=0;t<4;t=t+1)begin ordy[t]=por_n&&(cycles+t)%5!=0;cr[t]=por_n&&(cycles+t)%6!=0;end
  downstream_drained=(&topdone)&&(&canddone);
  // Keep the source beat immutable until accepted, including producer bubbles.
  if(!kv||accepted_key)begin
   kv=por_n&&beat<171&&cycles%3!=0;klast=beat==170;
   if(beat<171)for(integer t=0;t<64;t=t+1)begin
    klv[t]=keys[beat*64+t][566];kidx[20*t+:20]=keys[beat*64+t][546+:20];
    kref[t]=keys[beat*64+t][545];kkeep[t]=keys[beat*64+t][544];kd[544*t+:544]=keys[beat*64+t][543:0];
   end
  end
 end
 initial begin
  if(!$value$plusargs("ORIGINAL=%s",original_path)||!$value$plusargs("NATIVE=%s",native_path)||!$value$plusargs("KEYS=%s",keys_path)||!$value$plusargs("SCORES=%s",scores_path))$fatal(1,"actual retained sources required");
  $readmemh(original_path,initial_vm);$readmemh(native_path,native_vm);$readmemh(keys_path,keys);$readmemh(scores_path,expected);
  topfd=$fopen("topk.txt","w");candfd=$fopen("candidates.txt","w");if(!topfd||!candfd)$fatal(1,"actual output files unavailable");
  repeat(3)@(negedge clk);por_n=1;
  while(!start_ready)@(negedge clk);
  start=1;@(negedge clk);start=0;
 end
endmodule
