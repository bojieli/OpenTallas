`timescale 1ns/1ps
// MU-ADOPT-KV 10-19 (R6 write side through the wired role): the KV die writer role of qkd_kvs_ctl under OT_KV_MU=1,
// qkd_kv_static_writer_native_mu (closed qkd_kv_static_writer_native + qkd_kv_mu_wrow; user = the TAG epoch[1:0]),
// against the plain closed writer (today) in lockstep, plus the wrapper at MU 0 (must be wires).  Stimulus: 4 users x 36
// layers x NPOS positions of KVN words (4 words a position, VMAP 1), epoch = {seq14, user2} of the user's stage.
// Checked on every edge:
//   * MU 0 wrapper == plain writer on every output (bit-identical);
//   * MU 1: every output equal to the plain writer except es lane row[9:8] (es[q*288+265 +: 2]) and expected_address
//     row[9:8] ([19:18]), which must equal the word's user; no fault;
//   * every sector write inverted independently -> {user (row >> 8), layer (row[7:0] - 64), position, K/V, dim} exact
//     with the raw bytes; a 2^27-bit occupancy map {stack, PC, bank, column, row[9:0]} proves the 4 users' writes are
//     unique (no alias).
module tb_mu_kv_writer_rows;
 parameter integer VMAP=1;
 integer NPOS=8192;
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg v=0,slot=0;reg[10:0]tag;reg[511:0]data;
 reg[58:0]id,cid;reg[1:0]gen,cgen,ix;
 `define WR_OUTS(p) wire[1151:0]p``es;wire[19:0]p``pc,p``epc;wire[1:0]p``st,p``est,p``g,p``eg;wire[58:0]p``i,p``ei;wire[3:0]p``ev; \
   wire[28:0]p``xa;wire p``f;wire[7:0]p``fc;
 `define WR_CONN(p) .ck(ck),.rst_n(rst_n),.word_valid(v),.word_tag(tag),.word_data(data),.word_identity(id),.word_generation(gen), \
   .compiled_word_slot(slot),.compiled_word_index(ix),.compiled_identity(cid),.compiled_generation(cgen),.es(p``es),.dest_pc(p``pc), \
   .dest_stack(p``st),.identity(p``i),.generation(p``g),.expected_valid(p``ev),.expected_pc(p``epc),.expected_stack(p``est), \
   .expected_identity(p``ei),.expected_generation(p``eg),.expected_address(p``xa),.fault(p``f),.fault_code(p``fc)
 `define WR_VEC(p) {p``es,p``pc,p``epc,p``st,p``est,p``g,p``eg,p``i,p``ei,p``ev,p``xa,p``f,p``fc}
 `WR_OUTS(r_) `WR_OUTS(z_) `WR_OUTS(m_)
 qkd_kv_static_writer_native #(.VMAP(VMAP)) u_ref (`WR_CONN(r_));               // today
 qkd_kv_static_writer_native_mu #(.VMAP(VMAP),.MU(0)) u_z (`WR_CONN(z_));      // MU 0: wires
 qkd_kv_static_writer_native_mu #(.VMAP(VMAP),.MU(1)) u_m (`WR_CONN(m_));      // MU 1
 wire [1151:0] es_allow; genvar gq;
 generate for (gq=0;gq<4;gq=gq+1) begin:g_al assign es_allow[gq*288+:288] = 288'b11 << 265; end endgenerate
 integer cases=0,writes=0,errors=0,nalias=0,layer,pos,i,b,q,j,r,ba,co,e,dim,kind,tok,logical_e,uu,ru,cur_user=0;   // ru: checker-only
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
  if(`WR_VEC(z_)!==`WR_VEC(r_))begin errors=errors+1;if(errors<5)$display("MU0 wrapper not wires");end
  if(((m_es^r_es)&~es_allow)!=0||{m_pc,m_epc,m_st,m_est,m_g,m_eg,m_i,m_ei,m_ev,m_f,m_fc}!=={r_pc,r_epc,r_st,r_est,r_g,r_eg,r_i,r_ei,r_ev,r_f,r_fc}||
     {m_xa[28:20],m_xa[17:0]}!=={r_xa[28:20],r_xa[17:0]})begin errors=errors+1;if(errors<5)$display("MU1 differs outside row[9:8]");end
  if(m_f)begin errors=errors+1;if(errors<5)$display("MU1 fault code %h",m_fc);end
  for(q=0;q<4;q=q+1)begin
   if(m_es[q*288])begin
    writes=writes+1;r=m_es[q*288+257+:19];co=m_es[q*288+276+:5];ba=m_es[q*288+281+:5];
    j=(ba>>2)*128+co*4+(ba&3);kind=j>>9;
    logical_e=ungroup(m_pc[q*5+:5]>>2);
    if(VMAP!=0&&kind!=0)
     tok=(((j>>3)&15)<<9)|(m_st<<7)|(((j>>7)&1)<<6)|((logical_e>>1)<<4)|((j&7)<<1)|(logical_e&1);
    else
     tok=(((j>>3)&15)<<9)|(m_st<<7)|(((j>>7)&1)<<6)|((j&7)<<3)|logical_e;
    ru=r>>8;
    if((r&255)<64||(r&255)>=100||r>=1024||{19'(r),5'(ba),5'(co)}!==m_xa)errors=errors+1;
    if(tok!==m_ei[18:6]||(r&255)-64!==m_ei[42:37]-1||ru!==m_ei[44:43]||ru!==cur_user)begin
     errors=errors+1;if(errors<5)$display("inverse u%0d/%0d r%0d tok%0d/%0d",ru,cur_user,r,tok,m_ei[18:6]);end
    for(b=0;b<32;b=b+1)begin
     dim=(m_pc[q*5+:5]&3)*32+b;
     if(m_es[q*288+1+b*8+:8]!==bytecode(ru,(r&255)-64,tok,kind,dim))errors=errors+1;
    end
    key={m_st,m_pc[q*5+:5],5'(ba),5'(co),10'(r)};
    if(occ[key])begin nalias=nalias+1;if(nalias<5)$display("ALIAS key %h user%0d row%0d",key,ru,r);end
    occ[key]=1;
   end
  end
 end
 integer k,seq=0;
 initial begin
 void'($value$plusargs("NPOS=%d",NPOS));
 tag=0;data=0;id=0;cid=0;gen=0;cgen=0;ix=0;
 for(k=0;k<(1<<27);k=k+1)occ[k]=0;
 repeat(3)step();rst_n=1;repeat(4)step();
 // users interleaved stage by stage (op-level interleave): layer-major, user-minor
 for(layer=0;layer<36;layer=layer+1)for(uu=0;uu<4;uu=uu+1)begin
  seq=seq+1;
  for(pos=0;pos<NPOS;pos=pos+1)begin
   cid={14'(seq),2'(uu),6'(layer+1),18'(pos+13),13'(pos),6'd0};cgen=(pos+layer)%4;
   for(i=0;i<4;i=i+1)begin
    ix=i;slot=1;v=1;id=cid;gen=cgen;
    tag={3'b010,5'd0,1'(i/2),1'b0,1'(i%2)};
    for(e=0;e<64;e=e+1)data[e*8+:8]=bytecode(uu,layer,pos,i/2,(i%2)*64+e);
    step();if(i==0)cur_user=uu;
   end
   slot=0;v=0;repeat(3)step();cases=cases+1;
   if(errors||nalias)$fatal(1,"FAIL user%0d layer%0d pos%0d errors%0d nalias%0d fault%0d code%h",uu,layer,pos,errors,nalias,m_f,m_fc);
  end
 end
 if(writes!=4*36*NPOS*8)$fatal(1,"FAIL write count %0d",writes);
 $display("PASS MU_KV_WRITE_ROWS users4 x layers36 x positions%0d (stage-interleaved) words%0d sectors%0d unique alias0 inverse{user,layer,pos,kind,dim}+raw exact; MU1 == plain writer outside row[9:8]; MU0 wrapper == plain writer",NPOS,cases*4,writes);$finish;
 end
endmodule
