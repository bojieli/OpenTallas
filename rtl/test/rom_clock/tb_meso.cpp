#include "Vot_meso_fifo.h"
#include "verilated.h"
#include <cstdint>
#include <cmath>
#include <deque>
#include <iostream>
#include <stdexcept>
#include <string>
#include <algorithm>
struct Word {uint64_t id,t;};
uint32_t data(uint64_t id,int lane){return uint32_t((id*0x9e3779b97f4a7c15ULL)>>(lane%31)) ^ uint32_t(0x13579bdfU*uint32_t(lane+1));}
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);int phase=argc>1?std::stoi(argv[1]):0;std::string mode=argc>2?argv[2]:"stream";int goal=argc>3?std::stoi(argv[3]):20000;
 Vot_meso_fifo d;d.wclk=0;d.rclk=0;d.wrst_n=0;d.rrst_n=0;d.w_v=0;d.r_rdy=0;d.eval();
 std::deque<Word> q;uint64_t id=1,accepted=0,taken=0,minlat=~0ULL,maxlat=0,lasttake=0,firsttake=0;
 uint64_t nw=0,nr=phase,wedge=0,redge=0,t=0;bool wl=false,rl=false;bool faultSeen=false;uint64_t faultAt=0;
 bool recovery=false;uint64_t resetEnd=0;int resets=0;uint64_t rng=0x1234abcd,flushed=0;
 try{
 for(uint64_t events=0;events<40000000;events++){
  t=std::min(nw,nr);bool we=nw==t,re=nr==t;bool wrise=we&&!wl,rrise=re&&!rl;
  if(we){wl=!wl;nw+=5000;}
  if(re){rl=!rl;redge+=rrise;double wander=mode=="wander"?2304*std::sin(double(redge)*.017):0;
   double prev=mode=="wander"?2304*std::sin(double(redge-uint64_t(rrise))*.017):0;
   int64_t half=5000;
   if(mode=="drift" && redge>80)half=4500;
   if(mode=="stop" && redge>80)half=10000000;
   if(rrise && mode=="wander")half+=int64_t(wander-prev);
   nr+=uint64_t(std::max<int64_t>(half,100));}
  if(wrise)wedge++;
  d.wrst_n=wedge>=12;d.rrst_n=redge>=12;
  if(mode=="reset" && resets<12 && accepted>=uint64_t((resets+1)*500) && !q.empty()){
   if(!recovery){recovery=true;resetEnd=t+180000;flushed+=q.size();q.clear();resets++;}
  }
  if(recovery){d.wrst_n=!(resets%2) || t>resetEnd-150000;d.rrst_n=(resets%2) || t>resetEnd-150000;d.w_v=0;d.r_rdy=0;
   if(t>=resetEnd){recovery=false;q.clear();}}
  rng^=rng<<13;rng^=rng>>7;rng^=rng<<17;
  bool live=d.w_live&&d.r_live&&!recovery;
  bool sparse=mode=="sparse";
  d.w_v=live && accepted<uint64_t(goal) && (!sparse||q.empty()) && (mode!="stall"||(rng&3)!=0);
  d.r_rdy=live && (mode!="stall"||((rng>>4)&7)<3);
  for(int lane=0;lane<16;lane++)d.w_d[lane]=data(id,lane);
  d.eval();
  bool push=wrise&&d.w_v&&d.w_rdy,pop=rrise&&d.r_v&&d.r_rdy;
  if(pop){if(q.empty())throw std::runtime_error("uncredited/old epoch result");auto x=q.front();q.pop_front();
   for(int lane=0;lane<16;lane++)if(d.r_d[lane]!=data(x.id,lane))throw std::runtime_error("payload/order mismatch");
   uint64_t lat=t-x.t;minlat=std::min(minlat,lat);maxlat=std::max(maxlat,lat);taken++;lasttake=t;if(!firsttake)firsttake=t;
  }
  if(push){q.push_back({id++,t});accepted++;}
  if(q.size()>4)throw std::runtime_error("credit returned before consumer: capacity exceeded");
  d.wclk=wl;d.rclk=rl;d.eval();
  if(d.w_fault||d.r_fault){if(!faultSeen){faultSeen=true;faultAt=t;}
   if(mode!="drift"&&mode!="stop")throw std::runtime_error("spurious drift/protocol fault");
   if(t>faultAt+100000){if(d.w_rdy || (mode!="stop" && d.r_v))throw std::runtime_error("fault not fail-closed");break;}
  }
  if(accepted==uint64_t(goal)&&q.empty()&&!recovery)break;
 }
 if(mode=="drift"||mode=="stop"){if(!faultSeen)throw std::runtime_error("drift/clock loss not detected");}
 else if(accepted!=uint64_t(goal)||!q.empty()||taken+flushed!=accepted)throw std::runtime_error("campaign failed to drain");
 std::cout<<"{\"phase\":"<<phase<<",\"mode\":\""<<mode<<"\",\"accepted\":"<<accepted<<",\"taken\":"<<taken<<",\"min_cycles\":"<<double(minlat)/10000<<",\"max_cycles\":"<<double(maxlat)/10000<<",\"words_per_cycle\":"<<(lasttake>firsttake?double(taken-1)*10000/(lasttake-firsttake):0)<<",\"fault\":"<<(faultSeen?"true":"false")<<",\"flushed\":"<<flushed<<",\"resets\":"<<resets<<",\"status\":\"PASS_DIGITAL_ONLY\"}\n";
 return 0;
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<" phase="<<phase<<" mode="<<mode<<" t="<<t<<" accepted="<<accepted<<" taken="<<taken<<"\n";return 1;}
}
