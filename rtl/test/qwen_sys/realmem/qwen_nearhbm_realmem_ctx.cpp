// Long-context successor of qwen_nearhbm_realmem.cpp (pinned to context 129, untouched): the passed near-HBM
// subsystem (hub_p + stack_p, R = 8, layer-start fence) on the REAL_MEM service + four actual HBM timing/WR_ACK
// models, at any context, over a chain of layers, with the token K/V written at the layer program's own points.
//
//   usage: connected_ctx GATE T_V T_K1 GAP_K2 SUFFIX VECDIR...
//     GATE    kvok    near start waits for kv_ok && kv_write_drained (the adapter/combined-top gate as built)
//             drained near start waits for kv_write_drained of the token only
//     T_V     fast-clock cycles from layer start to the V write (img256 PC 3, measured in the REAL_MEM baseline)
//     T_K1    ... to the first K-half write (PC 8, after q/k norm and RoPE)
//     GAP_K2  cycles from the K-half-1 write-done to the K-half-2 write (PC 10; the baseline's drain barrier + PC 9)
//     SUFFIX  cycles from the attention output to the next layer's start (the measured O projection .. layer end)
//     VECDIR  one per chained layer (tools/qwen_nearhbm_ctx_vectors_gpu.py; same context, layers in order)
//
// Only history before P is preloaded.  Token P reaches HBM solely by the actual kv_we writes and tagged WR_ACK;
// the host never serves a requested row.  Every output, every HBM byte (all layers, positions 0..P) and the last
// layer's token slice codes are checked after measurement.
#include "Vot_qwen_nearhbm_sys_tb.h"
#include "Vmem.h"
#include "Vmem___024root.h"
#include "verilated.h"
#include "mem_access.hpp"
#include "fullshape_context.hpp"
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>
static uint64_t bits(const uint32_t* a,int b,int n){uint64_t v=0;for(int k=0;k<n;k++)v|=uint64_t((a[(b+k)/32]>>((b+k)%32))&1)<<k;return v;}
static void put(uint32_t* a,int b,int n,uint64_t v){for(int k=0;k<n;k++){uint32_t m=1u<<((b+k)%32);if((v>>k)&1)a[(b+k)/32]|=m;else a[(b+k)/32]&=~m;}}
static uint32_t expand(uint8_t u){uint32_t s=uint32_t(u>>7)<<31;int e=(u>>3)&15,m=u&7;if(!e){if(!m)return s;e=-6;while(m<8){m<<=1;--e;}return s|uint32_t(e+127)<<23|uint32_t(m-8)<<20;}return s|uint32_t(e+120)<<23|uint32_t(m)<<20;}
static int jint(const std::string& j,const char* k){auto at=j.find(std::string("\"")+k+"\":");if(at==std::string::npos){fprintf(stderr,"meta lacks %s\n",k);exit(2);}return atoi(j.c_str()+at+strlen(k)+3);}
struct Layer{int n;std::vector<uint16_t> q;std::vector<std::vector<uint8_t>> kv[2];std::vector<uint32_t> gold;};
int main(int argc,char** argv){
 if(argc<7)return 2;Verilated::commandArgs(argc,argv);
 std::string gate=argv[1];const bool kvok_gate=gate=="kvok";if(!kvok_gate&&gate!="drained")return 2;
 const long tV=atol(argv[2]),tK1=atol(argv[3]),gapK2=atol(argv[4]),suffix=atol(argv[5]);
 std::vector<Layer> L;int T=-1;
 for(int i=6;i<argc;i++){
   std::string dir=argv[i];std::ifstream fm(dir+"/meta.json");std::string meta((std::istreambuf_iterator<char>(fm)),{});
   int t=jint(meta,"ctx");if(T<0)T=t;else if(t!=T){fprintf(stderr,"chained layers must share the context\n");return 2;}
   Layer y;y.n=jint(meta,"layer");
   {std::ifstream f(dir+"/q.hex");std::string s;while(f>>s)y.q.push_back(strtoul(s.c_str(),0,16));}
   {std::ifstream f(dir+"/kv.hex");std::string s;long n=0;while(f>>s){std::vector<uint8_t>a(128);for(int d=0;d<128;d++)a[d]=strtoul(s.substr(2*(127-d),2).c_str(),0,16);y.kv[n++<2L*T?0:1].push_back(a);}}
   {std::ifstream f(dir+"/gold.hex");std::string s;while(f>>s)y.gold.push_back(strtoul(s.c_str(),0,16));}
   if(y.q.size()!=1024||y.gold.size()!=1024||y.kv[0].size()!=size_t(2*T)||y.kv[1].size()!=size_t(2*T)){fprintf(stderr,"bad vectors %s\n",dir.c_str());return 2;}
   if(!L.empty()&&y.n<=L.back().n){fprintf(stderr,"layers must increase\n");return 2;}
   L.push_back(std::move(y));
 }
 const int P=T-1;
 if(T<2||T>8192)return 2;
 Vot_qwen_nearhbm_sys_tb near;Vmem mem;near.clk=near.hclk=0;near.rst_n=near.hrst_n=0;near.start=near.q_valid=0;near.T=T;near.flip_period=0;
 mem.clk=mem.rst_n=mem.start=0;mem.pos=P;mem.layer=L[0].n;mem.kv_we=0;mem.probe_re=0;mem.probe_tile=mem.probe_addr=0;mem.row_valid=0;
 near.eval();mem.eval();
 const int MW=1<<19;   // the bench top's MEM_WORDS (address mod MEM_WORDS inside the model)
 for(int s=0;s<4;s++)for(int a=0;a<MW;a++)for(int w=0;w<8;w++)mem_word(mem,s,a,w)=0;
 auto location=[&](int n,int v,int g,int t,int d){
   return qwen_combined::locate({0,unsigned(n),unsigned(t),0},v?qwen_combined::Kind::V:qwen_combined::Kind::K,unsigned(g),unsigned(d));
 };
 auto byte_ref=[&](int n,int v,int g,int t,int d)->uint32_t&{auto h=location(n,v,g,t,d);if(h.sector_address>=uint32_t(MW)){fprintf(stderr,"address beyond MEM_WORDS\n");exit(2);}return mem_word(mem,h.stack,h.sector_address,h.byte_in_sector/4);};
 for(auto& y:L)for(int v=0;v<2;v++)for(int g=0;g<2;g++)for(int t=0;t<P;t++)for(int d=0;d<128;d++){
   auto h=location(y.n,v,g,t,d);uint32_t& w=byte_ref(y.n,v,g,t,d);int b=h.byte_in_sector;w=(w&~(255u<<(8*(b%4))))|(uint32_t(y.kv[v][2*t+g][d])<<(8*(b%4)));
 }
 uint64_t cf=0,ch=0,tf=833333,th=300000;
 auto step=[&](){int edges=(tf<=th?1:0)|(th<=tf?2:0);near.clk=near.hclk=0;mem.clk=0;near.eval();mem.eval();
   mem.row_valid=near.req_valid;mem.row_v=near.req_v;mem.row_g=near.req_g;mem.row_t=near.req_t;
   near.rsp_valid=mem.row_rsp_valid;near.rsp_data=mem.row_rsp_data;
   near.clk=edges&1?1:0;near.hclk=edges&2?1:0;mem.clk=edges&2?1:0;near.eval();mem.eval();
   if(edges&1){tf+=833333;cf++;}if(edges&2){th+=1024000;ch++;}return edges;};
 auto hf=[&](){while(!(step()&2)){};};auto ff=[&](){while(!(step()&1)){};};
 for(int n=0;n<8;n++)ff();near.rst_n=near.hrst_n=mem.rst_n=1;
 while(!near.links_up)ff();for(int n=0;n<16;n++)ff();
 bool all_good=true;std::string recs;
 uint32_t prev_fill=0,prev_wr=0;
 uint64_t next_start=cf;
 for(size_t li=0;li<L.size();li++){
   Layer& y=L[li];
   // the next layer starts at its scheduled cycle, and never before the service has retired the previous layer
   uint64_t sched=next_start;bool waited=false;
   while(cf<next_start)ff();
   if(li)while(!(mem.kv_ok&&mem.kv_write_drained&&mem.row_drained)&&!mem.fault){ff();waited=true;}
   mem.layer=y.n;mem.pos=P;
   const uint64_t L0=cf;mem.start=1;hf();mem.start=0;
   bool drain_low=false;
   // the token's K/V, as the layer program writes it through the SW64 element-write port:
   //   PC 3: V, head 0 then head 1 (128 dims: 2 beats each); PC 8: K dims 0..63 of heads 0,1; PC 10: K dims 64..127
   bool group_low=false;
   auto write_group=[&](int v,const std::vector<std::pair<int,int>>& beats){
     group_low=false;
     for(auto [g,d0]:beats){mem.kv_we=~uint64_t(0);
       for(int l=0;l<64;l++){int d=d0+l;put(mem.kv_waddr.data(),l*24,24,location(y.n,v,g,P,d).scalar_address);put(mem.kv_wdata.data(),l*32,32,expand(y.kv[v][2*P+g][d]));}
       hf();if(!mem.kv_write_drained)drain_low=group_low=true;}
     mem.kv_we=0;};
   // the group's write-done: kv_write_drained must first fall (the data is outstanding), then rise on the last WR_ACK
   auto wait_drained=[&](){for(int n=0;!group_low&&n<256&&!mem.fault;n++){hf();if(!mem.kv_write_drained)drain_low=group_low=true;}
     if(!group_low){fprintf(stderr,"token write never became outstanding\n");exit(1);}
     while(!mem.kv_write_drained&&!mem.fault)hf();return cf;};
   while(cf<L0+tV)ff();uint64_t v_at=cf;write_group(1,{{0,0},{0,64},{1,0},{1,64}});
   while(cf<L0+tK1)ff();uint64_t v_done_seen=0;
   if(mem.kv_write_drained)v_done_seen=cf;
   uint64_t k1_at=cf;write_group(0,{{0,0},{1,0}});
   uint64_t k1_done=wait_drained();
   while(cf<k1_done+gapK2)ff();uint64_t k2_at=cf;write_group(0,{{0,64},{1,64}});uint64_t last_write_input=cf;
   uint64_t k2_done=wait_drained();
   if(kvok_gate)while(!(mem.kv_ok&&mem.kv_write_drained)&&!mem.fault)ff();
   uint64_t ready_at=cf;
   if(mem.fault){fprintf(stderr,"memory fault before attention kv=%x\n",mem.kv_fault_code);return 1;}
   uint64_t begin=cf;near.start=1;ff();near.start=0;
   int qb=0,nout=0,mismatch=0;std::vector<uint32_t> got(1024,0xdeadbeef);std::vector<int> count(1024);
   uint64_t first_row_return=0,first_out=0,fill_done_at=0;
   while(nout<1024&&!mem.fault&&!near.fault&&!near.sys_fault){
     near.q_valid=qb<32;near.q_beat=qb;
     if(qb<32){for(int l=0;l<32;l++)put(near.q_data.data(),16*l,16,y.q[qb*32+l]);qb++;}
     ff();if(mem.row_rsp_valid&&!first_row_return)first_row_return=cf;
     if(mem.kv_ok&&!fill_done_at)fill_done_at=cf;
     if(near.out_valid){if(!first_out)first_out=cf;int g=near.out_g,beat=near.out_beat,h=4*g+beat/8,d0=16*(beat%8);for(int l=0;l<16;l++){int i=h*128+d0+l;got[i]=bits(near.out_data.data(),32*l,32);count[i]++;nout++;}}
     if(cf%100000==0){fprintf(stderr,"progress L%d cycles=%llu output=%d kv_ok=%d drained=%d\n",y.n,(unsigned long long)cf,nout,int(mem.kv_ok),int(mem.kv_write_drained));fflush(stderr);}
   }
   near.q_valid=0;uint64_t end=cf;
   for(int i=0;i<1024;i++)if(count[i]!=1||got[i]!=y.gold[i])mismatch++;
   uint32_t fill_sec=mem.st_fill_sectors-prev_fill,wr_sec=mem.st_wr_sectors-prev_wr;prev_fill=mem.st_fill_sectors;prev_wr=mem.st_wr_sectors;
   bool good=nout==1024&&mismatch==0&&!mem.fault&&!near.fault&&!near.sys_fault&&drain_low&&wr_sec==136&&first_row_return>=ready_at;
   all_good&=good;
   char buf[2048];
   snprintf(buf,sizeof buf,"%s{\"layer\":%d,\"status\":\"%s\",\"outputs\":%d,\"mismatches\":%d,\"scheduled_start\":%llu,\"waited_for_retire\":%s,"
     "\"rel\":{\"v_write\":%llu,\"k1_write\":%llu,\"k1_write_done\":%llu,\"k2_write\":%llu,\"k2_write_done\":%llu,\"near_start\":%llu,\"first_row_return\":%llu,\"first_output\":%llu,\"last_output\":%llu,\"kv_ok\":%lld},"
     "\"attention_cycles\":%llu,\"write_sectors\":%u,\"fill_sectors\":%u,\"fill_cycles_hclk\":%u,\"max_write_ACK_latency_hclk\":%u,\"drain_low_observed\":%s}",
     li?",":"",y.n,good?"pass":"fail",nout,mismatch,(unsigned long long)sched,waited?"true":"false",
     (unsigned long long)(v_at-L0),(unsigned long long)(k1_at-L0),(unsigned long long)(k1_done-L0),(unsigned long long)(k2_at-L0),(unsigned long long)(k2_done-L0),
     (unsigned long long)(begin-L0),(unsigned long long)(first_row_return?first_row_return-L0:0),(unsigned long long)(first_out-L0),(unsigned long long)(end-L0),
     fill_done_at?(long long)(fill_done_at-L0):-1LL,(unsigned long long)(end-begin),wr_sec,fill_sec,mem.st_fill_cycles,mem.st_wr_lat_max,drain_low?"true":"false");
   recs+=buf;(void)v_done_seen;(void)last_write_input;
   fprintf(stderr,"layer %d %s attention=%llu last_output_rel=%llu\n",y.n,good?"pass":"fail",(unsigned long long)(end-begin),(unsigned long long)(end-L0));
   if(!good)break;
   next_start=end+suffix;
 }
 // after measurement: every HBM byte of every chained layer (0..P), and the last layer's token slice codes
 for(int n=0;n<4000&&!(mem.kv_ok&&mem.kv_write_drained&&mem.row_drained);n++)hf();
 long wb_bad=0;int slice_bad=0;
 for(auto& y:L)for(int v=0;v<2;v++)for(int g=0;g<2;g++)for(int t=0;t<T;t++)for(int d=0;d<128;d++){
   auto h=location(y.n,v,g,t,d);if(((byte_ref(y.n,v,g,t,d)>>(8*(h.byte_in_sector%4)))&255)!=y.kv[v][2*t+g][d])wb_bad++;
 }
 const Layer& z=L.back();
 for(int v=0;v<2;v++)for(int g=0;g<2;g++)for(int d=0;d<128;d++){
   auto h=location(z.n,v,g,P,d);
   mem.probe_re=1;mem.probe_tile=h.tile;mem.probe_addr=h.slice_word;hf();hf();hf();
   if(bits(mem.probe_data.data(),h.byte_in_slice*8,8)!=z.kv[v][2*P+g][d])slice_bad++;
 }mem.probe_re=0;
 all_good&=wb_bad==0&&slice_bad==0&&!mem.fault&&mem.row_drained&&mem.kv_ok&&mem.kv_write_drained;
 printf("{\"status\":\"%s\",\"gate\":\"%s\",\"context\":%d,\"position\":%d,\"schedule\":{\"t_v\":%ld,\"t_k1\":%ld,\"gap_k2\":%ld,\"suffix\":%ld},"
        "\"layers\":[%s],\"HBM_bytes_mismatched\":%ld,\"token_slice_codes_mismatched\":%d,\"kv_fault\":%u,\"memory_fault\":%u,\"near_fault\":%u,\"sys_fault\":%u}\n",
        all_good?"pass":"fail",gate.c_str(),T,P,tV,tK1,gapK2,suffix,recs.c_str(),wb_bad,slice_bad,mem.kv_fault_code,mem.fault,near.fault,near.sys_fault);
 return all_good?0:1;
}
