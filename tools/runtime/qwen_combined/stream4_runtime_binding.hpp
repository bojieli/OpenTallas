#pragma once
#include "Vhbm.h"
#include "Vhbm___024root.h"
#include "hbm_access.hpp"
#include "stream4_memory_binding.hpp"

// REQUIRED Claude-owned native port hook, implemented in the selected source
// translation unit. No weak symbol or host memory-response fallback. The hook
// must join the actual tagged read ports to this model's shared controller
// state and backing memory. It owns no separate model/clock/ACK store.
// Called during settle AND after the caller assigns all actual clocks/resets,
// before either model evaluates an edge. The die's hclk/hrst_n identify the
// existing tagged-row boundary; backend sampling is its selected RTL's job.
bool qwen_stream4_wire_native_tagged_rows(Vdie&,Vhbm&);

struct CombinedStream4 {
    Vdie& die;
    Vhbm model;
    qwen_combined::BorrowedStream4Memory<Vhbm> borrowed;
    CombinedStream4(Vdie& d,VerilatedContext& ctx)
        :die(d),model(&ctx,"stream4"),borrowed(model,RM_HBM_LAYERS) {}
    void clocks(bool core_high) {model.clk=core_high;model.rst_n=die.rst_n;}
    void eval() {model.eval();}
    bool wire() {
        bool changed=qwen_combined::wire_stream4_transport(die,model);
        changed|=qwen_stream4_wire_native_tagged_rows(die,model);
        return changed;
    }
    auto& memory(std::size_t sector) {return borrowed.sector(sector);}
};
