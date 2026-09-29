#!/usr/bin/env python3
"""Emit source-pinned simulation-only Qwen runtime composition qualification.

Does not modify production RTL or launch a full-shape build. Source objects
must include a4870d3b (safe reference) and a80d6a30 (experimental bank cut).
Run emitted files with qwen_matvec_runtime_run.py; G64 execution requires
separate resource approval and has no exact verdict yet.
"""
import argparse,pathlib,json,hashlib,subprocess
ap=argparse.ArgumentParser()
ap.add_argument('--groups',type=int,choices=(4,64),required=True)
ap.add_argument('--out',type=pathlib.Path,required=True)
ap.add_argument('--count-width',type=int,choices=(16,18),default=16)
ap.add_argument('--source-root',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1])
args=ap.parse_args();root=args.source_root;out=args.out
out.mkdir(parents=True,exist_ok=True)
G=args.groups;LG=(G-1).bit_length();B=4;N=G//B
CANDIDATE='a80d6a30';REFERENCE='a4870d3b'
def source(revision,path):
 return subprocess.check_output(['git','show',f'{revision}:{path}'],cwd=root)
original=source(CANDIDATE,'rtl/hdc/ot_hdc_matvec.sv').decode()
s=original.split('// One compile bank')[0].replace('module ot_hdc_matvec #(', 'module replay_controller #(',1)
ports='''
    ,input wire [G*W*32-1:0] ext_sum
    ,input wire [G*W-1:0] ext_lfault
    ,input wire [$clog2(G)*G*W*32-1:0] ext_levels
    ,input wire [$clog2(G)-1:0] ext_tfault
    ,output wire ext_mac_valid,ext_mac_first,ext_mac_add_valid
    ,output wire [G*W*32-1:0] ext_mac_w
    ,output wire [G*32-1:0] ext_mac_x
    ,output wire [$clog2(G)-1:0] ext_reduce_valid,ext_reduce_select
'''
s=s.replace('\n);',ports+'\n);',1)
a=s.index('    // -- lanes');b=s.index('    // -- split tree',a)
s=s[:a]+'''    wire [G*W*32-1:0] sum=ext_sum;
    wire [G*W-1:0] lfault=ext_lfault;
    genvar g;
    assign ext_mac_valid=s3_v;
    assign ext_mac_first=fl_first[4];
    assign ext_mac_add_valid=vline[5];
    assign ext_mac_w=s3_w;
    assign ext_mac_x=s3_x;
'''+s[b:]
a=s.index('            wire [NBR-1:0] bank_fault;');b=s.index('            assign tfault[lv] = |bank_fault;',a)+len('            assign tfault[lv] = |bank_fault;')
s=s[:a]+'''            assign lvl[lv] = ext_levels[(lv-1)*G*W*32 +: G*W*32];
            assign tfault[lv] = ext_tfault[lv-1];
            assign ext_reduce_valid[lv-1] = vline[10+TL*(lv-1)] && (split_at[4*lv-1 -: 4] >= lv);
            assign ext_reduce_select[lv-1] = sp_sel >= lv;
'''+s[b:]
(out/'controller.sv').write_text(s)
(out/'kernels.sv').write_text('`timescale 1ns/1ps\n'+original[original.index('// One compile bank'):])
ref=source(REFERENCE,'rtl/hdc/ot_hdc_matvec.sv').decode().replace('module ot_hdc_matvec #(', 'module replay_matvec_ref #(',1)
(out/'reference.sv').write_text(ref)

for p in ['rtl/hdc/ot_hdc_fpu.sv','rtl/hdc/ot_hdc_fp32_mul_pipe.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_sfu.sv','rtl/proto/ot_fp32_add_rne_pipe.sv']:
 (out/pathlib.Path(p).name).write_bytes(source(CANDIDATE,p))
