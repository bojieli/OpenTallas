#include "Vot_v41_bf_col.h"
#include "verilated.h"
#include <cstdio>
#include <cstdint>
static uint64_t s=0x1234567ULL; static uint32_t r(){ s^=s<<13; s^=s>>7; s^=s<<17; return (uint32_t)s; }
template<class T> void rw(T& w,int n){ for(int i=0;i<n;i++) w[i]=r(); }
int main(int argc,char**argv){ Verilated::commandArgs(argc,argv); auto*m=new Vot_v41_bf_col;
  long N=argc>1?atol(argv[1]):30000; FILE*f=fopen(argc>2?argv[2]:"out.txt","w");
  m->clk=0; m->rst_n_pin=0; m->ze_d=1; m->eval();
  int ze_mode=0;
  for(long c=0;c<N;c++){
    // stimulus at clk low
    if(c%5000==0) ze_mode=(c/5000)%3;
    bool rst = (c<8) || (c%7919>=7900 && c%7919<7905);
    m->rst_n_pin = !rst;
    m->ze_d = ze_mode==0 ? 1 : ze_mode==1 ? ((r()&3)!=0) : (r()&1);
    m->issue=r()&1; m->a_ctr=r()&0x3fff; m->i1_v=(r()&3)!=0; m->i1_bk=r()&1; m->i1_bf=(r()&3)==0;
    m->i1_t=r(); rw(m->i2x_q0,8); rw(m->i2x_q1,8); m->i2x_e0=r()&0x3ff; m->i2x_e1=r()&0x3ff;
    rw(m->so_row,4); m->so_idx=((uint64_t)r()<<32|r())&0xffffffffffULL; m->so_n=((uint64_t)r()<<32|r())&0xffffffffffULL;
    m->eval(); m->clk=1; m->eval();
    fprintf(f,"%ld %d %08x %04x %02x %02x %d %d %d\n",c,m->pv,m->pval,m->prow,m->pseg,m->pnseg,m->perr,m->ppos,m->qy_bkf);
    m->clk=0; m->eval();
  }
  fclose(f); delete m; return 0; }
