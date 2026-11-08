// DIE-HBM-92-OPEN/OWNRF lock-step bench driver (Verilator). argv: seed cycles
#include "Vls_top.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <deque>
#include <random>
#include <algorithm>
struct Beat{uint32_t tag,beat;int ready_at;};
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);
 uint64_t seed=argc>1?strtoull(argv[1],0,10):1; long N=argc>2?atol(argv[2]):100000;
 std::mt19937_64 R(seed); auto rnd=[&](uint32_t n){return (uint32_t)(R()%n);};
 Vls_top* t=new Vls_top;
 auto setbits=[&](uint32_t* w,int lo,int n,uint64_t v){for(int i=0;i<n;i++){int b=lo+i;uint32_t m=1u<<(b&31);if((v>>i)&1)w[b>>5]|=m;else w[b>>5]&=~m;}};
 auto getbits=[&](const uint32_t* w,int lo,int n){uint64_t v=0;for(int i=0;i<n;i++){int b=lo+i;if((w[b>>5]>>(b&31))&1)v|=1ull<<i;}return v;};
 std::vector<int> krdy_at(4,-1);           // cycle at which k_rdy is driven for a pending p_v
 std::vector<int> krdy_acc(4,0);
 std::vector<std::deque<Beat>> beats(4);
 std::vector<std::vector<int>> prdy_hist(4,std::vector<int>(4,0));
 std::vector<std::deque<int>> cr(8);
 long words_out=0,words_sent=0,ndesc=0,cov=0,faults=0,kacc=0,beats_sent=0,mism_cyc=-1,fault_cyc=-1;
 std::deque<long> desc_tot;
 t->clk=0;t->rst_n=0;t->seam_res_v=0;t->seam_s_fault=0;t->bk_cr=0;t->k_rdy=0;t->k_wr_done=0;t->kr_v=0;
 for(int i=0;i<4;i++){t->clk=0;t->eval();t->clk=1;t->eval();}
 t->clk=0;t->rst_n=1;t->eval();
 for(long c=0;c<N;c++){
  // ---- drive inputs for cycle c (clk low)
  // descriptors: keep <=2 not drained
  long outstanding=0; for(long x:desc_tot) outstanding+=x;
  t->seam_res_v=0;
  if(c>32 && desc_tot.size()<2 && rnd(8)==0){
   uint32_t* w=(uint32_t*)t->seam_res_word.data(); for(int i=0;i<4;i++)w[i]=0;
   uint32_t total=1+rnd((rnd(4)==0)?512:96); uint64_t base=R()%((1ull<<30)-total);
   int perm[4]={0,1,2,3}; std::shuffle(perm,perm+4,R);
   setbits(w,0,16,R());setbits(w,16,2,rnd(4));setbits(w,18,12,total);setbits(w,30,30,base);setbits(w,60,2,0);setbits(w,62,15,R());
   for(int j=0;j<4;j++)setbits(w,77+5*j,5,perm[j]);
   t->seam_res_v=1; desc_tot.push_back(total); words_sent+=total; ndesc++;
  }
  // k_rdy
  uint8_t krdy=0; for(int p=0;p<4;p++) if(krdy_at[p]==c && krdy_acc[p]) krdy|=1<<p; t->k_rdy=krdy;
  // kr beats
  uint8_t krv=0; uint32_t* tg=(uint32_t*)t->kr_tag.data(); uint32_t btw[1]={0}; uint32_t* bt=btw; uint32_t* kd=(uint32_t*)t->kr_data.data();
  for(int p=0;p<4;p++){
   bool ok=prdy_hist[p][(c+2)%4]; // p_rdy observed at cycle c-2
   if(ok && !beats[p].empty() && rnd(10)<7){
    // pick among the first few ready beats (reorder)
    int k=-1; int lim=std::min<int>(4,beats[p].size()); int st=rnd(lim);
    for(int q=0;q<lim;q++){int i=(st+q)%lim; if(beats[p][i].ready_at<=c){k=i;break;}}
    if(k>=0){ Beat b=beats[p][k]; beats[p].erase(beats[p].begin()+k);
     krv|=1<<p; setbits(tg,17*p,17,b.tag); setbits(bt,4*p,4,b.beat); for(int i=0;i<8;i++)kd[8*p+i]=(uint32_t)R(); beats_sent++; }
   }
  }
  t->kr_v=krv; t->kr_beat=(uint16_t)btw[0];
  uint8_t bc=0; for(int g=0;g<8;g++) if(!cr[g].empty() && cr[g].front()<=c){bc|=1<<g;cr[g].pop_front();} t->bk_cr=bc;
  t->eval();
  if(t->mism && mism_cyc<0){mism_cyc=c;}
  // ---- observe outputs during cycle c
  for(int p=0;p<4;p++) prdy_hist[p][c%4]=(t->a_kr_rdy>>p)&1;
  for(int p=0;p<4;p++) if((t->a_k_v>>p)&1){ krdy_at[p]=c+2; krdy_acc[p]=rnd(10)<8;
    if(krdy_acc[p]){ uint32_t tag=getbits((uint32_t*)t->a_k_tag.data(),17*p,17); uint32_t lw[1]={(uint32_t)t->a_k_len}; uint32_t len=getbits(lw,4*p,4);
      std::vector<uint32_t> bs; for(uint32_t b=0;b<len;b++)bs.push_back(b); std::shuffle(bs.begin(),bs.end(),R);
      int lat=3+rnd(30); for(auto b:bs) beats[p].push_back({tag,b,(int)(c+2+lat+rnd(6))}); kacc++; } }
  for(int g=0;g<8;g++) if((t->a_bk_in_v>>g)&1){ words_out++; cr[g].push_back(c+2+rnd(30));
    long w=1; while(w>0 && !desc_tot.empty()){ if(desc_tot.front()>w){desc_tot.front()-=w;w=0;} else {w-=desc_tot.front();desc_tot.pop_front();} } }
  for(int p=0;p<4;p++) if((t->cov_tail>>p)&1) cov++;
  if(t->a_seam_h_fault){faults++; if(fault_cyc<0)fault_cyc=c;}
  // ---- clock edge
  t->clk=1;t->eval();t->clk=0;t->eval();
  if(mism_cyc>=0) break;
 }
 printf("LOCKSTEP seed=%llu cycles=%ld mismatch_cycle=%ld descriptors=%ld words_sent=%ld words_out=%ld k_accepted=%ld beats=%ld tail_grants=%ld fault_cycles=%ld first_fault=%ld\n",
  (unsigned long long)seed,N,mism_cyc,ndesc,words_sent,words_out,kacc,beats_sent,cov,faults,fault_cyc);
 delete t; return mism_cyc>=0?2:0;
}
