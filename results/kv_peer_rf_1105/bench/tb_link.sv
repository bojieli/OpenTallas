// DIE-KV-70/PEER 11-04: per-channel stream, credit and fault bench for qkd_host_peer_link (REF) and _r3.
// RX: a credited sender mixes normal and class 9 frames; normal_rx and peer_rx each checked word by word.
// TX: credited normal source, valid/ready peer source; physical tx checked per channel, physical credits conserved.
// BAD=1 class 9 frame with reserved bits, BAD=2 RX past the class 9 credit, BAD=3 normal TX past its credit,
// BAD=4 surplus physical credit: fault must rise and no later word may be delivered.
module tb_link;
 parameter int N=30000; parameter int MUTP=0;
 reg ck=0,rst_n=0; always #5 ck=~ck;
 int bad=0,seed=1; longint unsigned r=64'h9E3779B97F4A7C15;
 function automatic longint unsigned mix(input longint unsigned x);
  x^=x>>30;x*=64'hBF58476D1CE4E5B9;x^=x>>27;x*=64'h94D049BB133111EB;return x^(x>>31);
 endfunction
 function automatic bit[527:0] raw(input int ch,input int idx);
  bit[527:0] w; for(int i=0;i<9;i++)w[i*64+:64]=mix(64'(ch)*64'd1000003+64'(idx)*64'd257+64'(i)+64'd1);return w;
 endfunction
 function automatic bit is_pk(input int idx);return mix(64'(idx)+64'd33)%3==0;endfunction
 function automatic bit[527:0] w_rx(input int idx);
  bit[527:0] w=raw(1,idx);
  if(is_pk(idx))begin w[527:524]=9;w[523:512]=0;end else if(w[527:524]==9)w[524]=0;
  return w;
 endfunction
 function automatic bit[527:0] w_ntx(input int idx);bit[527:0] w=raw(2,idx);if(w[527:524]==9)w[524]=0;return w;endfunction
 function automatic bit[511:0] w_ptx(input int idx);return raw(3,idx)[511:0];endfunction
 reg rx_v=0;reg[527:0]rx_d=0;wire rx_cr;int rx_i=0;int rx_credit=4;
 wire nrx_v;wire[527:0]nrx_d;reg nrx_cr=0; int nrx_held=0;
 wire prx_v;wire[511:0]prx_d;reg prx_r=0;
 reg ntx_v=0;reg[527:0]ntx_d=0;wire ntx_cr;int ntx_i=0;int ntx_credit=4;
 reg ptx_v=0;wire[511:0]ptx_d=w_ptx(ptx_i);wire ptx_r;int ptx_i=0;
 wire tx_v;wire[527:0]tx_d;reg tx_cr=0;int tx_out=0;
 wire drained,fault;int quiet4=0;
`ifdef USE_R3
 qkd_host_peer_link_r3
`else
 qkd_host_peer_link
