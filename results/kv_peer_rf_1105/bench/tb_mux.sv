// DIE-KV-69 11-04: per-channel word stream and fault check for qkd_host_peer_root_mux (REF) and _pl2.
// Each output channel is checked against the generator: no drop, duplicate, reorder or corruption, under random
// valid/ready. BAD=1 non-shape physical RX word, BAD=2 bad coordinator TX header: fault must rise.
module tb_mux;
 parameter int N=20000;
 reg ck=0,por_n=0; always #5 ck=~ck;
 int bad=0; int seed=1;
 longint unsigned r=64'h9E3779B97F4A7C15;
 function automatic longint unsigned mix(input longint unsigned x);
  x^=x>>30;x*=64'hBF58476D1CE4E5B9;x^=x>>27;x*=64'h94D049BB133111EB;return x^(x>>31);
 endfunction
 function automatic bit[511:0] raw(input int ch,input int idx);
  bit[511:0] w; for(int i=0;i<8;i++)w[i*64+:64]=mix(64'(ch)*64'd1000003+64'(idx)*64'd257+64'(i)+64'd1);return w;
 endfunction
 function automatic int src_of(input int idx);return 1+int'(mix(64'(idx)+64'd77)%7);endfunction
 function automatic bit[511:0] w_rx(input int idx);
  bit[511:0] w=raw(10,idx);w[7]=0;w[13:11]=0;w[10:8]=3'(src_of(idx));
  if(bad==1&&idx==100)w[11]=1;
  return w;
 endfunction
 function automatic bit[511:0] w_loc(input int idx);return raw(11,idx);endfunction
 function automatic bit[511:0] w_tx(input int rk,input int idx);
  bit[511:0] w=raw(rk,idx);
  if(rk!=0)begin w[7]=1;w[10:8]=0;w[13:11]=3'(rk);if(bad==2&&rk==3&&idx==100)w[8]=1;end
  return w;
 endfunction
 reg prx_v=0;int prx_i=0; wire prx_r; reg ltx_v=0;int ltx_i=0; wire ltx_r;
 reg[7:0] ctx_v=0;int ctx_i[8]; wire[7:0] ctx_r;
 wire ptx_v;wire[511:0] ptx_d;reg ptx_r=0; wire lrx_v;wire[511:0] lrx_d;reg lrx_r=0;
 wire[7:0] crx_v;wire[4095:0] crx_d;reg[7:0] crx_r=0; wire fault;
 reg[4095:0] ctx_d; always @* for(int k=0;k<8;k++)ctx_d[k*512+:512]=w_tx(k,ctx_i[k]);
 wire[511:0] prx_d=w_rx(prx_i); wire[511:0] ltx_d=w_loc(ltx_i);
`ifdef USE_R3
 qkd_host_peer_root_mux_r3
`elsif USE_PL2
 qkd_host_peer_root_mux_pl2
