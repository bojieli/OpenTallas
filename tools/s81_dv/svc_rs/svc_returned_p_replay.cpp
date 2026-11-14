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
// Replaces ONLY the compiled SV testbench's timed stimulus coroutine. Clock,
// all design logic and original cache remain untouched. No UUT-state writes.
VlCoroutine Vtb_svc_native_programme_tb_svc_native_programme___eval_initial__TOP__tb_svc_native_programme__Vtiming__0(TB*){++driver_interpositions;co_return;}
using Word=std::array<uint32_t,16>;using Score=std::array<uint32_t,34>;
static void put(Word&w,int lo,int width,uint64_t x){for(int b=0;b<width;b++){uint32_t m=1U<<((lo+b)%32);if((x>>b)&1)w[(lo+b)/32]|=m;else w[(lo+b)/32]&=~m;}}
static Word hdr(int type,int len){Word w{};put(w,508,4,type);put(w,503,1,1);put(w,480,12,len);return w;}
template<size_t N>static std::array<uint32_t,N> hex(const std::string&s){std::array<uint32_t,N>w{};int i=0;for(int end=s.size();end>0;end-=8){int start=end>=8?end-8:0;if(i>=int(N)){fprintf(stderr,"overwide input\n");exit(2);}w[i++]=std::stoul(s.substr(start,end-start),nullptr,16);}return w;}
int main(int argc,char**argv){
 if(argc!=4){fprintf(stderr,"usage: replay returned_p.hex score.hex dates.hex\n");return 2;}
 std::vector<Word>pwords;std::vector<Score>scores;std::vector<int>dates;std::string line;
 {std::ifstream f(argv[1]);while(f>>line)pwords.push_back(hex<16>(line));}
 {std::ifstream f(argv[2]);while(f>>line)scores.push_back(hex<34>(line));}
 {std::ifstream f(argv[3]);while(f>>line)dates.push_back(std::stoul(line,nullptr,16));}
 if(pwords.size()!=8||scores.size()!=8||dates.size()!=8)return 2;
 std::map<int,Word>programme;int at=70;
 auto emit=[&](const Word&w){if(!programme.emplace(at++,w).second)abort();};auto gap=[&](){at+=5;};
 Word w=hdr(12,0);put(w,32,1,1);emit(w);gap();
 w=hdr(2,0);put(w,89,10,32);put(w,495,8,1);emit(w);gap();
 w=hdr(7,2);put(w,10,10,32);emit(w);
 for(int j=0;j<2;j++){w={};for(int r=0;r<16;r++)put(w,32*r,32,80+r+256*j);emit(w);}gap();
 emit(hdr(6,32));for(int r=0;r<32;r++){w={};put(w,0,10,r);put(w,10,21,80+r%16+256*(r/16));for(int d=0;d<32;d++)put(w,34+4*d,4,2);put(w,290,16,0x3838);emit(w);}gap();
 emit(hdr(1,128));for(int j=0;j<128;j++){w={};for(int d=0;d<32;d++)put(w,16*d,16,0x3e80+32*(j/16)+d);emit(w);}gap();
 if(at>=400)return 2;
 const int expected_go=402;
 w=hdr(13,0);put(w,0,16,800);put(w,16,16,1024);programme[400]=w;
 // Exact staged production packet tag1 and body timing, relative to source GO.
 w=hdr(5,8);put(w,495,8,1);programme[expected_go+725]=w;
 for(int k=0;k<8;k++)programme[expected_go+726+2*k]=pwords[k];
 auto*ctx=new VerilatedContext;ctx->commandArgs(argc,argv);auto*top=new Vtb_svc_native_programme(ctx);
 top->eval();auto*s=top->rootp->vlSymsp;auto&tb=s->TOP__tb_svc_native_programme;auto&u=s->TOP__tb_svc_native_programme__u;auto&e=s->TOP__tb_svc_native_programme__u__u_eng;
 if(driver_interpositions!=1){printf("REPLAY_LINK_FAIL driver_interpositions=%d\n",driver_interpositions);return 3;}
 int cycle=0,origin=-1,phase=-1,ns=0,np=0,qa=0,ka=0,pa=0,drains=0,dh=0,db=0,errors=0,affaults=0,firsts=-1,lasts=-1,firstp=-1,lastp=-1,firstd=-1,lastd=-1,firstword=-1,lastword=-1,pwseen=0;
 unsigned prevpw=0;bool clockwas=tb.__PVT__clk;
 while(!ctx->gotFinish()&&top->eventsPending()){
  bool next_rise=!tb.__PVT__clk;
  if(!next_rise){int next=cycle+1;tb.__PVT__rst_n=next>=65;auto it=programme.find(next);tb.__PVT__qv=it!=programme.end();for(int k=0;k<16;k++)tb.__PVT__q[k]=it==programme.end()?0:it->second[k];}
  ctx->time(top->nextTimeSlot());
  if(next_rise){
   cycle++;
   if(tb.__PVT__rst_n){
    if(u.__PVT__go){origin=cycle;phase=s->TOP__tb_svc_native_programme__u__g_native_load_calendar__DOT__u_calendar.__PVT__phase;printf("REPLAY_GO cycle%d phase%d po%u pvo%u tagPortUnobservable1\n",cycle,phase,u.__PVT__po,u.__PVT__pvo);if(origin!=expected_go||phase!=1||u.__PVT__po!=800||u.__PVT__pvo!=1024)errors++;}
    if(origin>=0){
     int rel=cycle-origin;
     if(u.__PVT__eq_v&&e.__PVT__q_ready){printf("REPLAY_Q cycle%d relative%d\n",cycle,rel);qa++;}
     if(u.__PVT__ekv_v&&e.__PVT__kv_ready)ka++;
     if(e.__PVT__g_pskid__DOT__pop){printf("REPLAY_P_ACCEPT cycle%d relative%d\n",cycle,rel);pa++;}
     if(e.__PVT__sc_v){
      if(firsts<0)firsts=rel;lasts=rel;
      if(ns>=8)errors++;
      else {if(rel!=dates[ns]||((unsigned(e.__PVT__sc_row)<<4)|e.__PVT__sc_m)!=(scores[ns][33]&0xfffff)||e.__PVT__sc_f!=scores[ns][0])errors++;for(int k=0;k<32;k++)if(e.__PVT__sc_y[k]!=scores[ns][k+1])errors++;}
      printf("REPLAY_SCORE relative%d index%d\n",rel,ns);ns++;
     }
     if(e.__PVT__pv_v){
      if(firstp<0)firstp=rel;lastp=rel;
      if(np>=8||e.__PVT__pv_c!=np||e.__PVT__pv_f!=0)errors++;
      for(int k=0;k<32;k++)if(e.__PVT__pv_y[k]!=(k%8==0?0x42000000U:0U)){if(errors<4)printf("REPLAY_PV_MISMATCH beat%d lane%d got%08x\n",np,k,e.__PVT__pv_y[k]);errors++;}
      printf("REPLAY_PV relative%d index%d head0%08x\n",rel,np,e.__PVT__pv_y[0]);np++;
     }
     if(u.__PVT__pv_ov){
      if(firstd<0)firstd=rel;lastd=rel;drains++;
      if(u.__PVT__p_i!=drains%5)errors++;
      if(u.__PVT__p_i==1)dh++;else db++;
      if(drains<=5)printf("REPLAY_DRAIN_SLOT relative%d nextIndex%u\n",rel,u.__PVT__p_i);
     }
     unsigned af=s->TOP__tb_svc_native_programme__u__u_eng__g_tr__BRA__0__KET____DOT__g_xb__DOT__u_band__u_t__u_hc__u_expand.__PVT__fault|s->TOP__tb_svc_native_programme__u__u_eng__g_tr__BRA__1__KET____DOT__g_xb__DOT__u_band__u_t__u_hc__u_expand.__PVT__fault|s->TOP__tb_svc_native_programme__u__u_eng__g_tr__BRA__2__KET____DOT__g_xb__DOT__u_band__u_t__u_hc__u_expand.__PVT__fault|s->TOP__tb_svc_native_programme__u__u_eng__g_tr__BRA__3__KET____DOT__g_xb__DOT__u_band__u_t__u_hc__u_expand.__PVT__fault;
     if(af)affaults++;
    }
   }
  }
  top->eval();
  if(next_rise&&tb.__PVT__rst_n&&u.__PVT__pw!=prevpw){if(u.__PVT__pw!=prevpw+1)errors++;if(firstword<0)firstword=cycle-origin;lastword=cycle-origin;pwseen++;printf("REPLAY_FRAME_BODY cycle%d relative%d acceptedWords%u\n",cycle,cycle-origin,unsigned(u.__PVT__pw));prevpw=u.__PVT__pw;}
  if(cycle>expected_go+1080)break;
 }
 if(origin!=expected_go||phase!=1||ns!=8||np!=8||qa!=8||ka!=8||pa!=4||drains!=40||dh!=8||db!=32||pwseen!=8||firstword!=726||lastword!=740||u.__PVT__pw!=8||u.__PVT__pr!=8||!u.__PVT__done||u.__PVT__fc||affaults)errors++;
 printf("RETURNED_P_REPLAY driverInterpositions%d GO%d phase%d Q%d KV%d Paccept%d score%d PV%d frameWords%d pw%u pr%u drain%d headers%d bodies%d scoreDates%d:%d PVDates%d:%d drainDates%d:%d inputDates%d:%d done%u fc%08x afSamples%d errors%d\n",driver_interpositions,origin,phase,qa,ka,pa,ns,np,pwseen,u.__PVT__pw,u.__PVT__pr,drains,dh,db,firsts,lasts,firstp,lastp,firstd,lastd,firstword,lastword,u.__PVT__done,u.__PVT__fc,affaults,errors);
 printf("REPLAY_SCOPE cached_tagj_and_pv_od_unobservable; raw_PV_exact; drain_slots_only\n");
 printf("RETURNED_P_REPLAY %s\n",errors?"FAIL":"PASS");top->final();delete top;delete ctx;return errors?1:0;
}
