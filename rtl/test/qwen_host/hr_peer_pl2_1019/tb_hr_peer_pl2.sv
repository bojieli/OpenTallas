`timescale 1ns/1ps
// KV-PEER5 (10-19): qkd_host_peer_root_mux_pl2 vs the UNCHANGED qkd_host_peer_root_mux, transaction level.
// Each model has its own sources and sinks over the SAME per-channel word lists; a source holds its word until its own
// model takes it (class9 valid/ready).  Channels: physical RX (shape-legal words, random rank 1..7), local rank-0 TX,
// coordinator TX per rank 0..7 (legal headers).  Sinks: physical_tx_ready, local_rx_ready, coordinator_rx_ready[7:0]
// random (the same draw per edge for both models).
// LEGAL epochs: after the active phase the sources stop and both models drain; then, per channel and per rank, the
//   delivered word sequence of _pl2 must EQUAL the reference's (no drop / duplicate / reorder / corruption), and
//   neither model may fault.  Then an async reset starts the next epoch.
// FAULT epochs (1 in 8): one illegal word (non-shape physical RX word, or a bad coordinator TX header on a random rank)
//   is placed in the stream; both models must end the epoch faulted (fault parity).
// PASS needs >= 40 legal epochs, >= 4 fault epochs and >= 20k delivered words.  -DQKD_HR_PE_PL2_MUTANT must FAIL.
module tb_hr_peer_pl2;
 parameter integer NEPOCH=160, SEED=1019;
 reg ck=0,por_n=0;
 always #5 ck=~ck;
 // shared sink draws
 reg ptr=0,lrr=0;reg[7:0]crr=0;
 // per-model source state
 reg prv[2];reg[511:0]prd[2];reg ltv[2];reg[511:0]ltd[2];reg[7:0]ctv[2];reg[4095:0]ctd[2];
 wire prr[2],ptv[2],ltr[2],lrv[2],flt[2];wire[511:0]ptd[2],lrd[2];wire[7:0]crv[2],ctr[2];wire[4095:0]crd[2];
 qkd_host_peer_root_mux ua(.ck(ck),.por_n(por_n),.physical_rx_valid(prv[0]),.physical_rx_data(prd[0]),.physical_rx_ready(prr[0]),
  .physical_tx_valid(ptv[0]),.physical_tx_data(ptd[0]),.physical_tx_ready(ptr),.local_tx_valid(ltv[0]),.local_tx_data(ltd[0]),
  .local_tx_ready(ltr[0]),.local_rx_valid(lrv[0]),.local_rx_data(lrd[0]),.local_rx_ready(lrr),.coordinator_rx_valid(crv[0]),
  .coordinator_rx_data(crd[0]),.coordinator_rx_ready(crr),.coordinator_tx_valid(ctv[0]),.coordinator_tx_data(ctd[0]),
  .coordinator_tx_ready(ctr[0]),.fault(flt[0]));
 qkd_host_peer_root_mux_pl2 ub(.ck(ck),.por_n(por_n),.physical_rx_valid(prv[1]),.physical_rx_data(prd[1]),.physical_rx_ready(prr[1]),
  .physical_tx_valid(ptv[1]),.physical_tx_data(ptd[1]),.physical_tx_ready(ptr),.local_tx_valid(ltv[1]),.local_tx_data(ltd[1]),
  .local_tx_ready(ltr[1]),.local_rx_valid(lrv[1]),.local_rx_data(lrd[1]),.local_rx_ready(lrr),.coordinator_rx_valid(crv[1]),
  .coordinator_rx_data(crd[1]),.coordinator_rx_ready(crr),.coordinator_tx_valid(ctv[1]),.coordinator_tx_data(ctd[1]),
  .coordinator_tx_ready(ctr[1]),.fault(flt[1]));
 // per-epoch word lists (index: 0 physical RX, 1 local TX, 2+r coordinator TX rank r)
 reg[511:0]lst[10][$];
 integer pos[2][10];
 // delivered streams per model: 0 physical TX (split by rank header later), 1 local RX, 2+r coordinator RX rank r
 reg[511:0]got[2][10][$];
 integer seed,ep,cyc,k,m,legal_ep=0,fault_ep=0,errs=0,first_err=-1,words=0,fparity=0,lfaults=0;
 reg fault_epoch;integer bad_ch;
 task automatic word(output reg[511:0]w);begin for(int j=0;j<16;j++)w[j*32+:32]=$random(seed);end endtask
 task automatic mk_lists(input integer n);
  reg[511:0]w;
  for(int c=0;c<10;c++)lst[c].delete();
  for(int i=0;i<n;i++)begin
   if(($random(seed)&3)!=0)begin word(w);w[7]=0;w[13:11]=0;w[10:8]=3'(1+(($random(seed)&32'h7fffffff)%7));lst[0].push_back(w);end
   if(($random(seed)&3)!=0)begin word(w);lst[1].push_back(w);end
   for(int r=0;r<8;r++)if(($random(seed)&7)==0)begin word(w);w[7]=1;w[10:8]=0;w[13:11]=3'(r);lst[2+r].push_back(w);end
  end
  if(fault_epoch)begin
   bad_ch=($random(seed)&1)?0:2+1+(($random(seed)&32'h7fffffff)%7);
   if(lst[bad_ch].size()==0)begin word(w);w[13:11]=3'(bad_ch==0?0:bad_ch-2);lst[bad_ch].push_back(w);end
   k=($random(seed)&32'h7fffffff)%lst[bad_ch].size();w=lst[bad_ch][k];
   if(bad_ch==0)w[7]=1;else w[10:8]=3'd5;   // non-shape RX word / bad TX source field
   lst[bad_ch][k]=w;
  end
 endtask
 // present the current list word of channel c for model m
 task automatic present(input integer mm);
  prv[mm]=pos[mm][0]<lst[0].size();if(prv[mm])prd[mm]=lst[0][pos[mm][0]];
  ltv[mm]=pos[mm][1]<lst[1].size();if(ltv[mm])ltd[mm]=lst[1][pos[mm][1]];
  for(int r=0;r<8;r++)begin ctv[mm][r]=pos[mm][2+r]<lst[2+r].size();if(ctv[mm][r])ctd[mm][r*512+:512]=lst[2+r][pos[mm][2+r]];end
 endtask
 task automatic err(input integer c);begin errs=errs+1;if(first_err<0)first_err=ep*1000+c;
  if(errs<=12)$display("HR_PEER_PL2_ERR ep=%0d c=%0d cyc=%0d sizes ref/pl2: ptx %0d/%0d lrx %0d/%0d crx0 %0d/%0d crx1 %0d/%0d lists prx %0d ltx %0d ctx0 %0d pos ref %0d %0d pl2 %0d %0d flt %0d/%0d",
   ep,c,cyc,got[0][0].size(),got[1][0].size(),got[0][1].size(),got[1][1].size(),got[0][2].size(),got[1][2].size(),got[0][3].size(),got[1][3].size(),
   lst[0].size(),lst[1].size(),lst[2].size(),pos[0][0],pos[0][1],pos[1][0],pos[1][1],flt[0],flt[1]);end endtask
 initial begin
  seed=SEED;
  for(m=0;m<2;m++)begin prv[m]=0;ltv[m]=0;ctv[m]=0;prd[m]=0;ltd[m]=0;ctd[m]=0;end
  for(ep=0;ep<NEPOCH;ep++)begin
   fault_epoch=(ep%8)==7;
   mk_lists(150+($random(seed)&127));
   for(m=0;m<2;m++)for(int c=0;c<10;c++)begin pos[m][c]=0;got[m][c].delete();end
   por_n=0;for(m=0;m<2;m++)present(m);
   repeat(2)@(posedge ck);#1;por_n=1;   // released just after an edge: the loop samples before the first live edge
   for(cyc=0;cyc<6000;cyc++)begin
    @(negedge ck);
    // handshakes the coming posedge performs (settled values)
    for(m=0;m<2;m++)begin
     if(prv[m]&&prr[m])pos[m][0]++;
     if(ltv[m]&&ltr[m])pos[m][1]++;
     for(int r=0;r<8;r++)if(ctv[m][r]&&ctr[m][r])pos[m][2+r]++;
     if(ptv[m]&&ptr)got[m][0].push_back(ptd[m]);
     if(lrv[m]&&lrr)got[m][1].push_back(lrd[m]);
     for(int r=0;r<8;r++)if(crv[m][r]&&crr[r])got[m][2+r].push_back(crd[m][r*512+:512]);
    end
    @(posedge ck);#1;
    for(m=0;m<2;m++)present(m);
    ptr=$random(seed);lrr=$random(seed);crr=($random(seed)&1)?8'hff:8'($random(seed));
    // done: every source empty and nothing delivered for a while (both models)
    if(cyc>200&&!prv[0]&&!prv[1]&&!ltv[0]&&!ltv[1]&&ctv[0]==0&&ctv[1]==0&&(cyc%64)==0&&
       !ptv[0]&&!ptv[1]&&crv[0]==0&&crv[1]==0&&!lrv[0]&&!lrv[1])break;
    if(flt[0]&&flt[1]&&fault_epoch)break;
   end
   if(fault_epoch)begin
    fault_ep++;
    if(!(flt[0]&&flt[1]))begin fparity++;err(900);end
   end else begin
    legal_ep++;
    if(flt[0]||flt[1])begin lfaults++;err(800);end
    // channels other than the merged physical TX stream: identical sequences (its interleaving of ranks may differ)
    for(int c=1;c<10;c++)begin
     if(got[0][c].size()!=got[1][c].size())err(c);
     else for(int i=0;i<got[0][c].size();i++)if(got[0][c][i]!==got[1][c][i])begin err(100+c);break;end
     words=words+got[1][c].size();
    end
    words=words+got[1][0].size();
    // the physical TX words of each rank, in BOTH models: exactly the rank's source list, in order
    for(int mm=0;mm<2;mm++)for(int r=1;r<8;r++)begin
     int j;j=0;
     for(int i=0;i<got[mm][0].size();i++)if(got[mm][0][i][13:11]==3'(r))begin
      if(j>=lst[2+r].size()||got[mm][0][i]!==lst[2+r][j])begin
       err(200+10*mm+r);break;end
      j++;
     end
     if(j!=lst[2+r].size())err(300+10*mm+r);
    end
    if(got[0][0].size()!=got[1][0].size())err(390);
    if(got[1][1].size()!=lst[2].size())err(400);   // local RX = coordinator TX rank 0
    for(int r=1;r<8;r++)begin int n;n=0;foreach(lst[0][i])if(lst[0][i][10:8]==3'(r))n++;if(got[1][2+r].size()!=n)err(500+r);end
    if(got[1][2].size()!=lst[1].size())err(600);   // coordinator RX rank 0 = local TX
   end
  end
  $display("HR_PEER_PL2 seed=%0d epochs=%0d legal=%0d fault=%0d words=%0d legal_faults=%0d fault_parity_errs=%0d errs=%0d first_err=%0d %s",
   SEED,NEPOCH,legal_ep,fault_ep,words,lfaults,fparity,errs,first_err,
   (errs==0&&legal_ep>=40&&fault_ep>=4&&words>=20000)?"PASS":"FAIL");
  $finish;
 end
endmodule
