"""PATH-QC-N59-5 fix (3) full-part lockstep: one C++ harness drives N Verilator models of qfd_qc_native59_part
(--prefix V<name>) with identical random inputs (biased native_cmd: embedding commands with clean/bad payload and
token around the 151936 bound) and compares EVERY output bit EVERY cycle vs model 0 (the old RTL).
Usage: gen_harness.py OBJ_DIR_OF_MODEL0/V<m0>.h m0 m1 [m2 ...] > tb.cpp"""
import re,sys
hdr,models=sys.argv[1],sys.argv[2:]
ports=[]
for l in open(hdr):
    m=re.search(r'VL_(IN|OUT)(8|16|64|W)?\(&(\w+),(\d+),(\d+)(?:,(\d+))?\)',l)
    if m:ports.append((m[1],m[2] or '',m[3],int(m[4])+1))
clocks={'clk','clk_t1','clk_t2','clk_t3'}
o=[]
o.append('#include <cstdio>\n#include <cstdlib>\n#include <cstdint>\n#include <random>\n#include "verilated.h"')
for m in models:o.append('#include "V%s.h"'%m)
o.append('static std::mt19937_64 rng(12345);static uint64_t R(){return rng();}')
o.append('double sc_time_stamp(){return 0;}')
o.append('int main(int argc,char**argv){Verilated::commandArgs(argc,argv);long N=argc>1?atol(argv[1]):20000;int mode=argc>2?atoi(argv[2]):0;')
o.append('VerilatedContext* ctx=new VerilatedContext;')
for i,m in enumerate(models):o.append('V%s* m%d=new V%s(ctx);'%(m,i,m))
o.append('long mism[%d]={0};long first[%d];for(int i=0;i<%d;i++)first[i]=-1;'%(len(models),len(models),len(models)))
o.append('long n_emb=0,n_emb_clean=0,n_bound=0,n_act=0;')
o.append('for(long cyc=0;cyc<N;cyc++){int rst=(cyc%400)<16;')
# input drive
for d,t,n,w in ports:
    if d!='IN' or n in clocks:continue
    if n=='arst_n':
        o.append(' {uint64_t v=rst?0:1;'+''.join(' m%d->arst_n=v;'%i for i in range(len(models)))+'}');continue
    if t=='W':
        nw=(w+31)//32
        o.append(' {uint32_t v[%d];for(int k=0;k<%d;k++)v[k]=(uint32_t)R();'%(nw,nw))
        if n=='native_cmd':
            o.append('  int sel=R()%8; if(sel<3){ // embedding command: bit0=0, [379:376]=E')
            o.append('   v[0]&=~1u; v[11]=(v[11]&~(0xfu<<24))|(0xeu<<24);')
            o.append('   if(sel<2){for(int b=1;b<=357;b++)v[b/32]&=~(1u<<(b%32)); n_emb_clean++;}')
            o.append('   uint32_t tok=(sel==0)?(151930+(R()%12)):(uint32_t)(R()%262144); if(tok>=151934&&tok<=151937)n_bound++;')
            o.append('   for(int b=0;b<18;b++){int bb=358+b; if((tok>>b)&1)v[bb/32]|=(1u<<(bb%32)); else v[bb/32]&=~(1u<<(bb%32));}')
            o.append('   n_emb++;} else if(sel==3){for(int k=0;k<%d;k++)v[k]=0;}'%nw)
        if n!='native_cmd':o.append('  if(mode==1)for(int k=0;k<%d;k++)v[k]=0;'%nw)
        o.append('  if(%d%%32)v[%d]&=(1u<<(%d%%32))-1;'%(w,nw-1,w))
        o.append(' '+''.join(' for(int k=0;k<%d;k++)m%d->%s[k]=v[k];'%(nw,i,n) for i in range(len(models)))+'}')
    else:
        mask='0x%xULL'%((1<<w)-1)
        bias=' if(R()%4==0)v=0;' if n not in ('start_i',) else ' v=rst?0:1;  /* START is a level run enable (ot_dp_rgate) */'
        bias+=' if(mode==1)v=0;' if n!='start_i' else ''
        o.append(' {uint64_t v=R()&%s;%s'%(mask,bias)+''.join(' m%d->%s=v;'%(i,n) for i in range(len(models)))+'}')
o.append(' for(int ph=0;ph<2;ph++){')
for i in range(len(models)):
    o.append('  m%d->clk=m%d->clk_t1=m%d->clk_t2=m%d->clk_t3=ph; m%d->eval();'%((i,)*5) if all(c in [p[2] for p in ports] for c in clocks) else '  m%d->clk=ph; m%d->eval();'%(i,i))
o.append(' }')
outs=[(t,n,w) for d,t,n,w in ports if d=='OUT']
o.append(' {static uint32_t prev[4096];int k0=0,ch=0;')
for t,n,w in outs:
    if t=='W':o.append('  for(int k=0;k<%d;k++){if(prev[k0]!=m0->%s[k])ch=1;prev[k0++]=m0->%s[k];}'%((w+31)//32,n,n))
    else:o.append('  {uint32_t x=(uint32_t)m0->%s^(uint32_t)((uint64_t)m0->%s>>32);if(prev[k0]!=x)ch=1;prev[k0++]=x;}'%(n,n))
o.append('  if(ch)n_act++;}')
# compare outputs after posedge
for i in range(1,len(models)):
    cmp=[]
    for d,t,n,w in ports:
        if d!='OUT':continue
        if t=='W':cmp.append('for(int k=0;k<%d;k++)if(m0->%s[k]!=m%d->%s[k])bad=1;'%((w+31)//32,n,i,n))
        else:cmp.append('if(m0->%s!=m%d->%s)bad=1;'%(n,i,n))
    o.append(' {int bad=0;%s if(bad){mism[%d]++;if(first[%d]<0)first[%d]=cyc;}}'%(''.join(cmp),i,i,i))
o.append('}')
o.append('printf("LOCKSTEP mode %d cycles %ld emb_cmds %ld clean %ld near_bound %ld output_change_cycles %ld\\n",mode,N,n_emb,n_emb_clean,n_bound,n_act);')
for i,m in enumerate(models[1:],1):o.append('printf("LOCKSTEP %s vs %s mismatching_cycles %%ld first %%ld\\n",mism[%d],first[%d]);'%(m,models[0],i,i))
o.append('return 0;}')
print('\n'.join(o))
