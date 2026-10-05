#pragma once
#include "Vhbm.h"
#include "Vhbm___024root.h"
#include "hbm_access.hpp"
#include "hbm_transport_wiring.hpp"
#include <array>
#include <memory>

// Actual four-stack HBM models for each of the same four compiled die models.
// Host only wires source pins and PRELOADS history before clocking. Requests,
// returns, write completions, refresh and finite queues remain model RTL.
struct CombinedHBM {
    std::array<std::unique_ptr<Vhbm>,4> stack;
    Vdie& die;
    CombinedHBM(Vdie& d,VerilatedContext& ctx):die(d) {
        for(unsigned s=0;s<4;++s)stack[s].reset(new Vhbm(&ctx,("hbm"+std::to_string(s)).c_str()));
    }
    void clocks(bool high) {for(auto& s:stack){s->clk=high;s->rst_n=die.hrst_n;}}
    void eval() {for(auto& s:stack)s->eval();}
    bool wire() {
        bool changed=false;
        for(unsigned s=0;s<4;++s)
            changed|=qwen_combined::wire_hbm_transport(die,*stack[s],s);
        return changed;
    }
    auto& memory(size_t sector) {
        // Literal corrected service owner[10:9], independent of pseudochannel
        // selection INSIDE the chosen physical HBM model.
        return combined_hbm_array(stack[(sector>>9)&3]->rootp)[sector];
    }
};
