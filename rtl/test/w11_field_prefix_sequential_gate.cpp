#include "Vgate.h"
#include "verilated.h"
#include <array>
#include <deque>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
struct Vec {
 uint32_t a=0x3f800000,b=0x40000000;
 std::array<uint32_t,8> x{},w{};
 int xe=0,we=0; bool fp4=false;
 int ae=-1,mf=-1,tf=-1; int64_t ay=-1,my=-1,ty=-1;
};
struct Exp {bool v=false;int e=-1;int64_t y=-1;};
static uint32_t xs(uint32_t& s){s^=s<<13;s^=s>>17;s^=s<<5;return s;}
static Vec dot(uint8_t x,uint8_t w,int xe=0,bool fp4=false){Vec p;p.x.fill(uint32_t(x)*0x01010101u);p.w.fill(uint32_t(w)*0x01010101u);p.xe=xe;p.fp4=fp4;return p;}
class Gate {
public:
 Vgate dut; uint64_t cycles=0,samples=0,resets=0,held=0,random=0;
 uint64_t av=0,mv=0,tv=0,ab=0,mb=0,tb=0,ae[3]={},mf[2]={},tf[2]={};
 std::deque<Exp> ah=std::deque<Exp>(7),mh=std::deque<Exp>(4),th=std::deque<Exp>(10);
 std::deque<uint32_t> tags=std::deque<uint32_t>(10,0);uint32_t expected_tag=0;
 std::string phase="startup",mismatch;uint32_t latest_tag=0;
 std::string state(const char* prop){std::ostringstream s;s<<"{\"property\":\""<<prop<<"\",\"phase\":\""<<phase<<"\",\"cycle\":"<<cycles<<",\"rst_n\":"<<unsigned(dut.rst_n)<<",\"inputs\":["<<dut.a<<","<<dut.b<<","<<unsigned(dut.fv)<<","<<unsigned(dut.mv)<<","<<unsigned(dut.tv)<<","<<latest_tag<<"],\"reference\":["<<dut.ref_add_y<<","<<unsigned(dut.ref_add_err)<<","<<unsigned(dut.ref_add_v)<<","<<dut.ref_mul_y<<","<<unsigned(dut.ref_mul_fault)<<","<<dut.ref_term_y<<","<<unsigned(dut.ref_term_f)<<","<<unsigned(dut.ref_term_v)<<","<<dut.ref_term_tag<<"],\"candidate\":["<<dut.sim_add_y<<","<<unsigned(dut.sim_add_err)<<","<<unsigned(dut.sim_add_v)<<","<<dut.sim_mul_y<<","<<unsigned(dut.sim_mul_fault)<<","<<dut.sim_term_y<<","<<unsigned(dut.sim_term_f)<<","<<unsigned(dut.sim_term_v)<<","<<dut.sim_term_tag<<"]}";return s.str();}
 void req(bool c,const char* p){if(!c){mismatch=state(p);throw 1;}}
 void compare(){++samples;
 req(dut.ref_add_y==dut.sim_add_y&&dut.ref_add_err==dut.sim_add_err&&dut.ref_add_v==dut.sim_add_v,"fadd_tuple_every_sample");
 req(dut.ref_mul_y==dut.sim_mul_y&&dut.ref_mul_fault==dut.sim_mul_fault,"bmul_tuple_every_sample");
 req(dut.ref_term_y==dut.sim_term_y&&dut.ref_term_f==dut.sim_term_f&&dut.ref_term_v==dut.sim_term_v&&dut.ref_term_tag==dut.sim_term_tag,"bterm_tuple_every_sample");
 if(!dut.rst_n){req(!dut.ref_add_v&&!dut.ref_term_v,"async_valid_reset");req(dut.ref_add_y==0&&dut.ref_add_err==0&&dut.ref_mul_y==0&&!dut.ref_mul_fault,"async_reset_payload");}
 }
 void reset(std::string label){phase=label;dut.clk=0;dut.rst_n=1;dut.eval();dut.rst_n=0;dut.eval();ah=std::deque<Exp>(7);mh=std::deque<Exp>(4);th=std::deque<Exp>(10);++resets;compare();}
 void release(){dut.rst_n=1;dut.eval();}
 Exp step(std::deque<Exp>& h,Exp e){Exp out=h.front();h.pop_front();h.push_back(e);return out;}
 void tick(const Vec& p,bool f,bool m,bool t,bool israndom=false){
 dut.clk=0;dut.a=p.a;dut.b=p.b;dut.fv=f;dut.mv=m;dut.tv=t;dut.fp4=p.fp4;dut.xe=p.xe&1023;dut.we=p.we&1023;
 latest_tag=((cycles*7919u)^0x15555u)&0x1ffffu;dut.tag=latest_tag;
 for(int j=0;j<8;++j){dut.xq[j]=p.x[j];dut.wq[j]=p.w[j];}dut.eval();
 Exp ea{},em{},et{};
 if(dut.rst_n){ea=step(ah,{f,p.ae,p.ay});em=step(mh,{m,p.mf,p.my});et=step(th,{t,p.tf,p.ty});}
 else {++held;ah=std::deque<Exp>(7);mh=std::deque<Exp>(4);th=std::deque<Exp>(10);}
 expected_tag=tags.front();tags.pop_front();tags.push_back(latest_tag); // tag delay has NO reset
 dut.clk=1;dut.eval();++cycles;if(israndom)++random;compare();
 req(dut.ref_add_v==ea.v&&dut.sim_add_v==ea.v,"independent_fadd_LAT8");
 req(dut.ref_term_v==et.v&&dut.sim_term_v==et.v,"independent_bterm_LAT11");
 req(dut.ref_term_tag==expected_tag&&dut.sim_term_tag==expected_tag,"independent_unreset_tag_LAT11");
 if(!em.v)req(!dut.ref_mul_fault&&!dut.sim_mul_fault,"bmul_fault_gated_LAT5");
 if(ea.v){++av;req(dut.ref_add_err<=2,"fadd_error_aperture");++ae[dut.ref_add_err];if(ea.e>=0)req(dut.ref_add_err==ea.e,"directed_fadd_error");if(ea.y>=0)req(dut.ref_add_y==uint32_t(ea.y),"directed_fadd_payload");}else ++ab;
 if(em.v){++mv;++mf[dut.ref_mul_fault];if(em.e>=0)req(dut.ref_mul_fault==em.e,"directed_bmul_LAT5_fault");if(em.y>=0)req(dut.ref_mul_y==uint32_t(em.y),"directed_bmul_LAT5_payload");}else ++mb;
 if(et.v){++tv;++tf[dut.ref_term_f];if(et.e>=0)req(dut.ref_term_f==et.e,"directed_bterm_fault");if(et.y>=0)req(dut.ref_term_y==uint32_t(et.y),"directed_bterm_payload");}else ++tb;
 dut.clk=0;dut.eval();
 }
 void drain(){Vec p=dot(0x7f,0x7f);p.a=0x7fc00001;p.b=0x7f7fffff;for(int i=0;i<14;++i)tick(p,false,false,false);}
 void print(uint32_t seed){std::cout<<"RESULT {\"status\":\""<<(mismatch.empty()?"PASS":"FAIL")<<"\",\"seed\":"<<seed<<",\"clock_cycles\":"<<cycles<<",\"checked_samples\":"<<samples<<",\"async_resets\":"<<resets<<",\"reset_held_edges\":"<<held<<",\"random_clock_cycles\":"<<random<<",\"valid_add_mul_term\":["<<av<<","<<mv<<","<<tv<<"],\"bubble_reset_add_mul_term\":["<<ab<<","<<mb<<","<<tb<<"],\"add_errors\":["<<ae[0]<<","<<ae[1]<<","<<ae[2]<<"],\"mul_faults\":["<<mf[0]<<","<<mf[1]<<"],\"term_faults\":["<<tf[0]<<","<<tf[1]<<"],\"first_mismatch\":"<<(mismatch.empty()?"null":mismatch)<<"}\n";}
};
int main(int argc,char** argv){Verilated::commandArgs(argc,argv);uint32_t seed=argc>1?std::strtoull(argv[1],nullptr,10):0x12345678u;unsigned n=argc>2?std::strtoul(argv[2],nullptr,10):8192;if(!seed||n<1||n>32768)return 2;Gate g;
 std::vector<Vec> v;
 Vec p=dot(0x38,0x38);p.ae=p.mf=p.tf=0;p.ay=0x40400000;p.my=0x40000000;p.ty=0x42000000;
 v.push_back(p);
 p=dot(0x38,0x02,0,true);p.tf=0;p.ty=0x42000000;v.push_back(p);
 p=dot(0x38,0x38);for(int j=0;j<8;++j)p.x[j]=0xb838b838;p.tf=0;p.ty=0;v.push_back(p);
 p=dot(0xb8,0x38);p.tf=0;p.ty=0xc2000000;v.push_back(p);
 p=dot(0x38,0x38,-150);p.tf=0;p.ty=0x10;v.push_back(p);
 p=dot(0x38,0x38,-160);p.tf=0;p.ty=0;v.push_back(p);
 p=dot(0x7f,0x38);p.tf=1;v.push_back(p);
 p=dot(0x38,0x7f);p.tf=1;v.push_back(p);
 p=dot(0x38,0x38,250);p.tf=1;p.ty=0x7f800000;v.push_back(p);
 p=dot(0x00,0x7e,511);p.tf=0;p.ty=0;v.push_back(p);
 for(bool fp4:{false,true})for(uint8_t code:{uint8_t(1),uint8_t(7),uint8_t(0x38),uint8_t(0x7e),uint8_t(0xfe)})for(int scale:{-150,-130,-20,0,100}){p=dot(code,fp4?0x0f:0x7e,scale,fp4);p.x[0]^=0x01010101;p.w[7]^=0x01010101;v.push_back(p);}
 const uint32_t fp[][2]={{0,0x80000000},{1,1},{0x007fffff,1},{0x00800000,0x3f000000},{0x00800001,0x3f7fffff},{0x3f800000,0xbf800000},{0x3f800001,0xbf800000},{0x3f800000,0xbf7fffff},{0x3f800000,0x33800000},{0x3f800001,0x33800000},{0x3fffffff,0x33800000},{0x3fffffff,0x3f800001},{0x7f7fffff,0x7f7fffff},{0xff7fffff,0xff7fffff},{0x7f800000,0},{0xff800000,0x3f800000},{0x7fc00001,0x3f800000},{0x7f800001,0x3f800000},{0,0x7fc00001},{0x00010000,0x3f800000},{0x00010000,0x00010000},{0x3fff0000,0x3fff0000}};
 for(auto& f:fp){p=dot(0x38,0x38);p.a=f[0];p.b=f[1];v.push_back(p);}
 p=dot(0x38,0x38);p.a=0x7fc00001;p.ae=1;p.mf=1;p.ay=p.my=0;v.push_back(p);
 p.a=0x7f7fffff;p.b=0x7f7fffff;p.ae=2;p.mf=1;v.push_back(p);
 try{
 g.reset("startup_async");for(int i=0;i<3;++i)g.tick(v[6],true,true,true);g.release();g.phase="directed_II1";for(auto& q:v)g.tick(q,true,true,true);g.drain();
 g.phase="directed_bubbles";for(size_t i=0;i<v.size();++i){g.tick(v[i],true,i%2==0,i%3!=0);g.tick(v[6],false,i%2!=0,i%3==0);}g.drain();
 for(int stage=0;stage<11;++stage){g.reset("prepare_stage_"+std::to_string(stage));g.tick(v[0],false,false,false);g.release();g.phase="fill_stage_"+std::to_string(stage);for(int j=0;j<=stage;++j)g.tick(v[j%v.size()],true,true,true);g.reset("inflight_async_stage_"+std::to_string(stage));if(stage%2==0)for(int j=0;j<3;++j)g.tick(v[6],true,true,true);g.release();g.tick(v[0],true,true,true);g.drain();}
 uint32_t rng=seed;for(unsigned k=0;k<n;++k){g.phase="seeded_random";if(k%257==0){g.reset("random_async");g.release();}if(k%509==17){g.reset("random_held");g.tick(v[0],true,true,true,true);g.tick(v[6],false,false,false,true);g.release();}
 p=Vec{};p.a=xs(rng);p.b=xs(rng);for(int j=0;j<8;++j){p.x[j]=xs(rng);p.w[j]=xs(rng);}p.xe=int(xs(rng)%1024)-512;p.we=int(xs(rng)%1024)-512;uint32_t ctl=xs(rng);p.fp4=ctl&1;
 if((ctl&15)==2)p.b=p.a^0x80000000u;if((ctl&7)==0){p=v[ctl%v.size()];}if((ctl&31)==1){p.a=(p.a&0xffff0000u)|xs(rng)%65536;p.b=(p.b&0xffff0000u)|xs(rng)%65536;}
 g.tick(p,(ctl&3)!=0,(ctl&12)!=0,(ctl&48)!=0,true);}
 g.drain();g.req(g.ae[1]&&g.ae[2]&&g.mf[1]&&g.tf[1],"error_coverage");g.req(g.av+g.ab==g.cycles&&g.mv+g.mb==g.cycles&&g.tv+g.tb==g.cycles,"all_clock_samples_accounted");g.req(g.samples==g.cycles+g.resets,"all_async_samples_accounted");
 }catch(int){g.print(seed);return 1;}g.print(seed);return 0;
}
