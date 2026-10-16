`timescale 1ns/1ps
// Q-ATTN-RATE 2026-10-16: PV16 V service composition = 8 x qkd_pv16_vport (actual RTL, KV die) feeding the actual
// ot_qwen_tp8_pv_wide_pair.  The HBM image is laid out by the PV16 V placement (qkd_kv_static_writer VMAP=1, proven
// row-by-row by tb_qkd_kv_static_writer VMAP=1's independent inverse oracle): row t -> stack t[8:7], group
// {t[5:4],t[0]}, quarter Q (dims 32Q..), PC ordinal {t[12:9],t[6],t[3:1]}.  Every PC return ring is a FIFO filled in
// the controller's v_consumer_order (ascending ordinal; the rows t < T are exactly an ordinal prefix) and is only
// ever POPPED AT ITS HEAD at a compiled slot -- no random access by t.  The compiled schedule uses only the pair's
// static request slots and the cycle parity (sel = q[0]); tags are carried for checking only.
// MODE: steady | legacy_order (rings streamed in raw sector order, not v_consumer_order: must FAIL).  VMUT: qkd_pv16_vport MUT.
module tb_qwen_pv16_vservice;
 parameter integer PAIR=0, MUT=0, VMUT=0, RL=19, LEAF_RESET_PIN=0, CTL_RESET_PIN=0;
 reg clk=0,rst_n=0;always #1 clk=~clk;
 reg start=0;integer CTX;string vec,mode;
 wire [7:0] in_valid;wire [8191:0] in_v;reg [511:0] in_e=0;wire [111:0] in_t;reg [127:0] in_epoch={8{16'd23}};
 wire [7:0] req_valid;wire [111:0] req_t;wire out_valid,fault,busy;wire [16383:0] out_leaf;wire [15:0] out_epoch,out_age;
 ot_qwen_tp8_pv_wide_pair #(.PAIR(PAIR),.CTL_RESET_PIN(CTL_RESET_PIN),.LEAF_RESET_PIN(LEAF_RESET_PIN),.FIRST_INPUT_AGE(RL+1),.MUT(MUT)) u(
  .clk(clk),.rst_n(rst_n),.start(start),
  .col_clk({33{clk}}),.context_len(14'(CTX)),.epoch(16'd23),.in_valid(in_valid),.in_v(in_v),.in_e(in_e),.in_t(in_t),
  .in_epoch(in_epoch),.req_valid(req_valid),.req_t(req_t),.out_valid(out_valid),.out_leaf(out_leaf),.out_epoch(out_epoch),
  .fault(fault),.busy(busy),.out_age(out_age));
 // ---- KV die: 8 V ports (stack PAIR lanes 0-3, stack PAIR+2 lanes 0-3) ----
 reg [7:0] p_slot=0,p_sel=0;reg [8*8-1:0] p_v=0;reg [8*8*14-1:0] p_t=0;reg [8*8*256-1:0] p_d=0;
 wire [7:0] vfault;
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:g_port
  qkd_pv16_vport #(.MUT(VMUT)) u_vp(.ck(clk),.rst_n(rst_n),
   .slot(p_slot[g]),.sel(p_sel[g]),
   .in_v0(p_v[8*g+:4]),.in_t0(p_t[8*14*g+:4*14]),.in_d0(p_d[8*256*g+:4*256]),
   .in_v1(p_v[8*g+4+:4]),.in_t1(p_t[8*14*g+4*14+:4*14]),.in_d1(p_d[8*256*g+4*256+:4*256]),
   .out_valid(in_valid[g]),.out_t(in_t[14*g+:14]),.out_v_lo(in_v[1024*g+:512]),.out_v_hi(in_v[1024*g+512+:512]),.fault(vfault[g]));
 end endgenerate
 reg [1023:0] vr[0:8191];reg [63:0] er[0:8191];reg [31:0] gold[0:511];
 // rings: [port][group bit][quarter] FIFO of row ids in ordinal order (quarter rings of one group hold the same rows)
 integer ring[0:7][0:1][0:255],rlen[0:7][0:1],rhead[0:7][0:1][0:3];
 integer due[0:7][0:63],dsel[0:7][0:63],wp[0:7],rp[0:7];
 integer cyc=0,scyc=-1,ocyc=-1,q0=-1,errors=0,words=0,nreq=0,pops=0,i,k,n,t,s,o,gq,qq,ln,ord;reg[7:0] seen;
 always @(posedge clk)cyc<=cyc+1;
 function automatic integer ordinal(input integer t, input integer legacy);
  // legacy: the sector j itself, {t[6],t[12:9],low3} (half-major) -- a valid bijection read WITHOUT the controller's
  // v_consumer_order: the stream order the pair cannot consume (must FAIL)
  ordinal=legacy ? (((t>>6)&1)<<7)|(((t>>9)&15)<<3)|((t>>1)&7) : (((t>>9)&15)<<4)|(((t>>6)&1)<<3)|((t>>1)&7);
 endfunction
 initial begin
  if(!$value$plusargs("VEC=%s",vec))$fatal(1,"+VEC");
  if(!$value$plusargs("CTX=%d",CTX))$fatal(1,"+CTX");
  if(!$value$plusargs("MODE=%s",mode))mode="steady";
  for(i=0;i<3;i=i+1)begin
   n=$fopen({vec,(i==0)?"/v.hex":(i==1)?"/e.hex":"/gold.hex"},"r");
   if(n==0)$fatal(1,"missing vector file in %0s",vec);
   $fclose(n);
  end
  $readmemh({vec,"/v.hex"},vr);$readmemh({vec,"/e.hex"},er);$readmemh({vec,"/gold.hex"},gold);
  // fill: for each of this pair's 64 PCs, rows t < T in ordinal order (the controller's v_consumer_order stream)
  for(k=0;k<8;k=k+1)for(gq=0;gq<2;gq=gq+1)begin
   rlen[k][gq]=0;for(qq=0;qq<4;qq=qq+1)rhead[k][gq][qq]=0;
   for(o=0;o<256;o=o+1)ring[k][gq][o]=-1;
  end
  for(t=0;t<CTX;t=t+1)begin
   s=(t>>7)&3;if((s&1)==PAIR)begin
    k=4*(s>>1)+((t>>4)&3);gq=t&1;ord=ordinal(t,mode=="legacy_order");
    if(ring[k][gq][ord]!=-1)$fatal(1,"placement collision t=%0d",t);
    ring[k][gq][ord]=t;
   end
  end
  for(k=0;k<8;k=k+1)for(gq=0;gq<2;gq=gq+1)begin   // compact to the stream (ascending ordinal)
   ln=0;for(o=0;o<256;o=o+1)if(ring[k][gq][o]!=-1)begin ring[k][gq][ln]=ring[k][gq][o];ln=ln+1;end
   rlen[k][gq]=ln;
  end
  for(k=0;k<8;k=k+1)begin wp[k]=0;rp[k]=0;end
  repeat(5)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);
  start=1;scyc=cyc;@(negedge clk);start=0;
 end
 // compiled pops: the request slot X of port k (static, a pure function of T) -> pop group {k&3, q[0]} at X+RL-2
 always @(negedge clk)if(rst_n)begin
  p_slot=0;p_v=0;
  for(k=0;k<8;k=k+1)if(rp[k]!=wp[k]&&due[k][rp[k]%64]==cyc)begin
   gq=dsel[k][rp[k]%64];rp[k]=rp[k]+1;p_slot[k]=1;p_sel[k]=gq[0];
   for(qq=0;qq<4;qq=qq+1)begin
    if(rhead[k][gq][qq]>=rlen[k][gq])begin $display("RING_EMPTY port%0d g%0d q%0d",k,gq,qq);errors=errors+1;end
    else begin
     n=ring[k][gq][rhead[k][gq][qq]];rhead[k][gq][qq]=rhead[k][gq][qq]+1;pops=pops+1;
     p_v[8*k+4*gq+qq]=1;p_t[8*14*k+14*(4*gq+qq)+:14]=14'(n);p_d[8*256*k+256*(4*gq+qq)+:256]=vr[n][256*qq+:256];
    end
   end
  end
  // e is the ASTK service (not under test): presented with the port's word
  #0.25;for(k=0;k<8;k=k+1)if(in_valid[k])in_e[64*k+:64]=er[in_t[14*k+:14]];
  #0.25;
  if(req_valid!=0&&q0<0)q0=cyc;
  for(k=0;k<8;k=k+1)if(req_valid[k])begin
   due[k][wp[k]%64]=cyc+RL-2;dsel[k][wp[k]%64]=(cyc-q0)&1;wp[k]=wp[k]+1;nreq=nreq+1;
  end
 end
 always @(posedge clk)if(rst_n&&out_valid)begin
  ocyc=cyc;
  for(i=0;i<512;i=i+1)begin
   if(out_leaf[32*i+:32]!==gold[i])begin if(errors<6)$display("MISMATCH %0d got %08h want %08h",i,out_leaf[32*i+:32],gold[i]);errors=errors+1;end
   words=words+1;
  end
 end
 initial begin
  #4000;
  for(k=0;k<8;k=k+1)for(gq=0;gq<2;gq=gq+1)for(qq=0;qq<4;qq=qq+1)
   if(rhead[k][gq][qq]!=rlen[k][gq])begin if(errors<6)$display("RING_LEFT port%0d g%0d q%0d %0d/%0d",k,gq,qq,rhead[k][gq][qq],rlen[k][gq]);errors=errors+1;end
  $display("PV16_VSERVICE %s T=%0d pair=%0d mode=%s vmut=%0d words=%0d errors=%0d fault=%0d vport_fault=%b out_age=%0d got_age=%0d rows=%0d pops=%0d",
   (errors==0&&words==512&&!fault&&vfault==0&&ocyc-scyc==out_age)?"PASS":"FAIL",CTX,PAIR,mode,VMUT,words,errors,fault,vfault,out_age,ocyc-scyc,nreq,pops);
  $finish;
 end
endmodule
