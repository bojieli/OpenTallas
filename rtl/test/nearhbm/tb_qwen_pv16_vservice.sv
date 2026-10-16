`timescale 1ns/1ps
// Q-ATTN-RATE 2026-10-16: PV16 V service composition = 8 x qkd_pv16_vport (actual RTL, KV die) feeding the actual
// ot_qwen_tp8_pv_wide_pair.  The HBM image is laid out by the PV16 V placement (qkd_kv_static_writer VMAP=1, proven
// row-by-row by tb_qkd_kv_static_writer VMAP=1's independent inverse oracle): row t -> stack t[8:7], group
// {t[5:4],t[0]}, quarter Q (dims 32Q..), PC ordinal {t[12:9],t[6],t[3:1]}.  Every PC return ring is a FIFO filled in
// the controller's v_consumer_order (ascending ordinal; the rows t < T are exactly an ordinal prefix) and is only
// ever POPPED AT ITS HEAD at a compiled slot -- no random access by t.  The compiled schedule uses only the pair's
// static request slots and the cycle parity (sel = q[0]); tags are carried for checking only.
// MODE: steady | legacy_order (rings streamed in raw sector order, not v_consumer_order: must FAIL).  VMUT: qkd_pv16_vport MUT.
// r4 port ABI: each vport side is a landing group's rsp face {valid, v, t, data quad} (the landing rowctl merges the four
// quarter PCs).  KINT=1 (default): every side that carries no V word on an edge carries a K response (v = 0, random
// tag/data) -- the K traffic sharing the landing rsp bus; the vport must ignore it (VMUT=3 ignores the flag: FAIL).
// r6: the port's word reaches the pair O edges later and carries the landing word's epoch (the pair checks it);
// RL = 4 + WP + O + DQ + RT, FIRST_INPUT_AGE = RL + 1.
// r5: the vport is the V issuer.  The pair's req_valid/req_t reach the port WP edges later (relay model); the port
// sends each V get to group {lane, t[0]}; the landing model answers a get RT edges after the port's vq register with
// the HEAD of that group's rings and checks the head is the requested row (a static stream never re-orders).
module tb_qwen_pv16_vservice;
 parameter integer PAIR=0, MUT=0, VMUT=0, KINT=1, WP=2, O=0, DQ=5, RT=8, LEAF_RESET_PIN=0, CTL_RESET_PIN=0;
 localparam integer RL=4+WP+O+DQ+RT;
 reg clk=0,rst_n=0;always #1 clk=~clk;
 reg start=0;integer CTX;string vec,mode;
 wire [7:0] in_valid;wire [8191:0] in_v;reg [511:0] in_e=0;wire [111:0] in_t;wire [127:0] in_epoch;
 wire [7:0] vo_valid;wire [8191:0] vo_v;wire [111:0] vo_t;wire [127:0] vo_e;
 wire [7:0] req_valid;wire [111:0] req_t;wire out_valid,fault,busy;wire [16383:0] out_leaf;wire [15:0] out_epoch,out_age;
 ot_qwen_tp8_pv_wide_pair #(.PAIR(PAIR),.CTL_RESET_PIN(CTL_RESET_PIN),.LEAF_RESET_PIN(LEAF_RESET_PIN),.FIRST_INPUT_AGE(RL+1),.MUT(MUT)) u(
  .clk(clk),.rst_n(rst_n),.start(start),
  .col_clk({33{clk}}),.context_len(14'(CTX)),.epoch(16'd23),.in_valid(in_valid),.in_v(in_v),.in_e(in_e),.in_t(in_t),
  .in_epoch(in_epoch),.req_valid(req_valid),.req_t(req_t),.out_valid(out_valid),.out_leaf(out_leaf),.out_epoch(out_epoch),
  .fault(fault),.busy(busy),.out_age(out_age));
 // ---- KV die: 8 V ports (stack PAIR lanes 0-3, stack PAIR+2 lanes 0-3) ----
 reg [7:0] p_prv=0;reg [111:0] p_prt=0;reg [15:0] p_val=0,p_vf=0;reg [16*16-1:0] p_e=0;reg [16*14-1:0] p_t=0;reg [16*1024-1:0] p_d=0;integer kw=0;
 wire [7:0] vfault;wire [15:0] vqv;wire [16*14-1:0] vqt;
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:g_port
  qkd_pv16_vport #(.MUT(VMUT),.DQ(DQ),.RT(RT)) u_vp(.ck(clk),.rst_n(rst_n),
   .pr_valid(p_prv[g]),.pr_t(p_prt[14*g+:14]),
   .vq0_valid(vqv[2*g]),.vq0_t(vqt[14*(2*g)+:14]),.vq1_valid(vqv[2*g+1]),.vq1_t(vqt[14*(2*g+1)+:14]),
   .in0_valid(p_val[2*g]),.in0_vflag(p_vf[2*g]),.in0_t(p_t[14*(2*g)+:14]),.in0_epoch(p_e[16*(2*g)+:16]),.in0_d(p_d[1024*(2*g)+:1024]),
   .in1_valid(p_val[2*g+1]),.in1_vflag(p_vf[2*g+1]),.in1_t(p_t[14*(2*g+1)+:14]),.in1_epoch(p_e[16*(2*g+1)+:16]),.in1_d(p_d[1024*(2*g+1)+:1024]),
   .out_valid(vo_valid[g]),.out_t(vo_t[14*g+:14]),.out_epoch(vo_e[16*g+:16]),.out_v_lo(vo_v[1024*g+:512]),.out_v_hi(vo_v[1024*g+512+:512]),.fault(vfault[g]));
  // port -> pair word relays (O edges)
  if(O==0)begin:g_o0 assign in_valid[g]=vo_valid[g];assign in_t[14*g+:14]=vo_t[14*g+:14];assign in_epoch[16*g+:16]=vo_e[16*g+:16];assign in_v[1024*g+:1024]=vo_v[1024*g+:1024];end
  else begin:g_o
   reg [1054:0] ch[0:O-1];
   always @(posedge clk)begin ch[0]<={vo_valid[g],vo_t[14*g+:14],vo_e[16*g+:16],vo_v[1024*g+:1024]};for(integer z=1;z<O;z=z+1)ch[z]<=ch[z-1];end
   assign {in_valid[g],in_t[14*g+:14],in_epoch[16*g+:16],in_v[1024*g+:1024]}=ch[O-1];
  end
 end endgenerate
 reg [1023:0] vr[0:8191];reg [63:0] er[0:8191];reg [31:0] gold[0:511];
 // rings: [port][group bit][quarter] FIFO of row ids in ordinal order (quarter rings of one group hold the same rows)
 integer ring[0:7][0:1][0:255],rlen[0:7][0:1],rhead[0:7][0:1][0:3];
 integer rdue[0:15][0:63],rtag[0:15][0:63],rwp[0:15],rrp[0:15];reg [7:0] hv[0:63];reg [111:0] ht[0:63];
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
  for(k=0;k<16;k=k+1)begin rwp[k]=0;rrp[k]=0;end for(k=0;k<64;k=k+1)hv[k]=0;
  repeat(5)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);
  start=1;scyc=cyc;@(negedge clk);start=0;
 end
 // landing model: a get seen on side i of port k (= 2k+i) at the vq register of cycle c answers in cycle c+RT with the head of
 // group {lane, i}'s four quarter rings (merged by the landing rowctl); the head must be the requested row
 always @(negedge clk)if(rst_n)begin
  p_val=0;p_vf=0;
  for(i=0;i<16;i=i+1)if(rrp[i]!=rwp[i]&&rdue[i][rrp[i]%64]==cyc)begin
   k=i>>1;gq=i&1;n=rtag[i][rrp[i]%64];rrp[i]=rrp[i]+1;p_val[i]=1;p_vf[i]=1;p_t[14*i+:14]=14'(n);p_e[16*i+:16]=16'd23;
   for(qq=0;qq<4;qq=qq+1)begin
    if(rhead[k][gq][qq]>=rlen[k][gq])begin $display("RING_EMPTY port%0d g%0d q%0d",k,gq,qq);errors=errors+1;end
    else begin
     o=ring[k][gq][rhead[k][gq][qq]];rhead[k][gq][qq]=rhead[k][gq][qq]+1;pops=pops+1;
     if(o!=n)begin if(errors<6)$display("ORDER port%0d g%0d asked t%0d ring head t%0d",k,gq,n,o);errors=errors+1;end
     p_d[1024*i+256*qq+:256]=vr[o][256*qq+:256];
    end
   end
  end
  if(KINT)for(i=0;i<16;i=i+1)if(!p_val[i])begin   // K responses on every idle side
   p_val[i]=1;p_vf[i]=0;p_t[14*i+:14]=14'($urandom);p_e[16*i+:16]=16'($urandom);for(qq=0;qq<32;qq=qq+1)p_d[1024*i+32*qq+:32]=$urandom;kw=kw+1;
  end
  // e is the ASTK service (not under test): presented with the port's word
  #0.25;for(k=0;k<8;k=k+1)if(in_valid[k])in_e[64*k+:64]=er[in_t[14*k+:14]];
  #0.25;
  if(req_valid!=0&&q0<0)q0=cyc;
  for(k=0;k<8;k=k+1)if(req_valid[k])nreq=nreq+1;
  // pair -> port request relays (WP edges)
  hv[cyc%64]=req_valid;ht[cyc%64]=req_t;
  if(cyc>=WP)begin p_prv=hv[(cyc-WP)%64];p_prt=ht[(cyc-WP)%64];end else p_prv=0;
  // the ports' V gets (vq registers of this cycle) -> landing answers
  for(i=0;i<16;i=i+1)if(vqv[i])begin rdue[i][rwp[i]%64]=cyc+RT;rtag[i][rwp[i]%64]=vqt[14*i+:14];rwp[i]=rwp[i]+1;end
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
  $display("PV16_VSERVICE %s T=%0d pair=%0d mode=%s vmut=%0d words=%0d errors=%0d fault=%0d vport_fault=%b out_age=%0d got_age=%0d rows=%0d pops=%0d kwords=%0d",
   (errors==0&&words==512&&!fault&&vfault==0&&ocyc-scyc==out_age)?"PASS":"FAIL",CTX,PAIR,mode,VMUT,words,errors,fault,vfault,out_age,ocyc-scyc,nreq,pops,kw);
  $finish;
 end
endmodule