`endif
 #(.MUT(MUTP)) dut(.ck(ck),.rst_n(rst_n),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),.normal_rx_v(nrx_v),.normal_rx_d(nrx_d),.normal_rx_cr(nrx_cr),
  .peer_rx_valid(prx_v),.peer_rx_data(prx_d),.peer_rx_ready(prx_r),.normal_tx_v(ntx_v),.normal_tx_d(ntx_d),.normal_tx_cr(ntx_cr),
  .peer_tx_valid(ptx_v),.peer_tx_data(ptx_d),.peer_tx_ready(ptx_r),.tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_cr),.drained(drained),.fault(fault));
 int nrx_c=0,prx_c=0,tn_c=0,tp_c=0,errs=0,cyc=0,fin=0,fault_cyc=-1,after=0,rxcr_c=0,rxsent=0,nrx_ret=0;
 function automatic int next_n(input int f);int i=f;while(i<N&&is_pk(i))i++;return i;endfunction
 function automatic int next_p(input int f);int i=f;while(i<N&&!is_pk(i))i++;return i;endfunction
 int nrx_e=0,prx_e=0;
 initial begin
  void'($value$plusargs("BAD=%d",bad));void'($value$plusargs("SEED=%d",seed));
  r=mix(64'(seed));repeat(5)@(posedge ck);rst_n<=1;
 end
 always @(posedge ck) if(rst_n)begin
  automatic longint unsigned q=mix(r);
  automatic int m=(cyc>>11)&3;
  automatic bit[7:0] g=(m==0)?8'hFF:(m==1)?q[7:0]:(m==2)?q[7:0]|q[15:8]:q[7:0]&q[15:8];
  automatic int cr=rx_credit+int'(rx_cr);
  automatic int ncr=ntx_credit+int'(ntx_cr);
  r<=q;cyc<=cyc+1;
  // RX sender: one word per credit; a word held by the normal consumer keeps its credit until normal_rx_cr
  rx_v<=0;
  if(bad==2&&rx_i>=200&&rx_i<212)begin rx_v<=1;rx_d<=w_rx(next_p(rx_i));rx_i<=next_p(rx_i)+1;end
  else if(cr>0&&rx_i<N&&q[16])begin
   automatic bit[527:0] w=w_rx(rx_i);
   if(bad==1&&is_pk(rx_i)&&rx_i>=100&&!fault)w[512]=1;
   rx_v<=1;rx_d<=w;rx_i<=rx_i+1;cr--;
  end
  rx_credit<=cr;
  if(rx_cr)rxcr_c<=rxcr_c+1;
  // normal consumer returns credit late
  begin automatic int h=nrx_held+int'(nrx_v);
   nrx_cr<=0;
   if(h>0&&g[0])begin nrx_cr<=1;h--;nrx_ret<=nrx_ret+1;end
   nrx_held<=h;
  end
  prx_r<=g[1]&&!(bad==2&&rx_i>=200);
  // normal TX source
  ntx_v<=0;
  if(bad==3&&ntx_i>=200&&ntx_i<212)begin ntx_v<=1;ntx_d<=w_ntx(ntx_i);ntx_i<=ntx_i+1;end
  else if(ncr>0&&ntx_i<N&&q[17])begin ntx_v<=1;ntx_d<=w_ntx(ntx_i);ntx_i<=ntx_i+1;ncr--;end
  ntx_credit<=ncr;
  // peer TX source, valid held until ready
  if(ptx_v&&ptx_r)begin ptx_i<=ptx_i+1;ptx_v<=q[18]&&ptx_i+1<N;end else if(!ptx_v)ptx_v<=q[18]&&ptx_i<N;
  // physical credit sink
  begin automatic int o=tx_out+int'(tx_v);
   tx_cr<=0;
   if(o>0&&g[2])begin tx_cr<=1;o--;end
   if(bad==4&&ntx_i==N&&ptx_i==N&&o==0&&!tx_cr&&!fault)begin tx_cr<=1;quiet4<=quiet4+1;end
   if(o>4)begin errs++;$display("ERR physical credits %0d",o);end
   tx_out<=o;
  end
  // checkers
  if(fault&&fault_cyc<0)fault_cyc<=cyc;
  if(nrx_v)begin
   automatic int e=next_n(nrx_e);
   if(bad!=2&&!fault&&nrx_d!==w_rx(e))begin errs++;$display("ERR nrx %0d",e);end
   nrx_e<=e+1;nrx_c<=nrx_c+1;
  end
  if(prx_v&&prx_r)begin
   automatic int e=next_p(prx_e);
   if(fault)after<=after+1;
   if(prx_d[511:0]!==w_rx(e)[511:0])begin errs++;$display("ERR prx %0d",e);end
   prx_e<=e+1;prx_c<=prx_c+1;
  end
  if(tx_v)begin
   if(tx_d[527:524]==9)begin if(tx_d[523:512]!=0||tx_d[511:0]!==w_ptx(tp_c))begin errs++;$display("ERR tx peer %0d",tp_c);end tp_c<=tp_c+1;end
   else begin if(tx_d!==w_ntx(tn_c))begin errs++;$display("ERR tx normal %0d",tn_c);end tn_c<=tn_c+1;end
  end
  if(errs>5)begin $display("FAIL errs=%0d",errs);$finish;end
  if(bad!=0&&fault_cyc>=0&&cyc>fault_cyc+200)begin
   $display("FAULT_RAISED bad=%0d cyc=%0d errs=%0d after=%0d",bad,fault_cyc,errs,after);
   if(errs==0&&after==0)$display("PASS");else $display("FAIL");$finish;end
  if(bad==0&&rx_i==N&&ntx_i==N&&ptx_i==N)fin<=fin+1;
  if(fin==300)begin
   automatic bit ok=next_n(nrx_e)==N&&next_p(prx_e)==N&&tn_c==N&&tp_c==N&&!fault&&drained&&rx_credit==4&&ntx_credit==4;
   $display("DONE cyc=%0d nrx=%0d prx=%0d tn=%0d tp=%0d errs=%0d fault=%0d drained=%0d rxcr=%0d cr=%0d/%0d",cyc,nrx_c,prx_c,tn_c,tp_c,errs,fault,drained,rxcr_c,rx_credit,ntx_credit);
   if(ok&&errs==0)$display("PASS");else $display("FAIL");$finish;end
  if(cyc>60*N)begin $display("FAIL timeout rx=%0d ntx=%0d ptx=%0d fault=%0d",rx_i,ntx_i,ptx_i,fault);$finish;end
 end
endmodule
