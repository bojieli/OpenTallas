`timescale 1ns/1ps
// Independent inverse address/data oracle, not a copy of sec_of forward logic.
module tb_qkd_kv_static_writer_native;
 parameter integer MUT=0, BAD=0, STRICT=0; // STRICT=1: a mutant is judged as a production run (must FAIL)
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg v=0,slot=0;reg[10:0]tag;reg[511:0]data;
 reg[58:0]id,cid;reg[1:0]gen,cgen,ix;
 wire[1151:0]es;wire[19:0]pc,epc;wire[1:0]stack,estack,og,eg;
 wire[58:0]oi,ei;wire[1023:0]mask;wire[3:0]native,ev;
 wire[28:0]ea;wire[317:0]ctx;wire[60:0]eci;wire fault;wire[7:0]fc;
 qkd_kv_static_writer #(.MUT(MUT))dut(.ck(ck),.rst_n(rst_n),.word_valid(v),.word_tag(tag),.word_data(data),.word_identity(id),.word_generation(gen),.compiled_word_slot(slot),.compiled_word_index(ix),.compiled_identity(cid),.compiled_generation(cgen),.es(es),.dest_pc(pc),.dest_stack(stack),.identity(oi),.generation(og),.write_mask(mask),.native_kv(native),.expected_valid(ev),.expected_pc(epc),.expected_stack(estack),.expected_identity(ei),.expected_generation(eg),.expected_address(ea),.es_context(ctx),.es_expected_identity(eci),.fault(fault),.fault_code(fc));
 wire [1151:0] n_es;
 wire [19:0] n_pc;
 wire [19:0] n_epc;
 wire [1:0] n_stack;
 wire [1:0] n_estack;
 wire [1:0] n_og;
 wire [1:0] n_eg;
 wire [58:0] n_oi;
 wire [58:0] n_ei;
 wire [3:0] n_ev;
 wire [28:0] n_ea;
 wire n_fault;
 wire [7:0] n_fc;
 qkd_kv_static_writer_native #(.MUT(MUT)) native_dut(.ck(ck),.rst_n(rst_n),.word_valid(v),.word_tag(tag),.word_data(data),.word_identity(id),.word_generation(gen),.compiled_word_slot(slot),.compiled_word_index(ix),.compiled_identity(cid),.compiled_generation(cgen),.es(n_es),.dest_pc(n_pc),.dest_stack(n_stack),.identity(n_oi),.generation(n_og),.expected_valid(n_ev),.expected_pc(n_epc),.expected_stack(n_estack),.expected_identity(n_ei),.expected_generation(n_eg),.expected_address(n_ea),.fault(n_fault),.fault_code(n_fc));
 always @(negedge ck)if(rst_n)begin
 if({es,pc,epc,stack,estack,og,eg,oi,ei,ev,ea,fault,fc} !== {n_es,n_pc,n_epc,n_stack,n_estack,n_og,n_eg,n_oi,n_ei,n_ev,n_ea,n_fault,n_fc})$fatal(1,"physical wrapper face mismatch");
 if(|ev)begin
 if(mask!=={1024{1'b1}} || native!==4'hf || ctx!=={1'b1,oi,og,{256{1'b1}}} || eci!=={ei,eg})$fatal(1,"omitted semantic field mismatch");
 end
 end

 integer cases=0,writes=0,errors=0,layer,pos,i,b,q,j,r,ba,co,e,dim,kind,tok,logical_e;
 function automatic[7:0]bytecode(input integer l,t,k,d);
  bytecode=(l*37+t*13+k*91+d*17+(t>>8))%256;
 endfunction
 function automatic integer ungroup(input integer g);
 case(g)0:ungroup=4;1:ungroup=5;2:ungroup=0;3:ungroup=1;4:ungroup=2;5:ungroup=3;6:ungroup=6;7:ungroup=7;endcase
 endfunction
 task step;begin @(negedge ck);end endtask
 always @(negedge ck)if(rst_n)begin
  for(q=0;q<4;q=q+1)begin
   if(es[q*288]!==ev[q])errors=errors+1;
   if(es[q*288])begin
    writes=writes+1;r=es[q*288+257+:19];co=es[q*288+276+:5];ba=es[q*288+281+:5];
    // Invert actual controller bank/column packing back to canonical sector j.
    j=(ba>>2)*128+co*4+(ba&3);kind=j>>9;
    logical_e=ungroup(pc[q*5+:5]>>2);
    tok=(((j>>3)&15)<<9)|(stack<<7)|(((j>>7)&1)<<6)|((j&7)<<3)|logical_e;
    if((j>>8&1)!=0||r<64||r>=100||oi!==ei||og!==eg||stack!==estack||pc[q*5+:5]!==epc[q*5+:5]||{19'(r),5'(ba),5'(co)}!==ea||mask[q*256+:256]!=={256{1'b1}})errors=errors+1;
    if(tok!==ei[18:6]||r-64!==ei[42:37]-1)errors=errors+1;
    for(b=0;b<32;b=b+1)begin
     dim=(pc[q*5+:5]&3)*32+b;
     if(es[q*288+1+b*8+:8]!==bytecode(r-64,tok,kind,dim))errors=errors+1;
    end
   end
  end
 end
 initial begin
 tag=0;data=0;id=0;cid=0;gen=0;cgen=0;ix=0;
 repeat(3)step();rst_n=1;
 // Physical master releases reset through ot_rst_relay (2 sync + 1 tree = 3 edges): the compiled boot
 // schedule issues the first word slot no earlier than that (idle edges are still face-compared above).
 repeat(3)step();
 // All36 stages and all8192 positions exercise every stack, bank, col, lane.
 for(layer=0;layer<36;layer=layer+1)for(pos=0;pos<8192;pos=pos+1)begin
  cid={16'(layer+9),6'(layer+1),18'(pos+13),13'(pos),6'd0};cgen=(pos+layer)%4;
  for(i=0;i<4;i=i+1)begin
   ix=i;slot=1;v=!(BAD==1&&i==1);id=cid ^ (((BAD==2&&i==1)||(BAD==3&&i==0))?59'd1:59'd0);gen=cgen;
   tag={3'b010,5'd0,1'(i/2),1'b0,1'(i%2)};
   for(e=0;e<64;e=e+1)data[e*8+:8]=bytecode(layer,pos,i/2,(i%2)*64+e);
   step();
  end
  slot=0;v=0;repeat(3)step();cases=cases+1;
  if((MUT!=0||BAD!=0)&&!STRICT)begin
   if((MUT!=0&&errors==0)||(BAD!=0&&(!fault||errors==0)))$fatal(1,"FAIL mutant escaped errors%0d fault%0d",errors,fault);
   $display("OBSERVED_FAIL MUT%0d BAD%0d errors%0d fault%0d",MUT,BAD,errors,fault);$finish;
  end
  if(errors||fault)$fatal(1,"FAIL layer%0d pos%0d errors%0d fault%0d code%h",layer,pos,errors,fault,fc);
 end
 if(writes!=2359296)$fatal(1,"FAIL write count %0d",writes);
 $display("PASS all36stages/all8192positions identities%0d sectors%0d inverse-map/raw256/fullmask/TAG59/gen2/exactslots",cases,writes);$finish;
 end
endmodule
