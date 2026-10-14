#include "native59.h"
#include "Vnative59.h"
#include "verilated.h"
#include <cstring>
#include <memory>
struct Native59 {
 VerilatedContext context; Vnative59 model; uint64_t cycles=0;
 Native59(): model(&context) {model.clk=0;model.rst_n=0;model.in_valid=0;model.in_mode=0;model.in_last=0;model.eval();}
};
template<class W> static uint64_t get_bits(const W &words,unsigned offset,unsigned width){
 uint64_t value=0;for(unsigned b=0;b<width;b++)value|=uint64_t((words[(offset+b)/32]>>((offset+b)%32))&1)<<b;return value;
}
template<class W> static void put_bits(W &words,unsigned offset,unsigned width,uint64_t value){
 for(unsigned b=0;b<width;b++){uint32_t mask=uint32_t(1)<<((offset+b)%32);auto &word=words[(offset+b)/32];word=(word&~mask)|(((value>>b)&1)?mask:0);}
}
extern "C" void *native59_create(){try{return new Native59;}catch(...){return nullptr;}}
extern "C" void native59_destroy(void *handle){if(handle){auto *n=static_cast<Native59*>(handle);n->model.final();delete n;}}
extern "C" int native59_tick(void *handle,const native59_input *input,native59_output *output){
 if(!handle||!input||!output)return -1;
 auto &n=*static_cast<Native59*>(handle);auto &m=n.model;
 m.clk=0;m.rst_n=input->rst_n;m.in_valid=input->valid;m.in_mode=input->mode;m.in_last=input->last;
 for(unsigned r=0;r<8;r++){for(unsigned l=0;l<16;l++)m.in_data[r*16+l]=input->data[r][l];put_bits(m.in_tag,r*59,59,input->tag[r]);}
 n.context.timeInc(416667);m.eval();std::memset(output,0,sizeof(*output));
 output->valid=m.out_valid;output->last=m.out_last;output->err=m.out_err;output->credit=m.in_cr;
 output->fault=m.fault;output->online=m.online;output->drained=m.drained;output->cycle=n.cycles;
 for(unsigned r=0;r<8;r++){for(unsigned l=0;l<16;l++)output->data[r][l]=m.out_data[r*16+l];output->tag[r]=get_bits(m.out_tag,r*59,59);
  output->rank[r]=(m.out_rank>>(3*r))&7;output->fault_code[r]=(m.fault_code>>(5*r))&31;output->credits[r]=(m.in_credits>>(6*r))&63;}
 m.clk=1;n.context.timeInc(416667);m.eval();n.cycles++;
 return n.context.gotFinish()?-2:0;
}
