#pragma once
#include "combined_driver.hpp"
#include <array>

namespace qwen_combined {
// Direct binding for Laplace's ot_qwen_rom_combined_die, four full-shape ranks.
// The enclosing runtime supplies its EXISTING tile fabric / collective eval
// object, referring to these SAME four die models. No second model set, ready
// callback, memory handler, KV write encoder or synthetic completion is added.
// `kv_arm_o` is a read-only exposure of the source register. It must not be
// substituted with kv_layer_start/core_start or a host reconstructed state.
template<class Die,class Runtime> class CombinedDieBinding {
    std::array<Die*,ranks> dies_;Runtime& runtime_;
public:
    CombinedDieBinding(std::array<Die*,ranks> dies,Runtime& runtime):dies_(dies),runtime_(runtime) {
        for(auto* d:dies_)if(!d)throw std::invalid_argument("missing physical TP4 rank model");
    }
    void check_geometry() {runtime_.check_combined_geometry(groups,sw,nw,ranks);}
    void set_time_fs(uint64_t t) {runtime_.set_time_fs(t);}
    void drive_clocks(bool clk,bool hclk) {for(auto* d:dies_){d->clk=clk;d->hclk=hclk;}}
    void pulse_stage_start(bool v) {for(auto* d:dies_)d->h_start=v;}
    void set_stage(unsigned layer,unsigned pos,unsigned token) {
        for(auto* d:dies_){d->rm_layer=layer;d->tp_pos=pos;d->tp_token=token;}
    }
    void reset(bool core_n,bool hbm_n) {for(auto* d:dies_){d->rst_n=core_n;d->hrst_n=hbm_n;}}
    void eval() {runtime_.eval_combined();}
    RankPins sample(unsigned rank) const {
        const auto& d=*dies_.at(rank);
        return {bool(d.rst_n),bool(d.h_start),bool(d.core_start_o),bool(d.kv_arm_o),bool(d.kv_layer_start_o),
                bool(d.rst_n),bool(d.kv_layer_start_o),unsigned(d.rm_layer),unsigned(d.tp_pos),unsigned(d.tp_token),
                unsigned(d.rm_layer),unsigned(d.tp_pos),bool(d.s_done),bool(d.kv_ok_o),bool(d.kv_drained_o),
                bool(d.row_drained_o),bool(d.mem_fault||d.core_fault||d.s_fault)};
    }
};
} // namespace qwen_combined
