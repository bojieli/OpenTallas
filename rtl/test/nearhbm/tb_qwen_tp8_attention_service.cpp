#include "Vot_qwen_tp8_attention_service.h"
#include "verilated.h"
#include <vector>
#include <deque>
#include <fstream>
#include <string>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
static uint64_t bits(const uint32_t*v,int off,int n){uint64_t z=0;for(int i=0;i<n;i++)z|=uint64_t((v[(off+i)/32]>>((off+i)%32))&1)<<i;return z;}
static void put(uint32_t*v,int off,int n,uint64_t z){for(int i=0;i<n;i++){uint32_t m=1u<<((off+i)%32);v[(off+i)/32]=(v[(off+i)/32]&~m)|(((z>>i)&1)?m:0);}}
template<typename T>static uint64_t bits(const T&v,int o,int n){return (uint64_t(v)>>o)&((uint64_t(1)<<n)-1);}
template<typename T>static void put(T&v,int o,int n,uint64_t z){uint64_t m=((uint64_t(1)<<n)-1)<<o;v=T((uint64_t(v)&~m)|((z<<o)&m));}
template<size_t N>static uint64_t bits(const VlWide<N>&v,int o,int n){return bits(v.data(),o,n);}
template<size_t N>static void put(VlWide<N>&v,int o,int n,uint64_t z){put(v.data(),o,n,z);}
struct Return{int t,slot;uint64_t at;};
int main(int argc,char**argv){
 if(argc<2)return 2;std::string d=argv[1],mode=argc>2?argv[2]:"steady";
 std::vector<uint32_t>q,gold;std::vector<std::vector<uint8_t>>kv;
 auto load=[&](const std::string& path){
  q.clear();gold.clear();kv.clear();
  for(auto spec:{std::make_pair("q.hex",&q),std::make_pair("gold.hex",&gold)}){std::ifstream f(path+"/"+spec.first);std::string x;while(f>>x)spec.second->push_back(strtoul(x.c_str(),0,16));}
  std::ifstream f(path+"/kv.hex");std::string x;while(f>>x){if(x.size()!=256)return false;std::vector<uint8_t>r(128);for(int j=0;j<128;j++)r[j]=strtoul(x.substr(2*(127-j),2).c_str(),0,16);kv.push_back(r);}
  return q.size()==512&&gold.size()==512&&kv.size()%2==0&&kv.size()>=2&&kv.size()<=16384;
 };
 if(!load(d))return 2;int ctx=kv.size()/2;
 Vot_qwen_tp8_attention_service t;uint64_t cy=0;auto tick=[&](){t.clk=0;t.eval();t.clk=1;t.eval();cy++;};
 t.rst_n=0;t.request_valid=0;t.q_valid=0;t.k_rsp_valid=0;t.v_rsp_valid=0;t.k_req_ready=0;t.v_req_ready=0;t.result_ready=0;t.fused_program_capability=1;
 for(int i=0;i<8;i++)tick();t.rst_n=1;for(int i=0;i<(mode=="coldboot"?0:(mode=="idle"?2000:80));i++)tick();
 bool stalls=mode=="stalls";bool scheduled=mode=="scheduled"||mode=="schedule_late";bool mutant=mode!="steady"&&mode!="stalls"&&mode!="restart"&&mode!="coldboot"&&mode!="idle"&&mode!="scheduled";
 unsigned outputs=0,errors=0,epochs=0;uint64_t kcount=0,vcount=0,first=cy;bool changed=false;
 for(int round=0;round<(mode=="restart"?2:1);round++){
  if(round&&argc>3){if(!load(argv[3]))return 2;ctx=kv.size()/2;}
  int epoch=17+round,layer=6+round;
  t.request_epoch=epoch;t.request_layer=layer;t.request_position=ctx-1-(mode=="context");t.fused_program_capability=mode!="capability";t.request_valid=1;
  bool took=false;for(int wait=0;wait<200&&!took&&!t.fault;wait++){t.clk=0;t.eval();took=t.request_ready;tick();}
  t.request_valid=0;
  const uint64_t frame_k=kcount,frame_v=vcount;
  bool qheld=false,result_held=false;unsigned held_beat=0,held_epoch=0,held_layer=0;
  uint32_t held_data[16]={0};uint32_t khold=0;unsigned vhold=0;uint16_t kt_hold[32]={0},vt_hold[4]={0};unsigned vs_hold[4]={0};
  int qb=0,ob=0;std::deque<Return>kq[32],vq[4];
  for(unsigned step=0;step<250000;step++){
   t.clk=0;t.eval();
   if(scheduled)qb=step>0?int(step-1):0;
   t.q_valid=scheduled?(step>=1&&step<=32):(qb<32&&(qheld||!stalls||cy%7!=0));t.q_beat=qb;
   if(mode=="schedule_late"&&step==9)t.q_valid=0;
   for(int j=0;j<16;j++)t.q_data[j]=q[qb<32?qb*16+j:j];
   if(mode=="q_order"&&qb==7)t.q_beat=6;
   if(mode=="precision")for(int j=0;j<16;j++)t.q_data[j]&=0xffff0000u; // wrong early BF16 truncation replaces lossless FP32 transport
   t.k_req_ready=0;for(int i=0;i<32;i++)if(!stalls||(cy+i)%11!=0)t.k_req_ready|=1u<<i;
   t.v_req_ready=0;for(int i=0;i<4;i++)if(!stalls||(cy+i)%13!=0)t.v_req_ready|=1u<<i;
   t.result_ready=!stalls||cy%5!=0;t.k_rsp_valid=0;t.v_rsp_valid=0;
   for(int i=0;i<32;i++)if(!kq[i].empty()&&kq[i].front().at<=cy&&(!stalls||(cy+i)%9!=0)){
    auto r=kq[i].front();kq[i].pop_front();t.k_rsp_valid|=1u<<i;put(t.k_rsp_t,13*i,13,r.t);put(t.k_rsp_epoch,16*i,16,epoch);put(t.k_rsp_layer,6*i,6,layer);
    if(!changed&&mode=="k_epoch"){put(t.k_rsp_epoch,16*i,16,epoch-1);changed=true;}
    if(!changed&&mode=="k_order"){put(t.k_rsp_t,13*i,13,r.t+1);changed=true;}
    for(int j=0;j<128;j++)put(t.k_rsp_data,1024*i+8*j,8,kv[r.t][j]);
   }
   for(int i=0;i<4;i++)if(!vq[i].empty()&&vq[i].front().at<=cy&&(!stalls||(cy+i)%7!=0)){
    // Ready/valid return producer holds ownership while backpressured.
    auto r=vq[i].front();t.v_rsp_valid|=1u<<i;put(t.v_rsp_t,14*i,14,r.t);put(t.v_rsp_slot,3*i,3,r.slot);put(t.v_rsp_epoch,16*i,16,epoch);put(t.v_rsp_layer,6*i,6,layer);
    if(!changed&&mode=="v_epoch"){put(t.v_rsp_epoch,16*i,16,epoch-1);changed=true;}
    for(int j=0;j<128;j++)put(t.v_rsp_data,1024*i+8*j,8,kv[ctx+r.t][j]);
   }
   t.eval();if(scheduled&&t.q_valid&&!t.q_ready)errors++;bool qt=t.q_valid&&t.q_ready;qheld=t.q_valid&&!t.q_ready;
   if(result_held){if(!t.result_valid||t.result_beat!=held_beat||t.result_epoch!=held_epoch||t.result_layer!=held_layer)errors++;for(int j=0;j<16;j++)if(t.result_data[j]!=held_data[j])errors++;}
   result_held=t.result_valid&&!t.result_ready;
   if(result_held){held_beat=t.result_beat;held_epoch=t.result_epoch;held_layer=t.result_layer;for(int j=0;j<16;j++)held_data[j]=t.result_data[j];}
   for(int i=0;i<32;i++){if((khold&(1u<<i))&&(!(t.k_req_valid&(1u<<i))||bits(t.k_req_t,13*i,13)!=kt_hold[i]))errors++;kt_hold[i]=bits(t.k_req_t,13*i,13);}
   khold=t.k_req_valid&~t.k_req_ready;
   for(int i=0;i<4;i++){if((vhold&(1u<<i))&&(!(t.v_req_valid&(1u<<i))||bits(t.v_req_t,14*i,14)!=vt_hold[i]||bits(t.v_req_slot,3*i,3)!=vs_hold[i]))errors++;vt_hold[i]=bits(t.v_req_t,14*i,14);vs_hold[i]=bits(t.v_req_slot,3*i,3);}
   vhold=t.v_req_valid&~t.v_req_ready;
   for(int i=0;i<32;i++)if((t.k_req_valid&t.k_req_ready)&(1u<<i)){int pos=bits(t.k_req_t,13*i,13);if(pos>=ctx)return 3;kq[i].push_back({pos,0,cy+16});kcount++;}
   for(int i=0;i<4;i++)if((t.v_req_valid&t.v_req_ready)&(1u<<i)){int pos=bits(t.v_req_t,14*i,14),slot=bits(t.v_req_slot,3*i,3);if(pos>=ctx)return 3;vq[i].push_back({pos,slot,cy+16+(stalls?slot%3:0)});vcount++;}
   for(int i=0;i<4;i++)if((t.v_rsp_valid&t.v_rsp_ready)&(1u<<i))vq[i].pop_front();
   if(t.result_valid&&t.result_ready){if(t.result_beat!=ob||t.result_epoch!=epoch||t.result_layer!=layer)errors++;
    for(int j=0;j<16;j++){unsigned got=t.result_data[j],want=gold[16*ob+j];if(got!=want){if(errors<8)fprintf(stderr,"word %d got %08x want %08x\n",16*ob+j,got,want);errors++;}}
    ob++;outputs+=16;
   }
   tick();if(qt)qb++;
   if(t.fault)break;
   if(t.result_done){epochs++;break;}
  }
  if(!mutant&&(kcount-frame_k!=unsigned(ctx)||vcount-frame_v!=unsigned(ctx)))errors++;
  if(t.fault||ob!=32)break;for(int j=0;j<20;j++)tick();
 }
 bool observed=t.fault||errors>0;bool exact=!t.fault&&errors==0&&outputs==512*(mode=="restart"?2:1)&&epochs==(mode=="restart"?2:1);
 printf("{\"scope\":\"FUNCTIONAL_FUSED_ATTENTION_NOT_PHYSICAL_OR_FULL_TOKEN\",\"mode\":\"%s\",\"exact\":%s,\"fault\":%u,\"data_errors\":%u,\"output_words\":%u,\"epochs\":%u,\"k_rows\":%llu,\"v_rows\":%llu,\"cycles\":%llu,\"qualified_hbm_timing\":false}\n",mode.c_str(),exact?"true":"false",unsigned(t.fault),errors,outputs,epochs,(unsigned long long)kcount,(unsigned long long)vcount,(unsigned long long)(cy-first));
 return (mutant?observed:exact)?0:1;
}
