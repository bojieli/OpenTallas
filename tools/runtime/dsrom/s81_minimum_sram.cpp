#include "s81_minimum_sram_abi.h"
#include "Vnative_sram.h"
#include "verilated.h"
#include <memory>
namespace {
struct NativeSram {
    VerilatedContext context;
    Vnative_sram model;
    NativeSram():model(&context,"native_sram") {
        model.clk=0; model.r_ce_in=0; model.w_ce_in=0;
        model.r_addr_in=0; model.w_addr_in=0;
        model.rr_en=0; model.rr_addr=0; model.cr_en=0; model.cr_sel=0;
        for(unsigned i=0;i<4;++i){model.wd_in[i]=0;model.w_mask_in[i]=0;}
        model.eval();
    }
};
}
extern "C" void* s81_minimum_sram_create() {
    try{return new NativeSram;}catch(...){return nullptr;}
}
extern "C" void s81_minimum_sram_destroy(void* p) {delete static_cast<NativeSram*>(p);}
extern "C" int s81_minimum_sram_eval(void* p,const S81MinimumSramInput* in,
                                     S81MinimumSramOutput* out) {
    if(!p||!in||!out||in->clk>1||in->read_enable>1||in->write_enable>1||
       in->read_row>=512||in->write_row>=512)return -1;
    auto& m=static_cast<NativeSram*>(p)->model;
    m.r_ce_in=in->read_enable; m.w_ce_in=in->write_enable;
    m.r_addr_in=in->read_row; m.w_addr_in=in->write_row;
    for(unsigned i=0;i<4;++i){m.wd_in[i]=in->data[i];m.w_mask_in[i]=in->mask[i];}
    m.clk=in->clk;m.eval();
    for(unsigned i=0;i<4;++i)out->data[i]=m.rd_out[i];
    return 0;
}
