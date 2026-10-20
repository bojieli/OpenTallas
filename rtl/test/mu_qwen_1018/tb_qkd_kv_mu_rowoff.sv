`timescale 1ns/1ps
// MU-QWEN-HOST 10-18: per-user KV rows on the KV die.  The production writer qkd_kv_static_writer (VMAP 1, the PV16
// layout of the die) feeds qkd_kv_mu_wrow (MU 1); every physical sector write of 4 users x 36 layers x 8,192 positions
// is inverted independently (bank/column/PC/stack -> token, row -> {user, layer}) and must name exactly the written
// {user, layer, position, K/V, dim} with the raw bytes; a 2^27-bit occupancy map {stack, PC, bank, column, row[9:0]}
// proves no two writes nalias (every sector written exactly once).  The read leaf qkd_kv_mu_rrow must map each user's
// KV descriptor (op 0 / 3) to the same row the writer wrote, keep row[7:0] (the closed read-return tag: row[7:0] - 64
// = layer), and leave embedding rows (24,427+), go and write commands unchanged.  MU 0 must be wires.
module tb_qkd_kv_mu_rowoff;
 parameter integer VMAP=1, NPOS=8192;
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg v=0,slot=0;reg[10:0]tag;reg[511:0]data;
 reg[58:0]id,cid;reg[1:0]gen,cgen,ix;reg[1:0]user=0;
 wire[1151:0]es_w,es;wire[19:0]pc,epc;wire[1:0]stack,estack,og,eg;
 wire[58:0]oi,ei;wire[1023:0]mask;wire[3:0]native,ev;
 wire[28:0]ea_w,ea;wire[317:0]ctx;wire[60:0]eci;wire fault,rfault;wire[7:0]fc;
 qkd_kv_static_writer #(.VMAP(VMAP))u_w(.ck(ck),.rst_n(rst_n),.word_valid(v),.word_tag(tag),.word_data(data),.word_identity(id),.word_generation(gen),.compiled_word_slot(slot),.compiled_word_index(ix),.compiled_identity(cid),.compiled_generation(cgen),.es(es_w),.dest_pc(pc),.dest_stack(stack),.identity(oi),.generation(og),.write_mask(mask),.native_kv(native),.expected_valid(ev),.expected_pc(epc),.expected_stack(estack),.expected_identity(ei),.expected_generation(eg),.expected_address(ea_w),.es_context(ctx),.es_expected_identity(eci),.fault(fault),.fault_code(fc));
 // user is held for the stage; the writer's es/expected outputs of a stage leave within the stage's 7 edges
 reg [1:0] user_q;always @(posedge ck)user_q<=user;
 qkd_kv_mu_wrow #(.MU(1))u_mu(.user(user_q),.es_i(es_w),.xa_i(ea_w),.es_o(es),.xa_o(ea),.range_fault(rfault));
 wire[1151:0]es0;wire[28:0]ea0;wire rf0;
 qkd_kv_mu_wrow #(.MU(0))u_mu0(.user(user_q),.es_i(es_w),.xa_i(ea_w),.es_o(es0),.xa_o(ea0),.range_fault(rf0));
 reg[42:0]cmd;wire[42:0]rcmd,rcmd0;
 qkd_kv_mu_rrow #(.MU(1))u_rr(.user(user),.cmd_i(cmd),.cmd_o(rcmd));
 qkd_kv_mu_rrow #(.MU(0))u_rr0(.user(user),.cmd_i(cmd),.cmd_o(rcmd0));
 integer cases=0,writes=0,errors=0,nalias=0,layer,pos,i,b,q,j,r,ba,co,e,dim,kind,tok,logical_e,uu,rows_ok=0,reads=0;
 reg occ[0:(1<<27)-1];
 reg[26:0] key;
 function automatic[7:0]bytecode(input integer u,l,t,k,d);
  bytecode=(u*101+l*37+t*13+k*91+d*17+(t>>8))%256;
 endfunction
 function automatic integer ungroup(input integer g);
 case(g)0:ungroup=4;1:ungroup=5;2:ungroup=0;3:ungroup=1;4:ungroup=2;5:ungroup=3;6:ungroup=6;7:ungroup=7;endcase
 endfunction
 task step;begin @(negedge ck);end endtask
 always @(negedge ck)if(rst_n)begin
  if(es0!==es_w||ea0!==ea_w||rf0!==0||rcmd0!==cmd)begin errors=errors+1;$display("MU0 not wires");end
  if(rfault)begin errors=errors+1;$display("range fault");end
  for(q=0;q<4;q=q+1)begin
   if(es[q*288]!==ev[q])errors=errors+1;
   if(es[q*288])begin
    writes=writes+1;r=es[q*288+257+:19];co=es[q*288+276+:5];ba=es[q*288+281+:5];
    if(es[q*288+:257]!==es_w[q*288+:257]||es[q*288+276+:12]!==es_w[q*288+276+:12])errors=errors+1; // only row[9:8] may differ
    j=(ba>>2)*128+co*4+(ba&3);kind=j>>9;
    logical_e=ungroup(pc[q*5+:5]>>2);
    if(VMAP!=0&&kind!=0)
     tok=(((j>>3)&15)<<9)|(stack<<7)|(((j>>7)&1)<<6)|((logical_e>>1)<<4)|((j&7)<<1)|(logical_e&1);
    else
     tok=(((j>>3)&15)<<9)|(stack<<7)|(((j>>7)&1)<<6)|((j&7)<<3)|logical_e;
    uu=r>>8;
    if((j>>8&1)!=0||(r&255)<64||(r&255)>=100||r>=1024||oi!==ei||og!==eg||stack!==estack||pc[q*5+:5]!==epc[q*5+:5]||{19'(r),5'(ba),5'(co)}!==ea||mask[q*256+:256]!=={256{1'b1}})errors=errors+1;
    if(tok!==ei[18:6]||(r&255)-64!==ei[42:37]-1||uu!==user_q)begin errors=errors+1;if(errors<5)$display("inverse u%0d/%0d r%0d tok%0d/%0d",uu,user_q,r,tok,ei[18:6]);end
    for(b=0;b<32;b=b+1)begin
     dim=(pc[q*5+:5]&3)*32+b;
     if(es[q*288+1+b*8+:8]!==bytecode(uu,(r&255)-64,tok,kind,dim))errors=errors+1;
    end
    key={stack,pc[q*5+:5],5'(ba),5'(co),10'(r)};
    if(occ[key])begin nalias=nalias+1;if(nalias<5)$display("ALIAS key %h user%0d row%0d",key,uu,r);end
    occ[key]=1;
   end
  end
 end
 integer k,op,nl;reg[18:0]rw;
 initial begin
 tag=0;data=0;id=0;cid=0;gen=0;cgen=0;ix=0;cmd=0;
 for(k=0;k<(1<<27);k=k+1)occ[k]=0;
 repeat(3)step();rst_n=1;
 for(uu=0;uu<4;uu=uu+1)begin
  user=uu;
  for(layer=0;layer<36;layer=layer+1)for(pos=0;pos<NPOS;pos=pos+1)begin
   cid={16'(layer+9),6'(layer+1),18'(pos+13),13'(pos),6'd0};cgen=(pos+layer)%4;
   for(i=0;i<4;i=i+1)begin
    ix=i;slot=1;v=1;id=cid;gen=cgen;
    tag={3'b010,5'd0,1'(i/2),1'b0,1'(i%2)};
    for(e=0;e<64;e=e+1)data[e*8+:8]=bytecode(uu,layer,pos,i/2,(i%2)*64+e);
    step();
   end
   slot=0;v=0;repeat(3)step();cases=cases+1;
   if(errors||fault||nalias)$fatal(1,"FAIL user%0d layer%0d pos%0d errors%0d nalias%0d fault%0d code%h",uu,layer,pos,errors,nalias,fault,fc);
  end
 end
 if(writes!=4*36*NPOS*8)  // 8 sectors (K+V, 128 dims x 1 B each, 32 B a sector) a position
 $fatal(1,"FAIL write count %0d",writes);
 // read side: every user's KV descriptor row equals the row its writes used; tag and non-KV commands unchanged
 for(uu=0;uu<4;uu=uu+1)begin user=uu;
  for(layer=0;layer<36;layer=layer+1)for(op=0;op<4;op=op+1)for(nl=0;nl<3;nl=nl+1)begin
   rw=(nl==2)?19'(24427+layer*7):19'(64+layer);
   cmd={10'(layer*3+nl),2'(op),11'(5+layer),rw,1'(nl)};#0.1;
   reads=reads+1;
   if((op==0||op==3)&&nl!=2)begin
    if(rcmd[19:1]!==19'(64+layer+256*uu)||rcmd[8:1]-8'd64!==8'(layer)||{rcmd[42:20],rcmd[0]}!=={cmd[42:20],cmd[0]})
     $fatal(1,"FAIL read map user%0d layer%0d op%0d row %0d",uu,layer,op,rcmd[19:1]);
    rows_ok=rows_ok+1;
   end else if(rcmd!==cmd)$fatal(1,"FAIL non-KV command changed user%0d layer%0d op%0d nl%0d",uu,layer,op,nl);
   if(rcmd0!==cmd)$fatal(1,"FAIL MU0 read not wires");
  end
 end
 $display("PASS users4 x stages36 x positions%0d identities%0d sectors%0d unique-addresses%0d alias0 inverse{user,layer,pos,kind,dim}+raw256 exact; read rows %0d/%0d commands, tag row[7:0]-64=layer, embedding/go/write unchanged; MU0 wires",NPOS,cases,writes,writes,rows_ok,reads);$finish;
 end
endmodule
