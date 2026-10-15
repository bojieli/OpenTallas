`timescale 1ns/1ps
// An independent clock/word/data driver composes the candidate programme with
// the actual native physical writer. The programme never supplies its payload
// driver, identity oracle, or expected event times. No hierarchical accesses.
module tb_qkd_kv_native_programme;
 parameter integer MUT=0,BAD=0;
 reg ck=0;always #1 ck=~ck;
 reg rst_n=0,cfg_we=0,start=0;reg[7:0]cfg_addr=0;reg[5:0]stage=1;reg[63:0]cfg_data=0;
 reg[15:0]epoch=0;reg[17:0]token=0;reg[12:0]position=0;reg[1:0]generation=0;
 wire slot,kvslot,configured,active,done,pfault;wire[1:0]ix,cgen;wire[58:0]cid;wire[31:0]cycle;
 wire[3:0]pev;wire[19:0]ppc;wire[1:0]pst,pg;wire[58:0]pi;wire[28:0]pa;
 qkd_kv_native_programme #(.MUT(MUT))p(.ck(ck),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .start(start),.stage(stage),.epoch(epoch),.token(token),.position(position),.generation(generation),
 .compiled_word_slot(slot),.compiled_word_index(ix),.compiled_identity(cid),.compiled_generation(cgen),.kvn_word_slot(kvslot),
 .configured(configured),.active(active),.done(done),.fault(pfault),.cycle(cycle),
 .expected_valid(pev),.expected_pc(ppc),.expected_stack(pst),.expected_identity(pi),.expected_generation(pg),.expected_address(pa));
 reg wv=0;reg[10:0]wt=0;reg[511:0]wd=0;reg[58:0]wi=0;reg[1:0]wg=0;
 wire[1151:0]es;wire[19:0]pc,epc;wire[1:0]stack,estack,og,eg;wire[58:0]oi,ei;wire[3:0]ev;wire[28:0]ea;wire wf;wire[7:0]fc;
 qkd_kv_static_writer_native w(.ck(ck),.rst_n(rst_n),.word_valid(wv),.word_tag(wt),.word_data(wd),.word_identity(wi),.word_generation(wg),
 .compiled_word_slot(slot),.compiled_word_index(ix),.compiled_identity(cid),.compiled_generation(cgen),
 .es(es),.dest_pc(pc),.dest_stack(stack),.identity(oi),.generation(og),.expected_valid(ev),.expected_pc(epc),.expected_stack(estack),
 .expected_identity(ei),.expected_generation(eg),.expected_address(ea),.fault(wf),.fault_code(fc));
 reg[63:0]boot[0:180];reg[58:0]root_id;reg[1:0]root_gen;
 integer i,j,k,n,l,t,pos,cohort,token_no,word_index,errors=0,sectors=0,cases=0,slots=0;
 integer bank,col,row,sector,kind,logical_group,recovered_pos,dim,b;
 reg[28:0]expected_addr;
 function automatic[7:0]bytecode(input integer layer,position_i,kind_i,dim_i);
  bytecode=(layer*37+position_i*13+kind_i*91+dim_i*17+(position_i>>8))%256;
 endfunction
 function automatic integer ungroup(input integer physical_group);
  case(physical_group)0:ungroup=4;1:ungroup=5;2:ungroup=0;3:ungroup=1;4:ungroup=2;5:ungroup=3;6:ungroup=6;7:ungroup=7;endcase
 endfunction
 task step;begin @(negedge ck);end endtask
 task verify;
  begin
   if(pev!==ev)errors=errors+1;
   if(|ev)begin
    if({pi,pg,ppc,pst,pa}!={ei,eg,epc,estack,ea})errors=errors+1;
    if(ei!==root_id||eg!==root_gen)errors=errors+1;
   end
   for(j=0;j<4;j=j+1)begin
    if(es[j*288]!==ev[j])errors=errors+1;
    if(es[j*288])begin
     sectors=sectors+1;
     row=es[j*288+257+:19];col=es[j*288+276+:5];bank=es[j*288+281+:5];
     sector=(bank>>2)*128+col*4+(bank&3);kind=sector>>9;
     logical_group=ungroup(pc[j*5+:5]>>2);
     recovered_pos=(((sector>>3)&15)<<9)|(stack<<7)|(((sector>>7)&1)<<6)|((sector&7)<<3)|logical_group;
     if(recovered_pos!==root_id[18:6]||row!==64+root_id[42:37]-1||oi!==root_id||og!==root_gen)errors=errors+1;
     for(b=0;b<32;b=b+1)begin
      dim=(pc[j*5+:5]&3)*32+b;
      if(es[j*288+1+b*8+:8]!==bytecode(row-64,recovered_pos,kind,dim))errors=errors+1;
     end
    end
   end
  end
 endtask
 task boot_image;
  begin
   for(i=0;i<181;i=i+1)begin
    cfg_we=1;cfg_addr=i;cfg_data=boot[i];
    if(BAD==1&&i==2)cfg_addr=3;
    step();
   end
   cfg_we=0;step(); // flush the exceptional boot pin-capture edge
  end
 endtask
 task transaction(input integer layer_i,position_i,gen_i,epoch_i,token_i);
  begin
   epoch=epoch_i;token=token_i;position=position_i;generation=gen_i;stage=layer_i+1;
   root_id={16'(epoch_i),6'(layer_i+1),18'(token_i),13'(position_i),6'd0};root_gen=gen_i;
   start=1;step();start=0;
   // First edge captures the external request and its original roots.
   // Change input roots before internal accept to prove pin ownership.
   epoch=epoch+1;token=token+3;position=position+7;generation=generation+1;stage=(stage==36)?6'd1:stage+6'd1;
   if(active)$fatal(1,"external start bypassed pin capture");
   step();
   if(!active||cycle!=0)$fatal(1,"internal start capture latency mismatch");
   // Check interval 0 and every subsequent compiler cycle. Actual source word
   // valid/data arise from the independently loaded timeline, even if MUT
   // shifts a programme slot or flips its index/identity.
   for(t=0;t<=boot[5*layer_i+4][31:0]+3;t=t+1)begin
    wv=0;
    for(k=0;k<4;k=k+1)if(t==boot[5*layer_i+k][31:0])begin
     wv=1;wt={3'b010,5'd0,1'(k/2),1'b0,1'(k%2)};wi=root_id;wg=root_gen;
     if(BAD==2&&k==1)wv=0;
     if(BAD==3&&k==2)wi=wi^(59'd1<<19);
     for(n=0;n<64;n=n+1)wd[n*8+:8]=bytecode(layer_i,position_i,k/2,(k%2)*64+n);
    end
    if(slot)begin
     slots=slots+1;word_index=-1;
     for(k=0;k<4;k=k+1)if(t==boot[5*layer_i+k][31:0])word_index=k;
     if(word_index<0||ix!==word_index[1:0]||cid!==root_id||cgen!==root_gen||kvslot!==slot)errors=errors+1;
    end
    if(active&&cycle!==t)errors=errors+1;
    step();verify();
    // Inputs deliberately change during a transaction: captured roots must
    // remain stable until the next accepted start.
    epoch=epoch+1;token=token+3;position=position+7;generation=generation+1;stage=(stage==36)?6'd1:stage+6'd1;
   end
   wv=0;cases=cases+1;
  end
 endtask
 initial begin
  $readmemh("boot.hex",boot);
  rst_n=0;step();rst_n=1;repeat(5)step();boot_image();
  if(BAD==1)begin if(!pfault||configured)$fatal(1,"bad boot escaped");$display("PASS refused malformed ascending boot");$finish;end
  if(!configured||pfault)$fatal(1,"configuration failed");
  // One boot and one reset for the complete two-token/all36 sequence.
  for(token_no=0;token_no<2;token_no=token_no+1)for(l=0;l<36;l=l+1)begin
   for(cohort=0;cohort<16;cohort=cohort+1)begin
    case(cohort)
     0:pos=0;1:pos=1;2:pos=7;3:pos=8;4:pos=31;5:pos=32;6:pos=63;7:pos=64;
     8:pos=127;9:pos=128;10:pos=511;11:pos=512;12:pos=4095;13:pos=4096;14:pos=8190;15:pos=8191;
    endcase
    transaction(l,pos,(cohort+token_no)%4,(cohort==15)?65535:token_no+9,151935-cohort-token_no);
    if(MUT!=0||BAD!=0)begin
     if(errors==0&&!wf&&!pfault)$fatal(1,"negative control escaped");
     $display("PASS observed negative MUT%0d BAD%0d errors%0d writer_fault%0d",MUT,BAD,errors,wf);$finish;
    end
    if(errors||wf||pfault)$fatal(1,"FAIL layer%0d pos%0d errors%0d wf%0d fc%h pf%0d",l,pos,errors,wf,fc,pfault);
   end
  end
  if(sectors!=9216||slots!=4608)$fatal(1,"wrong production counts sectors%0d slots%0d",sectors,slots);
  $display("PASS programme+native_writer all36 two_tokens boundary_positions single_boot_noreset_no_reconfigure cases%0d slots%0d sectors%0d noreset_roots TAG59 generation2 inverse_address raw_data",cases,slots,sectors);$finish;
 end
endmodule