adds=sorted({max(0,min(B,(G>>level)-bank*B)) for level in range(1,LG+1) for bank in range(N)})
for n in adds:
 (out/f'bank{n}.sv').write_text(f'''`timescale 1ns/1ps
module replay_bank{n}(input clk,rst_n,v,sel,input [2047:0] h,a,b,output [2047:0] y,output fault);
ot_hdc_matvec_reduce_bank #(.B(4),.W(16),.ADDS({n})) u(clk,rst_n,v,sel,h,a,b,y,fault);
endmodule
''')
OUTPUTS={'ready': '', 'idle': '', 'wrom_re': '', 'wrom_addr': '[23:0]', 'scale_re': '', 'scale_gre': '[G-1:0]', 'scale_addr': '[G*24-1:0]', 'kv_re': '', 'kv_addr': '[G*24-1:0]', 'x_re': '[G-1:0]', 'x_addr': '[G*24-1:0]', 'ov': '', 'o_we': '[G-1:0]', 'o_addr': '[G*24-1:0]', 'o_mask': '[G*W-1:0]', 'o_data': '[G*W*32-1:0]', 'am_idx': '[15:0]', 'am_val': '[31:0]', 'am_any': '', 'mx_we': '', 'mx_addr': '[23:0]', 'mx_mask': '[W-1:0]', 'mx_data': '[W*32-1:0]', 'progress': '[15:0]', 'fault': ''}
outputs={k:(1 if not v else eval(v[1:].split(':')[0],{'G':G,'W':16})+1) for k,v in OUTPUTS.items()}
checks='\n'.join((f'CHECK({k});' if width<=64 else f'CHECKW({k},{(width+31)//32});') for k,width in outputs.items())
initial='\n'.join(f'c.{k}=r.{k}={v};' for k,v in {'i_nout':511,'i_tiles':2,'i_k':3,'i_wsrc':0,'i_wbase':100,'i_ts':12,'i_ks':4,'i_js':1,'i_xbase':11,'i_xks':3,'i_xjs':1,'i_xcs':17,'i_jsh':0,'i_split':0,'i_wcs':8,'i_round':1,'i_obase':20,'i_ots':8,'i_ojs':1,'i_mmode':0,'i_oen':1,'i_amax':1,'i_rmax':0,'i_mbase':2}.items())
cpp=r'''#include "Vreplay_controller.h"
#include "Vreplay_matvec_ref.h"
#include "Vot_hdc_matvec_mac_group.h"
BANK_INCLUDES
#include "verilated.h"
#include <cstdio>
#include <memory>
#include <cstring>
#include <vector>
#include <algorithm>
#include <sys/resource.h>
#define CHECK(p) if(c.p!=r.p){printf("FAIL case=%d tick=%d port=" #p "\n",test,tick);return 1;}
#define CHECKW(p,n) if(memcmp(&c.p[0],&r.p[0],4*(n))){printf("FAIL case=%d tick=%d port=" #p "\n",test,tick);return 1;}
struct BankBase{
 uint32_t h[64]={},a[64]={},b[64]={},y[64]={};bool rst=0,v=0,sel=0,fault=0;int clk=0;
 virtual void eval()=0;virtual ~BankBase(){}
};
template<class T>struct Bank:BankBase{
 T model;
 void eval()override{
  model.clk=clk;model.rst_n=rst;model.v=v;model.sel=sel;
  for(int j=0;j<64;j++){model.h[j]=h[j];model.a[j]=a[j];model.b[j]=b[j];}
  model.eval();for(int j=0;j<64;j++)y[j]=model.y[j];fault=model.fault;
 }
};
std::unique_ptr<BankBase> make_bank(int adds){switch(adds){BANK_CASES default:std::abort();}}
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);
 constexpr int G=GROUPS,LG=LEVELS,NB=G/4,NW=COUNTWIDTH;
 Vreplay_controller c;Vreplay_matvec_ref r;
 std::unique_ptr<Vot_hdc_matvec_mac_group> m[G];for(auto&p:m)p.reset(new Vot_hdc_matvec_mac_group);
 std::vector<std::unique_ptr<BankBase>> banks;
 for(int lv=1;lv<=LG;lv++)for(int b=0;b<NB;b++)banks.push_back(make_bank(std::max(0,std::min(4,(G>>lv)-b*4))));
 INITIAL
 auto outputs=[&](){
  ZERO_FAULT
  for(int g=0;g<G;g++){for(int j=0;j<16;j++)c.ext_sum[g*16+j]=m[g]->sum[j];SET_FAULT}
  c.ext_tfault=0;
  for(int lv=0;lv<LG;lv++)for(int b=0;b<NB;b++){
   auto &bank=*banks[lv*NB+b];for(int j=0;j<64;j++)c.ext_levels[lv*G*16+b*64+j]=bank.y[j];
   c.ext_tfault|=bank.fault<<lv;
  }
 };
 auto wire_inputs=[&](){
  for(int g=0;g<G;g++){
   m[g]->rst_n=c.rst_n;m[g]->valid=c.ext_mac_valid;m[g]->first=c.ext_mac_first;m[g]->add_valid=c.ext_mac_add_valid;
   for(int j=0;j<16;j++)m[g]->w[j]=c.ext_mac_w[g*16+j];m[g]->x=c.ext_mac_x[g];
  }
  for(int lv=0;lv<LG;lv++)for(int b=0;b<NB;b++){
   auto &bank=*banks[lv*NB+b];bank.rst=c.rst_n;bank.v=(c.ext_reduce_valid>>lv)&1;bank.sel=(c.ext_reduce_select>>lv)&1;
   auto prior=[&](int word){return lv==0?c.ext_sum[word]:banks[(lv-1)*NB+word/64]->y[word%64];};
   for(int j=0;j<64;j++){bank.h[j]=prior(b*64+j);bank.a[j]=bank.b[j]=0;}
   int active=std::max(0,std::min(4,(G>>(lv+1))-b*4));
   for(int g=0;g<active;g++)for(int j=0;j<16;j++){
    bank.a[g*16+j]=prior(2*(b*4+g)*16+j);bank.b[g*16+j]=prior((2*(b*4+g)+1)*16+j);
   }
  }
 };
 auto evaluate=[&](){for(auto&p:m)p->eval();for(auto&p:banks)p->eval();outputs();c.eval();wire_inputs();};
 auto snapshot=[&](){
  std::vector<uint32_t>s;
  for(auto&p:m){s.push_back(p->sum[0]);for(int j=1;j<16;j++)s.push_back(p->sum[j]);s.push_back(p->fault);s.push_back(p->valid|(p->first<<1)|(p->add_valid<<2));}
  for(auto&p:banks){s.insert(s.end(),p->y,p->y+64);s.push_back(p->fault);s.push_back(p->v|(p->sel<<1)|(p->rst<<2));}
  return s;
 };
 int cycles=0,writes=0,max_settle=0;
 for(int test=0;test<(LG+1)*8;test++){
  c.i_split=r.i_split=test%(LG+1);c.i_wsrc=r.i_wsrc=(test/(LG+1))%2;
  c.i_nout=r.i_nout=(test%4==0?1:(test%4==1?127:(test%4==2?G*16:G*16*8-1)));
  c.i_mmode=r.i_mmode=(test/(2*(LG+1)))%2;c.i_rmax=r.i_rmax=test>=4*(LG+1);
  bool high_count=(NW==18 && test>=(LG+1)*8-2);
  int tile_count=high_count?std::max(20,(151936+G*16*8-1)/(G*16*8)):2;
  c.i_tiles=r.i_tiles=tile_count;
  if(high_count){c.i_nout=r.i_nout=151936;c.i_split=r.i_split=0;c.i_mmode=r.i_mmode=0;}
  bool high_write=false;
  int limit=high_count?tile_count*26+380:230;
  for(int tick=0;tick<limit;tick++){
   c.rst_n=r.rst_n=tick>=4;c.go=r.go=tick==5;
   for(int j=0;j<G*4;j++)c.wrom_q[j]=r.wrom_q[j]=(test%4==0?0x01010101u:(0x807fff01u^(j*0x10001u)));
   for(int j=0;j<G*8;j++)c.scale_q[j]=r.scale_q[j]=(j%3==0?0x3f003f00u:(j%3==1?0x3f803f80u:0x40004000u));
   for(int j=0;j<G*16;j++)c.kv_q[j]=r.kv_q[j]=(test%4==0?0x3f800000u:((j%2?0xbf800000u:0x3f000000u)));
   for(int j=0;j<G;j++)c.x_q[j]=r.x_q[j]=(test%4==0?0x3f800000u:(j%2?0xbf800000u:0x3f000000u));
   c.clk=r.clk=0;for(auto&p:m)p->clk=0;for(auto&p:banks)p->clk=0;
   int settle=0;for(;settle<LG+5;settle++){auto before=snapshot();evaluate();if(settle>=1 && before==snapshot())break;}
   if(settle==LG+5){printf("FAIL clock-low did not converge\n");return 4;}max_settle=std::max(max_settle,settle+1);
   r.eval();
   if(tick%17!=13){
    c.clk=r.clk=1;for(auto&p:m)p->clk=1;for(auto&p:banks)p->clk=1;
    c.eval();if(argc>1)wire_inputs();
    for(auto&p:m)p->eval();for(auto&p:banks)p->eval();r.eval();outputs();c.eval();
   }
   if(tick>8){CHECKS}
   if(c.o_we)writes++;
   for(int group=0;group<G;group++)if((uint64_t(c.o_we)>>group)&1){
    int bit=group*24;uint64_t address=c.o_addr[bit/32];
    if(bit%32+24>32)address|=uint64_t(c.o_addr[bit/32+1])<<32;
    address=(address>>(bit%32))&0xffffff;
    if(address*16>=65536)high_write=true;
   }
   if(tick==limit-1 && high_count && !high_write){printf("FAIL high-count test never wrote high rows\n");return 5;}
   if(tick==limit-1 && (!r.idle || r.progress==0)){printf("FAIL no completion case%d\n",test);return 3;}
   cycles++;
  }
 }
 struct rusage ru;getrusage(RUSAGE_SELF,&ru);
 printf("PASS generic runtime composition G%d cases%d cycles%d writes%d settle%d RSS_KiB%ld\n",G,(LG+1)*8,cycles,writes,max_settle,ru.ru_maxrss);
}
'''
cpp=cpp.replace('BANK_INCLUDES','\n'.join(f'#include "Vreplay_bank{n}.h"' for n in adds)).replace('BANK_CASES','\n'.join(f'case {n}:return std::unique_ptr<BankBase>(new Bank<Vreplay_bank{n}>);' for n in adds)).replace('COUNTWIDTH',str(args.count_width)).replace('GROUPS',str(G)).replace('LEVELS',str(LG)).replace('INITIAL',initial).replace('CHECKS',checks)
cpp=cpp.replace('ZERO_FAULT','c.ext_lfault=0;' if G==4 else f'for(int j=0;j<{G//2};j++)c.ext_lfault[j]=0;').replace('SET_FAULT','c.ext_lfault|=uint64_t(m[g]->fault)<<(g*16);' if G==4 else 'c.ext_lfault[g/2]|=uint32_t(m[g]->fault)<<((g%2)*16);')
# o_we is 64-bit at G64, so scalar activity remains well defined.
(out/'main.cpp').write_text(cpp)
(out/'parameters.json').write_text(json.dumps({'count_width':args.count_width,'groups':G,'levels':LG,'bank_groups':4,'banks':LG*N,'bank_add_variants':adds,'source_reference':'a4870d3b','simulation_candidate':'a80d6a30'},indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},indent=2)+'\n')
print(out)
