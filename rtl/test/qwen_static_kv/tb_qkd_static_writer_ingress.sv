`timescale 1ns/1ps
// An independent clock/word/data driver composes the candidate programme with
// the actual native physical writer. The programme never supplies its payload
// driver, identity oracle, or expected event times. No hierarchical accesses.
module tb_qkd_static_writer_ingress;
 parameter integer MUT=0,BAD=0,IMUT=0,CASE=0,WMUT=0;
 reg ck=0;always #1 ck=~ck;
 reg rst_n=0,cfg_we=0,start=0;reg[7:0]cfg_addr=0;reg[5:0]stage=1;reg[63:0]cfg_data=0;
 reg[15:0]epoch=0;reg[17:0]token=0;reg[12:0]position=0;reg[1:0]generation=0;
 wire slot,kvslot,configured,active,done,pfault;wire[1:0]ix,cgen;wire[58:0]cid;wire[31:0]cycle;
 wire[3:0]pev;wire[19:0]ppc;wire[1:0]pst,pg;wire[58:0]pi;wire[28:0]pa;
 qkd_kv_native_programme #(.MUT(MUT),.VMAP(1))p(.ck(ck),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .start(start),.stage(stage),.epoch(epoch),.token(token),.position(position),.generation(generation),
 .compiled_word_slot(slot),.compiled_word_index(ix),.compiled_identity(cid),.compiled_generation(cgen),.kvn_word_slot(kvslot),
 .configured(configured),.active(active),.done(done),.fault(pfault),.cycle(cycle),
 .expected_valid(pev),.expected_pc(ppc),.expected_stack(pst),.expected_identity(pi),.expected_generation(pg),.expected_address(pa));
 reg wv=0;reg[10:0]wt=0;reg[511:0]wd=0;reg[58:0]wi=0;reg[1:0]wg=0;
 wire[1151:0]es;wire[19:0]pc,epc;wire[1:0]stack,estack,og,eg;wire[58:0]oi,ei;wire[3:0]ev;wire[28:0]ea;wire wf;wire[7:0]fc;
 qkd_kv_static_writer_native #(.VMAP(1),.MUT(WMUT)) w(.ck(ck),.rst_n(rst_n),.word_valid(wv),.word_tag(wt),.word_data(wd),.word_identity(wi),.word_generation(wg),
 .compiled_word_slot(slot),.compiled_word_index(ix),.compiled_identity(cid),.compiled_generation(cgen),
 .es(es),.dest_pc(pc),.dest_stack(stack),.identity(oi),.generation(og),.expected_valid(ev),.expected_pc(epc),.expected_stack(estack),
 .expected_identity(ei),.expected_generation(eg),.expected_address(ea),.fault(wf),.fault_code(fc));
 integer cfg_s=0,cfg_g=2,layer_count=36,token_count=2;
 reg native_mode=0,ownership_valid=1,verify_native=0;
 wire[19:0]actual_pc=pc^((CASE==1)?20'd1:20'd0);
 wire[58:0]actual_id=oi^((CASE==2)?(59'd1<<19):59'd0);
 wire[1151:0]ge,oe;wire[317:0]gc;wire[1271:0]oc;
 wire[3:0]gv,ov,pmf;wire[60:0]gi;wire[243:0]odi;wire[28:0]ga;wire[115:0]oda;
 wire[19:0]gp,odp;wire[1:0]gs;wire[7:0]ods;wire gf,group_idle;wire[3:0]pc_idle;
 reg[1151:0]host_input=0;reg[1043:0]ctrl_return=0;reg[3:0]c_v=0,c_w=0;
 wire[1043:0]host_return;wire[3:0]host_cv,host_cw;
 qkd_static_writer_group #(.NATIVE_FULL_SECTOR(1),.MUT(IMUT))g(.ck(ck),.rst_n(rst_n),.cfg_stack(2'(cfg_s)),.cfg_group(3'(cfg_g)),
 .writer_es(es),.writer_pc(actual_pc),.writer_stack(stack),.writer_identity(actual_id),.writer_generation(og),
 .programme_valid(pev),.programme_pc(ppc),.programme_stack(pst),.programme_identity(pi),.programme_generation(pg),.programme_address(pa),
 .pc_es(ge),.pc_context(gc),.pc_expected_valid(gv),.pc_expected_identity(gi),.pc_expected_address(ga),.pc_expected_pc(gp),.pc_expected_stack(gs),.fault(gf),.idle(group_idle));
 genvar mq;
 generate for(mq=0;mq<4;mq=mq+1)begin:g_mux
 qkd_static_writer_pc_mux m(.ck(ck),.rst_n(rst_n),.native_mode(native_mode),.ownership_valid(ownership_valid),
 .native_es(ge[288*mq+:288]),.native_context(gc),.native_expected_valid(gv[mq]),.native_expected_identity(gi),.native_expected_address(ga),.native_expected_pc(gp[5*mq+:5]),.native_expected_stack(gs),
 .host_es(host_input[288*mq+:288]),.ctrl_er(ctrl_return[261*mq+:261]),.ctrl_completion_v(c_v[mq]),.ctrl_completion_we(c_w[mq]),
 .es(oe[288*mq+:288]),.es_context(oc[318*mq+:318]),.es_expected_valid(ov[mq]),.es_expected_identity(odi[61*mq+:61]),.es_expected_address(oda[29*mq+:29]),.es_expected_pc(odp[5*mq+:5]),.es_expected_stack(ods[2*mq+:2]),
 .host_er(host_return[261*mq+:261]),.host_completion_v(host_cv[mq]),.host_completion_we(host_cw[mq]),.fault(pmf[mq]),.idle(pc_idle[mq]));
 end endgenerate
 // Independent transport scoreboard: actual input payload/context and independent
 // programme descriptors are sampled separately, then each moves exactly3edges.
 reg[1151:0]re[0:2];reg[60:0]ri[0:2],rpi[0:2];reg[3:0]rv[0:2];
 reg[28:0]ra[0:2];reg[19:0]rp[0:2];reg[1:0]rs[0:2];
 integer transported=0,expected_transfers=0;
 always @(posedge ck)begin
  for(integer d=2;d>0;d=d-1)begin re[d]<=re[d-1];ri[d]<=ri[d-1];rpi[d]<=rpi[d-1];rv[d]<=rv[d-1];ra[d]<=ra[d-1];rp[d]<=rp[d-1];rs[d]<=rs[d-1];end
  re[0]<=es;ri[0]<={actual_id,og};rpi[0]<={pi,pg};ra[0]<=pa;rp[0]<=ppc;rs[0]<=pst;
  for(integer q0=0;q0<4;q0=q0+1)rv[0][q0]<=rst_n&&pev[q0]&&pst==cfg_s&&ppc[5*q0+:5]=={3'(cfg_g),2'(q0)};
 end
 always @(negedge ck)if(verify_native)begin
  if(ov!==rv[2])$fatal(1,"distribution expected slot moved actual%h expected%h",ov,rv[2]);
  for(integer q0=0;q0<4;q0=q0+1)begin
   if(oe[288*q0]!==rv[2][q0])$fatal(1,"actual reserved payload missing or wrong target");
   if(ov[q0])begin
    expected_transfers=expected_transfers+1;
    if(odi[61*q0+:61]!==rpi[2]||oda[29*q0+:29]!==ra[2]||odp[5*q0+:5]!==rp[2][5*q0+:5]||ods[2*q0+:2]!==rs[2])$fatal(1,"independent programme expectation changed");
    if(oc[318*q0+:318]!=={1'b1,ri[2],{256{1'b1}}})$fatal(1,"actual context/mask changed or echoed");
    if(oe[288*q0+:288]!==re[2][288*q0+:288])$fatal(1,"actual writer payload changed");
    transported=transported+1;
   end else if(oc[318*q0+317])$fatal(1,"native context leaked outside reserved slot");
  end
  if(host_return!=0||host_cv!=0||host_cw!=0)$fatal(1,"native return leaked to HOST credit/completion arbiter");
 end
 always @(negedge ck)if(|ev)begin
  if(w.u_writer.write_mask!=={1024{1'b1}}||w.u_writer.native_kv!==4'hf)$fatal(1,"native full-mask semantic contract violated");
 end
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
     recovered_pos=kind?((((sector>>3)&15)<<9)|(stack<<7)|(((sector>>7)&1)<<6)|((logical_group>>1)<<4)|((sector&7)<<1)|(logical_group&1)):
      ((((sector>>3)&15)<<9)|(stack<<7)|(((sector>>7)&1)<<6)|((sector&7)<<3)|logical_group);
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
  if($value$plusargs("S=%d",cfg_s))begin end
  if($value$plusargs("G=%d",cfg_g))begin end
  if($value$plusargs("L=%d",layer_count))begin end
  if($value$plusargs("N=%d",token_count))begin end
  rst_n=0;step();rst_n=1;repeat(5)step();boot_image();
  if(BAD==1)begin if(!pfault||configured)$fatal(1,"bad boot escaped");$display("PASS refused malformed ascending boot");$finish;end
  if(!configured||pfault)$fatal(1,"configuration failed");
  // One boot and one reset for the complete two-token/all36 sequence.
  native_mode=1;repeat(4)step();verify_native=1;
  // Native read-return/credit/completion events must never enter the legacy
  // HOST arbiter while native programme owns this controller face.
  ctrl_return={4{{1'b0,1'b1,258'd7,1'b1}}};c_v=4'hf;c_w=4'hf;
  for(token_no=0;token_no<token_count;token_no=token_no+1)for(l=0;l<layer_count;l=l+1)begin
   for(cohort=0;cohort<135;cohort=cohort+1)begin
    if(cohort<128)pos=(cfg_s<<7)|cohort;else case(cohort)
     128:pos=128;129:pos=511;130:pos=512;131:pos=4095;132:pos=4096;133:pos=8190;134:pos=8191;
    endcase
    transaction(l,pos,(cohort+token_no)%4,(cohort==15)?65535:token_no+9,151935-cohort-token_no);
    if(MUT!=0||BAD!=0)begin
     if(errors==0&&!wf&&!pfault)$fatal(1,"negative control escaped");
     $display("PASS observed negative MUT%0d BAD%0d errors%0d writer_fault%0d",MUT,BAD,errors,wf);$finish;
    end
    if(errors||wf||pfault||(CASE==0&&gf)||(|pmf))$fatal(1,"FAIL layer%0d pos%0d errors%0d wf%0d fc%h pf%0d",l,pos,errors,wf,fc,pfault);
   end
  end
  if(CASE!=0&&!gf)$fatal(1,"bad actual metadata escaped fixed-slot distributor");
  if(sectors!=8*layer_count*135*token_count||slots!=4*layer_count*135*token_count)$fatal(1,"production word counts");
  verify_native=0;ctrl_return=0;c_v=0;c_w=0;repeat(4)step();native_mode=0;repeat(3)step();
  if(group_idle!==!gf||pc_idle!==4'hf)$fatal(1,"actual ingress did not drain after flush");
  // HOST exceptional traffic has native-context0 and no native expectation.
  host_input[287:0]={287'h12345,1'b1};ctrl_return[260:0]={1'b0,1'b1,258'h321,1'b1};c_v=1;c_w=1;step();
  if(oe[287:0]!==host_input[287:0]||oc[317]||ov!=0||host_return[260:0]!==ctrl_return[260:0]||host_cv!=1||host_cw!=1)$fatal(1,"HOST exception ownership/context/return contract");
  // Invalid handover is exceptional fault-stop, not a wait/ready path.
  ownership_valid=0;step();
  if(oe[0]||host_return!=0||host_cv!=0||ov!=0||!pmf[0])$fatal(1,"invalid ownership did not fault-stop both paths");
  host_input=0;ctrl_return=0;c_v=0;c_w=0;repeat(3)step();
  if(pc_idle[0])$fatal(1,"faulted mux reported quiet");
  $display("WRITER_INGRESS PASS CASE%0d IMUT%0d layers%0d tokens%0d stack%0d group%0d cases%0d slots%0d sectors%0d transported%0d expected%0d added_edges3 groupfault%0d",CASE,IMUT,layer_count,token_count,cfg_s,cfg_g,cases,slots,sectors,transported,expected_transfers,gf);$finish;
 end
endmodule
