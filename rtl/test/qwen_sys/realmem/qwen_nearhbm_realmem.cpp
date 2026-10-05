#include "Vot_qwen_nearhbm_sys_tb.h"
#include "Vmem.h"
#include "Vmem___024root.h"
#include "verilated.h"
#include "mem_access.hpp"
#include "fullshape_context.hpp"
#include <algorithm>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>
static uint64_t bits(const uint32_t* a,int b,int n){uint64_t v=0;for(int k=0;k<n;k++)v|=uint64_t((a[(b+k)/32]>>((b+k)%32))&1)<<k;return v;}
static void put(uint32_t* a,int b,int n,uint64_t v){for(int k=0;k<n;k++){uint32_t m=1u<<((b+k)%32);if((v>>k)&1)a[(b+k)/32]|=m;else a[(b+k)/32]&=~m;}}
static uint32_t expand(uint8_t u){uint32_t s=uint32_t(u>>7)<<31;int e=(u>>3)&15,m=u&7;if(!e){if(!m)return s;e=-6;while(m<8){m<<=1;--e;}return s|uint32_t(e+127)<<23|uint32_t(m-8)<<20;}return s|uint32_t(e+120)<<23|uint32_t(m)<<20;}
int main(int argc,char** argv){
 if(argc!=2)return 2;Verilated::commandArgs(argc,argv);std::string dir=argv[1];
 std::ifstream fmeta(dir+"/meta.json");std::string meta((std::istreambuf_iterator<char>(fmeta)),{});auto at=meta.find("\"ctx\":");int T=atoi(meta.c_str()+at+6),P=T-1;
 if(T!=129){fprintf(stderr,"This connected measurement is pinned to context129/position128\n");return 2;}
 std::vector<uint16_t> q;{std::ifstream f(dir+"/q.hex");std::string s;while(f>>s)q.push_back(strtoul(s.c_str(),0,16));}
 std::vector<std::vector<uint8_t>> kv[2];{std::ifstream f(dir+"/kv.hex");std::string s;int n=0;while(f>>s){std::vector<uint8_t>a(128);for(int d=0;d<128;d++)a[d]=strtoul(s.substr(2*(127-d),2).c_str(),0,16);kv[n++<2*T?0:1].push_back(a);}}
 std::vector<uint32_t> gold;{std::ifstream f(dir+"/gold.hex");std::string s;while(f>>s)gold.push_back(strtoul(s.c_str(),0,16));}
 if(q.size()!=1024 || gold.size()!=1024 || kv[0].size()!=2*T || kv[1].size()!=2*T)return 2;
 Vot_qwen_nearhbm_sys_tb near;Vmem mem;near.clk=near.hclk=0;near.rst_n=near.hrst_n=0;near.start=near.q_valid=0;near.T=T;near.flip_period=0;
 mem.clk=mem.rst_n=mem.start=0;mem.pos=P;mem.layer=0;mem.kv_we=0;mem.probe_re=0;mem.probe_tile=mem.probe_addr=0;mem.row_valid=0;
 near.eval();mem.eval();
 // Only history before P is preloaded. Token P reaches HBM solely by actual
 // kv_we writes and tagged WR_ACK; the host never serves a requested row.
 for(int s=0;s<4;s++)for(int a=0;a<131072;a++)for(int w=0;w<8;w++)mem_word(mem,s,a,w)=0;
 // Use the adopted full-shape context codec; never reduced sys-die aliases.
 auto location=[&](int v,int g,int t,int d){
   return qwen_combined::locate({0,0,unsigned(t),0},v?qwen_combined::Kind::V:qwen_combined::Kind::K,unsigned(g),unsigned(d));
 };
 for(int v=0;v<2;v++)for(int g=0;g<2;g++)for(int t=0;t<P;t++)for(int d=0;d<128;d++){
   auto home=location(v,g,t,d);int a=home.sector_address,b=home.byte_in_sector,s=home.stack;auto &w=mem_word(mem,s,a,b/4);w=(w&~(255u<<(8*(b%4))))|(uint32_t(kv[v][2*t+g][d])<<(8*(b%4)));
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
 uint64_t mem_start=cf;mem.start=1;hf();mem.start=0;
 bool drain_low=false;uint64_t last_write_input=0,ready_at=0,first_row_return=0;
 // Same SW64 element-write API as the REAL_MEM runtime; current token K then V.
 for(int v=0;v<2;v++)for(int block=0;block<4;block++){
   mem.kv_we=~uint64_t(0);
   for(int l=0;l<64;l++){int x=block*64+l,g=x/128,d=x%128;
     int scalar=location(v,g,P,d).scalar_address;
     put(mem.kv_waddr.data(),l*24,24,scalar);put(mem.kv_wdata.data(),l*32,32,expand(kv[v][2*P+g][d]));
   }hf();if(!mem.kv_write_drained)drain_low=true;
 }mem.kv_we=0;last_write_input=cf;
 while(!(mem.kv_ok&&mem.kv_write_drained)&&!mem.fault){hf();if(!mem.kv_write_drained)drain_low=true;}ready_at=cf;
 if(mem.fault){fprintf(stderr,"memory fault before attention kv=%x\n",mem.kv_fault_code);return 1;}
 uint64_t begin=cf;near.start=1;ff();near.start=0;
 int qb=0,nout=0,mismatch=0;std::vector<uint32_t> got(1024,0xdeadbeef);std::vector<int> count(1024);
 while(nout<1024 && !mem.fault && !near.fault && !near.sys_fault){
   near.q_valid=qb<32;near.q_beat=qb;
   if(qb<32){for(int l=0;l<32;l++)put(near.q_data.data(),16*l,16,q[qb*32+l]);qb++;}
   ff();if(mem.row_rsp_valid && !first_row_return)first_row_return=cf;
   if(near.out_valid){int g=near.out_g,beat=near.out_beat,h=4*g+beat/8,d0=16*(beat%8);for(int l=0;l<16;l++){int i=h*128+d0+l;got[i]=bits(near.out_data.data(),32*l,32);count[i]++;nout++;}}
   if(cf%100000==0){fprintf(stderr,"progress cycles=%llu output=%d kv_ok=%d drained=%d\n",(unsigned long long)cf,nout,int(mem.kv_ok),int(mem.kv_write_drained));fflush(stderr);}
 }near.q_valid=0;uint64_t attention_cycles=cf-begin;
 for(int i=0;i<1024;i++)if(count[i]!=1||got[i]!=gold[i])mismatch++;
 // Read the actual HBM arrays and tile SRAM ports AFTER measurement.
 int wb_bad=0,slice_bad=0;
 for(int v=0;v<2;v++)for(int g=0;g<2;g++)for(int t=0;t<T;t++)for(int d=0;d<128;d++){
   auto home=location(v,g,t,d);int a=home.sector_address,b=home.byte_in_sector,s=home.stack;if(((mem_word(mem,s,a,b/4)>>(8*(b%4)))&255)!=kv[v][2*t+g][d])wb_bad++;
 }
 for(int v=0;v<2;v++)for(int g=0;g<2;g++)for(int d=0;d<128;d++){
   auto home=location(v,g,P,d);int tile=home.tile,loc=home.slice_word,b=home.byte_in_slice;
   mem.probe_re=1;mem.probe_tile=tile;mem.probe_addr=loc;hf();hf();hf();
   if(bits(mem.probe_data.data(),b*8,8)!=kv[v][2*P+g][d])slice_bad++;
 }mem.probe_re=0;
 bool good=nout==1024&&mismatch==0&&wb_bad==0&&slice_bad==0&&!mem.fault&&!near.fault&&!near.sys_fault&&mem.row_drained&&mem.kv_ok&&mem.kv_write_drained&&drain_low&&mem.st_wr_sectors==136&&first_row_return>=ready_at;
 printf("{\"status\":\"%s\",\"context\":129,\"position\":128,\"outputs\":%d,\"mismatches\":%d,\"HBM_bytes_mismatched\":%d,\"token_slice_codes_mismatched\":%d,\"attention_cycles\":%llu,\"memory_start_cycle\":%llu,\"last_write_input_cycle\":%llu,\"real_memory_ready_cycle\":%llu,\"first_row_return_cycle\":%llu,\"write_sectors\":%u,\"max_write_ACK_latency\":%u,\"fill_sectors\":%u,\"kv_fault\":%u,\"memory_fault\":%u,\"near_fault\":%u,\"sys_fault\":%u,\"drain_low_observed\":%s}\n",good?"pass":"fail",nout,mismatch,wb_bad,slice_bad,(unsigned long long)attention_cycles,(unsigned long long)mem_start,(unsigned long long)last_write_input,(unsigned long long)ready_at,(unsigned long long)first_row_return,mem.st_wr_sectors,mem.st_wr_lat_max,mem.st_fill_sectors,mem.kv_fault_code,mem.fault,near.fault,near.sys_fault,drain_low?"true":"false");
 return good?0:1;
}
