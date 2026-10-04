#pragma once
// Port-only connection to the actual ot_qwen_hbm_stream4_ack model. Include
// after getb/setb/rt_set and the generated hbm_access.hpp. No model ownership,
// clocks, eval, memory mirror, transaction server or completion is added here.
#include <cstddef>
#include <cstdint>
#include <stdexcept>
namespace qwen_combined {
template<class Die,class Stream4>
bool wire_stream4_transport(Die& d,Stream4& m) {
    bool changed=false;
    changed|=rt_set(m.d_v,d.stream_d_v);
    changed|=rt_set(m.d_row,d.stream_d_row);
    changed|=rt_set(m.d_n,d.stream_d_n);
    changed|=rt_set(m.go,d.stream_go);
    changed|=rt_set(d.stream_d_rdy,m.d_rdy);
    changed|=rt_set(d.stream_fault,m.fault);
    auto copy=[&](auto& dst,const auto& src,unsigned words) {
        for(unsigned i=0;i<words;++i)changed|=rt_set(dst[i],src[i]);
    };
    copy(m.l_pop,d.stream_l_pop,4);
    copy(m.w_v,d.stream_w_v,4);
    copy(m.w_sec,d.stream_w_sec,96);
    copy(m.w_data,d.stream_w_data,1024);
    copy(m.w_tag,d.stream_w_tag,36);
    copy(d.stream_l_v,m.l_v,4);
    copy(d.stream_l_sec,m.l_sec,68);
    copy(d.stream_l_row,m.l_row,32);
    copy(d.stream_l_data,m.l_data,1024);
    copy(d.stream_w_room,m.w_room,4);
    copy(d.stream_wd_v,m.wd_v,4);
    copy(d.stream_wd_tag,m.wd_tag,36);
    return changed;
}
// The initialized runtime borrows its ONE stream model per rank (four stacks
// already live inside it). It must replace the old four independently-owned
// ACK models, not add this store alongside them. Row-read model/RTL must use
// this SAME array; the native shared controller/row hook remains required.
template<class Stream4> class BorrowedStream4Memory {
    Stream4& model_;
    std::size_t extent_;
public:
    BorrowedStream4Memory(Stream4& actual,unsigned actual_layers):model_(actual),extent_(std::size_t(actual_layers)*131072) {
        if(actual_layers<1||actual_layers>36)throw std::invalid_argument("STREAM4 compiled layer extent");
        if(combined_hbm_array(model_.rootp).size()!=extent_)
            throw std::invalid_argument("STREAM4 actual array/compiled extent mismatch");
    }
    auto& array() {return combined_hbm_array(model_.rootp);}
    auto& sector(std::size_t logical_sector) {
        if(logical_sector>=extent_)throw std::out_of_range("STREAM4 logical sector");
        return array()[logical_sector];
    }
    // Intended for binding identity checks, never a copied array or row payload.
    const void* identity() {return static_cast<const void*>(&array());}
};
struct Stream4PhysicalSector {
    unsigned stack,pc,bank,column,layer;
};
inline Stream4PhysicalSector stream4_physical_sector(uint32_t logical_sector,unsigned actual_layers) {
    if(actual_layers<1||actual_layers>36||uint64_t(logical_sector)>=uint64_t(actual_layers)*131072)
        throw std::out_of_range("STREAM4 source address extent");
    const unsigned l=logical_sector&131071u;
    // Exact ot_qwen_hbm_stream4_ack l2port/l2bank/l2col, no canonical
    // old owner[10:9] alias. A tagged 16-sector burst spans all four stacks.
    const unsigned j=(((l>>6)&511u)<<1)|((l>>16)&1u);
    return {l&3u,((l>>15)&1u)*16+((l>>2)&15u),((j>>7)<<2)|(j&3u),(j>>2)&31u,logical_sector>>17};
}
// Read the already-loaded f2a5 descriptor image, never regenerate it. The
// first normal descriptor executes O and its all-reduce; the following normal
// descriptor starts MLP after that collective has actually retired.
template<class Descriptors>
unsigned stream4_mlp_program_base(const Descriptors& actual_descriptors) {
    if(actual_descriptors.size()<3)
        throw std::invalid_argument("STREAM4 descriptor3/O/MLP image required");
    const uint64_t near=actual_descriptors[0],o=actual_descriptors[1],mlp=actual_descriptors[2];
    if((near&3u)!=3u||(near>>62)!=0||(o&3u)!=1u||(mlp&3u)!=1u)
        throw std::invalid_argument("STREAM4 actual near/O-AR/MLP descriptors");
    const unsigned o_base=(o>>32)&65535u,mlp_base=(mlp>>32)&65535u;
    if(o_base>=4096||mlp_base>=4096||mlp_base<=o_base)
        throw std::invalid_argument("STREAM4 actual PAW12 suffix/MLP boundaries");
    return mlp_base;
}
template<class Die>
bool wire_stream4_kv_free(Die& d,unsigned actual_mlp_program_base) {
    if(actual_mlp_program_base>=4096)
        throw std::out_of_range("STREAM4 actual MLP program boundary");
    // Invoke in the existing low-clock settle loop. The sequencer itself
    // asserts core_start after O's actual AR retirement; no host clock/count.
    // RTL additionally enforces near inactive and row drain before slice reuse.
    const uint8_t release=bool(d.core_start_o)&&!bool(d.kv_arm_o)&&
        d.rm_layer!=255&&unsigned(d.prog_base)==actual_mlp_program_base;
    return rt_set(d.rm_kv_free,release);
}
template<class Die> bool stream4_layer_terminal(const Die& d) {
    // Posted kv_drained alone is insufficient. Readback/reuse also retains
    // actual write-ACK debt, row retirement and sequencer completion.
    return d.s_done&&d.kv_ok_o&&d.kv_drained_o&&d.row_drained_o&&!d.wb_busy_o&&!d.nhb_active_o&&
           !d.mem_fault&&!d.core_fault&&!d.s_fault;
}
} // namespace qwen_combined
