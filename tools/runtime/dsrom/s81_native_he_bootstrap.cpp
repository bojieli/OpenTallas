#include "s81_native_he_bootstrap_abi.h"
#include "Vs81_native_he_bootstrap.h"
#include "verilated.h"
#include <algorithm>
#include <memory>
struct Leaf {
 VerilatedContext context;
 Vs81_native_he_bootstrap model{&context};
};
static void apply(Leaf& l,const S81NativeHeBootstrapInput& i,S81NativeHeBootstrapOutput& o,unsigned clk) {
 auto& m=l.model;
 m.clk=clk;m.rst_n=i.reset_n;m.he_go=i.he_go;m.he_nout=i.he_nout;m.he_k=i.he_k;
 m.he_wbase=i.he_wbase;m.he_xbase=i.he_xbase;m.he_obase=i.he_obase;
 m.he_m=i.he_m;m.he_xps=i.he_xps;m.he_ops=i.he_ops;
 std::copy_n(i.he_w_data,64,&m.he_w_data[0]);std::copy_n(i.he_x_q,8,&m.he_x_q[0]);
 m.ssx_valid=i.ssx_valid;m.ssx_last=i.ssx_last;std::copy_n(i.ssx_x,256,&m.ssx_x[0]);
 m.eval();
 o.he_ready=m.he_ready;o.he_idle=m.he_idle;o.he_fault=m.he_fault;
 o.he_w_re=m.he_w_re;o.he_x_re=m.he_x_re;
 // Packed AW30 and BAW16 ports, not an array of AW32 addresses.
 for(unsigned b=0;b<8;b++) {
  o.he_w_addr[b]=(m.he_w_addr[b/2]>>(16*(b%2)))&65535;
  unsigned bit=30*b,j=bit/32,s=bit%32;
  uint64_t q=m.he_x_addr[j];if(s&&j+1<8)q|=uint64_t(m.he_x_addr[j+1])<<32;
  o.he_x_addr[b]=(q>>s)&0x3fffffff;
 }
 o.he_o_we=m.he_o_we;o.he_o_addr=m.he_o_addr;o.he_o_mask=m.he_o_mask;
 std::copy_n(&m.he_o_data[0],32,o.he_o_data);
 o.ssx_we=m.ssx_we;o.ssx_addr=m.ssx_addr;o.ssx_data=m.ssx_data;
 o.ssx_busy=m.ssx_busy;o.ssx_fault=m.ssx_fault;
}
extern "C" void* s81_native_he_bootstrap_create(){return new Leaf;}
extern "C" void s81_native_he_bootstrap_destroy(void* p){delete static_cast<Leaf*>(p);}
extern "C" void s81_native_he_bootstrap_eval(void*p,const S81NativeHeBootstrapInput*i,S81NativeHeBootstrapOutput*o){apply(*static_cast<Leaf*>(p),*i,*o,0);}
extern "C" void s81_native_he_bootstrap_rise(void*p,const S81NativeHeBootstrapInput*i,S81NativeHeBootstrapOutput*o){apply(*static_cast<Leaf*>(p),*i,*o,1);}
extern "C" void s81_native_he_bootstrap_fall(void*p,const S81NativeHeBootstrapInput*i,S81NativeHeBootstrapOutput*o){apply(*static_cast<Leaf*>(p),*i,*o,0);}
