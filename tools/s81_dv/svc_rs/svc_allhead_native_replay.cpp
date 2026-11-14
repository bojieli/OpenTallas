#include "Vtb_svc_native_programme.h"
#include "Vtb_svc_native_programme__Syms.h"
#include "verilated.h"
#include "verilated_timing.h"
#include <array>
#include <vector>
#include <map>
#include <fstream>
#include <string>
#include <cstdio>
#include <cstdlib>
using TB=Vtb_svc_native_programme_tb_svc_native_programme;
static int driver_interpositions=0;
VlCoroutine Vtb_svc_native_programme_tb_svc_native_programme___eval_initial__TOP__tb_svc_native_programme__Vtiming__0(TB*){++driver_interpositions;co_return;}
using Word=std::array<uint32_t,16>;using Score=std::array<uint32_t,34>;
static void put(Word&w,int lo,int n,uint64_t v){for(int b=0;b<n;b++){uint32_t m=1U<<((lo+b)%32);if((v>>b)&1)w[(lo+b)/32]|=m;else w[(lo+b)/32]&=~m;}}
static Word hdr(int t,int n){Word w{};put(w,508,4,t);put(w,503,1,1);put(w,480,12,n);return w;}
template<size_t N>static std::array<uint32_t,N> hx(const std::string&s){std::array<uint32_t,N>w{};int i=0;for(int e=s.size();e>0;e-=8){int a=e>=8?e-8:0;if(i>=int(N))exit(2);w[i++]=std::stoul(s.substr(a,e-a),nullptr,16);}return w;}
template<size_t N>static std::vector<std::array<uint32_t,N>> readhex(const char*p){std::vector<std::array<uint32_t,N>>v;std::ifstream f(p);std::string s;while(f>>s)v.push_back(hx<N>(s));return v;}
int main(int argc,char**argv){
 if(argc!=7){fprintf(stderr,"usage: replay ROWS P0 P1 SCORE0 SCORE1 DATES\n");return 2;}
 int rows=std::atoi(argv[1]);if(rows!=32&&rows!=128)return 2;int nb=rows/4;
 auto p0=readhex<16>(argv[2]),p1=readhex<16>(argv[3]);auto s0=readhex<34>(argv[4]),s1=readhex<34>(argv[5]);auto d=readhex<1>(argv[6]);
 std::vector<Word>pvectors[2]={p0,p1};std::vector<Score>svectors[2]={s0,s1};
 if(int(p0.size())!=nb||int(p1.size())!=nb||int(s0.size())!=nb||int(s1.size())!=nb||int(d.size())!=nb)return 2;
 for(int p=0;p<2;p++)for(auto&w:pvectors[p])for(auto x:w)if(x!=0x3f803f80U)return 2;
 std::map<int,Word>q;int at=70;auto emit=[&](const Word&w){if(!q.emplace(at++,w).second)abort();};auto gap=[&](){at+=5;};
 Word w=hdr(12,0);put(w,32,1,1);emit(w);gap();w=hdr(2,0);put(w,89,10,rows);put(w,495,8,1);emit(w);gap();
 w=hdr(7,rows/16);put(w,10,10,rows);emit(w);for(int j=0;j<rows/16;j++){w={};for(int r=0;r<16;r++)put(w,32*r,32,80+r+256*j);emit(w);}gap();
 emit(hdr(6,rows));for(int r=0;r<rows;r++){w={};put(w,0,10,r);put(w,10,21,80+r%16+256*(r/16));for(int k=0;k<32;k++)put(w,34+4*k,4,2);put(w,290,16,0x3838);emit(w);}gap();
 auto emitQ=[&](int hb){Word h=hdr(1,128);put(h,448,1,hb);emit(h);for(int j=0;j<128;j++){Word b{};for(int k=0;k<32;k++)put(b,16*k,16,(hb?0x3d80:0x3e80)+32*(j/16)+k);emit(b);}gap();};
 emitQ(0);if(at>=400)return 2;
 const int gos[2]={402,1702};
 for(int p=0;p<2;p++){if(p){at=1500;emitQ(1);if(at>=1700)return 2;}w=hdr(13,0);put(w,0,16,800);put(w,16,16,1024);put(w,48,1,p==0);q[gos[p]-2]=w;w=hdr(5,nb);put(w,495,8,1);q[gos[p]+725]=w;for(int k=0;k<nb;k++)q[gos[p]+726+2*k]=pvectors[p][k];}
 auto*c=new VerilatedContext;c->commandArgs(argc,argv);auto*t=new Vtb_svc_native_programme(c);t->eval();auto*s=t->rootp->vlSymsp;auto&tb=s->TOP__tb_svc_native_programme;auto&u=s->TOP__tb_svc_native_programme__u;auto&e=s->TOP__tb_svc_native_programme__u__u_eng;
 if(driver_interpositions!=1){printf("ALLHEAD_NATIVE_LINK_FAIL interpositions%d\n",driver_interpositions);return 3;}
 int cyc=0,p=-1,origin=-1,errors=0,retention=0,qa[2]={},ka[2]={},pa[2]={},ns[2]={},np[2]={},inputs[2]={},drain[2]={},headers[2]={},body[2]={},afn=0;
 int firsts[2]={-1,-1},lasts[2]={-1,-1},firstv[2]={-1,-1},lastv[2]={-1,-1},firstk[2]={-1,-1},lastk[2]={-1,-1},firsti[2]={-1,-1},lasti[2]={-1,-1},firstd[2]={-1,-1},lastd[2]={-1,-1};unsigned oldpw=0;
 uint32_t gold=rows==32?0x42000000U:0x43000000U;
 while(!c->gotFinish()&&t->eventsPending()){
  bool rise=!tb.__PVT__clk;
  if(!rise){int next=cyc+1;tb.__PVT__rst_n=next>=65;auto it=q.find(next);tb.__PVT__qv=it!=q.end();for(int k=0;k<16;k++)tb.__PVT__q[k]=it==q.end()?0:it->second[k];}
  c->time(t->nextTimeSlot());
  if(rise){cyc++;if(tb.__PVT__rst_n){
   if(cyc==1490){bool present=true;for(int r=0;r<rows;r++)if(!(u.__PVT__pres[r/32]&(1U<<(r%32))))present=false;retention=u.__PVT__job_open&&!u.__PVT__done&&!u.__PVT__job_active&&present;printf("ALLHEAD_RETENTION rows%d jobOpen%u done%u active%u allRowsPresent%d pass%d\n",rows,u.__PVT__job_open,u.__PVT__done,u.__PVT__job_active,present,retention);if(!retention)errors++;}
   if(u.__PVT__go){p++;origin=cyc;if(p>=2)return 1;int phase=s->TOP__tb_svc_native_programme__u__g_native_load_calendar__DOT__u_calendar.__PVT__phase;printf("ALLHEAD_NATIVE_GO pass%d rows%d cycle%d phase%d po%u pvo%u nsel%u\n",p,rows,cyc,phase,u.__PVT__po,u.__PVT__pvo,u.__PVT__nsel);if(cyc!=gos[p]||phase!=1||u.__PVT__po!=800||u.__PVT__pvo!=1024||u.__PVT__nsel!=rows)errors++;}
   if(p>=0){int rel=cyc-origin;
    if(u.__PVT__eq_v&&e.__PVT__q_ready)qa[p]++;
    if(u.__PVT__ekv_v&&e.__PVT__kv_ready){if(firstk[p]<0)firstk[p]=rel;lastk[p]=rel;ka[p]++;}
    if(e.__PVT__g_pskid__DOT__pop)pa[p]++;
    if(e.__PVT__sc_v){
     if(firsts[p]<0)firsts[p]=rel;lasts[p]=rel;
     if(ns[p]>=nb)errors++;else {auto&g=svectors[p][ns[p]];if(rel!=int(d[ns[p]][0])||((unsigned(e.__PVT__sc_row)<<4)|e.__PVT__sc_m)!=(g[33]&0xfffff)||e.__PVT__sc_f!=g[0])errors++;for(int k=0;k<32;k++)if(e.__PVT__sc_y[k]!=g[k+1])errors++;}
     printf("FRESH_SCORE pass%d rows%d relative%d row%u payload",p,rows,rel,e.__PVT__sc_row);for(int k=31;k>=0;k--)printf("%08x",e.__PVT__sc_y[k]);printf(" flags%08x\n",e.__PVT__sc_f);ns[p]++;
    }
    if(e.__PVT__pv_v){if(firstv[p]<0)firstv[p]=rel;lastv[p]=rel;if(np[p]>=8||e.__PVT__pv_c!=np[p]||e.__PVT__pv_f)errors++;for(int k=0;k<32;k++)if(e.__PVT__pv_y[k]!=gold)errors++;printf("FRESH_PV pass%d rows%d relative%d c%u payload",p,rows,rel,e.__PVT__pv_c);for(int k=31;k>=0;k--)printf("%08x",e.__PVT__pv_y[k]);printf(" flags%08x\n",e.__PVT__pv_f);np[p]++;}
    if(u.__PVT__pv_ov){if(firstd[p]<0)firstd[p]=rel;lastd[p]=rel;drain[p]++;if(u.__PVT__p_i!=drain[p]%5)errors++;if(u.__PVT__p_i==1)headers[p]++;else body[p]++;}
    unsigned af=s->TOP__tb_svc_native_programme__u__u_eng__g_tr__BRA__0__KET____DOT__g_xb__DOT__u_band__u_t__u_hc__u_expand.__PVT__fault|s->TOP__tb_svc_native_programme__u__u_eng__g_tr__BRA__1__KET____DOT__g_xb__DOT__u_band__u_t__u_hc__u_expand.__PVT__fault|s->TOP__tb_svc_native_programme__u__u_eng__g_tr__BRA__2__KET____DOT__g_xb__DOT__u_band__u_t__u_hc__u_expand.__PVT__fault|s->TOP__tb_svc_native_programme__u__u_eng__g_tr__BRA__3__KET____DOT__g_xb__DOT__u_band__u_t__u_hc__u_expand.__PVT__fault;if(af)afn++;
   }
  }}
  t->eval();
  if(rise&&tb.__PVT__rst_n&&u.__PVT__pw!=oldpw){if(u.__PVT__pw!=oldpw+1||p<0)errors++;if(p>=0){int rel=cyc-origin;if(firsti[p]<0)firsti[p]=rel;lasti[p]=rel;inputs[p]++;}oldpw=u.__PVT__pw;}
  if(cyc>gos[1]+1080)break;
 }
 for(int k=0;k<2;k++){if(qa[k]!=8||ka[k]!=nb||pa[k]!=nb/2||ns[k]!=nb||np[k]!=8||inputs[k]!=nb||drain[k]!=40||headers[k]!=8||body[k]!=32||firstk[k]!=2||lastk[k]!=nb+1||firsti[k]!=726||lasti[k]!=726+2*(nb-1))errors++;
  printf("ALLHEAD_NATIVE_PASS pass%d rows%d Q%d KV%d Pconsume%d SCORE%d PV%d inputWords%d drain%d headers%d bodies%d KVDates%d:%d SCOREDates%d:%d PVDates%d:%d inputDates%d:%d drainDates%d:%d\n",k,rows,qa[k],ka[k],pa[k],ns[k],np[k],inputs[k],drain[k],headers[k],body[k],firstk[k],lastk[k],firsts[k],lasts[k],firstv[k],lastv[k],firsti[k],lasti[k],firstd[k],lastd[k]);}
 if(p!=1||!retention||!u.__PVT__done||u.__PVT__job_open||u.__PVT__pw!=2*nb||u.__PVT__pr!=2*nb||u.__PVT__fc||afn)errors++;
 printf("ALLHEAD_NATIVE_SUMMARY rows%d interpositions%d retention%d pw%u pr%u done%u jobOpen%u fc%08x af%u errors%d\n",rows,driver_interpositions,retention,u.__PVT__pw,u.__PVT__pr,u.__PVT__done,u.__PVT__job_open,u.__PVT__fc,afn,errors);
 printf("ALLHEAD_NATIVE_REPLAY %s rows%d\n",errors?"FAIL":"PASS",rows);t->final();delete t;delete c;return errors?1:0;
}