`else
 qkd_host_peer_root_mux
`endif
  dut(.ck(ck),.por_n(por_n),.physical_rx_valid(prx_v),.physical_rx_data(prx_d),.physical_rx_ready(prx_r),
  .physical_tx_valid(ptx_v),.physical_tx_data(ptx_d),.physical_tx_ready(ptx_r),
  .local_tx_valid(ltx_v),.local_tx_data(ltx_d),.local_tx_ready(ltx_r),
  .local_rx_valid(lrx_v),.local_rx_data(lrx_d),.local_rx_ready(lrx_r),
  .coordinator_rx_valid(crx_v),.coordinator_rx_data(crx_d),.coordinator_rx_ready(crx_r),
  .coordinator_tx_valid(ctx_v),.coordinator_tx_data(ctx_d),.coordinator_tx_ready(ctx_r),.fault(fault));
 int ptx_c[8];int lrx_c=0;int crx_c0=0;int crx_i[8];int errs=0;int cyc=0;int fin=0;
 function automatic int next_rx(input int rk,input int from);int i=from;while(i<N&&src_of(i)!=rk)i++;return i;endfunction
 initial begin
  for(int k=0;k<8;k++)begin ctx_i[k]=0;ptx_c[k]=0;crx_i[k]=0;end
  void'($value$plusargs("BAD=%d",bad));void'($value$plusargs("SEED=%d",seed));
  r=mix(64'(seed));
  repeat(5)@(posedge ck);por_n<=1;
 end
 always @(posedge ck) if(por_n)begin
  // drivers: valid held until ready. mode band changes the pressure over time
  automatic longint unsigned q=mix(r);
  automatic int m=(cyc>>12)&3;
  automatic bit[7:0] gate=(m==0)?8'hFF:(m==1)?q[7:0]:(m==2)?q[7:0]|q[15:8]:q[7:0]&q[15:8];
  r<=q;cyc<=cyc+1;
  if(prx_v&&prx_r)begin prx_i<=prx_i+1;prx_v<=q[16]&&prx_i+1<N;end else if(!prx_v)prx_v<=q[16]&&prx_i<N;
  if(ltx_v&&ltx_r)begin ltx_i<=ltx_i+1;ltx_v<=q[17]&&ltx_i+1<N;end else if(!ltx_v)ltx_v<=q[17]&&ltx_i<N;
  for(int k=0;k<8;k++)begin
   if(ctx_v[k]&&ctx_r[k])begin ctx_i[k]<=ctx_i[k]+1;ctx_v[k]<=q[18+k]&&ctx_i[k]+1<N;end
   else if(!ctx_v[k])ctx_v[k]<=q[18+k]&&ctx_i[k]<N;
  end
  ptx_r<=gate[0];lrx_r<=gate[1];crx_r<=m==0?8'hFF:(q[33:26]|q[41:34]);
  // checkers
  if(!fault)begin
  if(ptx_v&&ptx_r)begin automatic int rk=int'(ptx_d[13:11]);
   if(ptx_d!==w_tx(rk,ptx_c[rk]))begin errs++;$display("ERR ptx rank %0d word %0d",rk,ptx_c[rk]);end ptx_c[rk]<=ptx_c[rk]+1;end
  if(lrx_v&&lrx_r)begin if(lrx_d!==w_tx(0,lrx_c))begin errs++;$display("ERR lrx %0d",lrx_c);end lrx_c<=lrx_c+1;end
  if(crx_v[0]&&crx_r[0])begin if(crx_d[0+:512]!==w_loc(crx_c0))begin errs++;$display("ERR crx0 %0d",crx_c0);end crx_c0<=crx_c0+1;end
  for(int k=1;k<8;k++)if(crx_v[k]&&crx_r[k])begin automatic int e=next_rx(k,crx_i[k]);
   if(crx_d[k*512+:512]!==w_rx(e))begin errs++;$display("ERR crx rank %0d word %0d",k,e);end crx_i[k]<=e+1;end
  end
  if(errs>5)begin $display("FAIL errs=%0d",errs);$finish;end
  if(bad!=0&&fault)begin $display("FAULT_RAISED bad=%0d cyc=%0d errs=%0d",bad,cyc,errs);if(errs==0)$display("PASS");else $display("FAIL");$finish;end
  if(bad==0&&prx_i==N&&ltx_i==N&&ctx_i[0]==N&&ctx_i[1]==N&&ctx_i[2]==N&&ctx_i[3]==N&&ctx_i[4]==N&&ctx_i[5]==N&&ctx_i[6]==N&&ctx_i[7]==N)fin<=fin+1;
  if(fin==200)begin automatic int tot=0;automatic bit ok=1;
   for(int k=1;k<8;k++)begin tot+=ptx_c[k];if(ptx_c[k]!=N)ok=0;if(next_rx(k,crx_i[k])!=N)ok=0;end
   if(lrx_c!=N||crx_c0!=N)ok=0;
   $display("DONE cyc=%0d ptx=%0d lrx=%0d crx0=%0d errs=%0d fault=%0d",cyc,tot,lrx_c,crx_c0,errs,fault);
   if(ok&&errs==0&&!fault)$display("PASS");else $display("FAIL");$finish;end
  if(cyc>40*N)begin $display("FAIL timeout prx=%0d ltx=%0d fault=%0d",prx_i,ltx_i,fault);$finish;end
 end
endmodule
