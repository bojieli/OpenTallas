#include "s81_embedding_abi.h"
#include "Vembedding_vm.h"
#include <verilated.h>
#include <stdexcept>
struct Reader { Vembedding_vm dut; };
static void apply(Reader& r,const S81EmbeddingInput& i) {
 auto& d=r.dut;
 if(i.token>=(1u<<17)||i.identity>=(1ull<<47)||i.rsp_identity>=(1ull<<47)||
    i.vm_base>=(1u<<19)||i.rsp_macro>=(1u<<14)||i.rsp_row>=4096)
   throw std::runtime_error("embedding ABI bounds");
 d.rst_n=i.reset_n;d.start=i.start;d.token=i.token;d.identity=i.identity;d.vm_base=i.vm_base;
 d.req_ready=i.req_ready;d.rsp_v=i.rsp_valid;d.rsp_identity=i.rsp_identity;
 d.rsp_macro=i.rsp_macro;d.rsp_row=i.rsp_row;d.commit_ready=i.commit_ready;
 for(int k=0;k<8;k++)d.rsp_data[k]=i.rsp_data[k];
}
static void output(Reader& r,S81EmbeddingOutput& o) {
 auto& d=r.dut;
 o.req_valid=d.req_v;o.req_macro=d.req_macro;o.req_row=d.req_row;o.req_identity=d.req_identity;
 o.rsp_ready=d.rsp_ready;o.vm_valid=d.vm_v;o.vm_address=d.vm_address;o.vm_identity=d.vm_identity;
 for(int k=0;k<16;k++)o.vm_data[k]=d.vm_data[k];
 o.busy=d.busy;o.done=d.done;o.fault=d.fault;o.committed_words=d.committed_words;
}
extern "C" void* s81_embedding_create(){return new Reader;}
extern "C" void s81_embedding_destroy(void* p){delete static_cast<Reader*>(p);}
extern "C" void s81_embedding_eval(void* p,const S81EmbeddingInput* i,S81EmbeddingOutput* o){
 auto& r=*static_cast<Reader*>(p);apply(r,*i);r.dut.clk=0;r.dut.eval();output(r,*o);
}
extern "C" void s81_embedding_edge(void* p,const S81EmbeddingInput* i,S81EmbeddingOutput* o){
 auto& r=*static_cast<Reader*>(p);apply(r,*i);r.dut.clk=0;r.dut.eval();r.dut.clk=1;
 r.dut.eval();output(r,*o);
}
extern "C" uint32_t s81_embedding_vm_word(void* p,uint32_t address){
 if(address>=32768)throw std::runtime_error("small native endpoint bounds");
 auto& r=*static_cast<Reader*>(p);r.dut.probe_address=address;r.dut.eval();return r.dut.probe_data;
}
