#pragma once
// Source-only wiring support for Laplace's enclosing combined die.
// Port slices reproduce Fabric::propagate in qwen_rom_rt_w12_rm.cpp.
// Does NOT evaluate models, drive clocks, make responses, or assert drain.
#include "fullshape_context.hpp"
#include <cstddef>
#include <cstdint>
#include <stdexcept>
namespace qwen_combined {
struct TileCaptureSourceShape {
    static constexpr unsigned GT=6144, NW=18, SMIN=6;
    static constexpr unsigned KV_NH=2, KV_VB=131072;
    static constexpr unsigned tile_count=GT/4;
    static constexpr unsigned address_bits=7,data_bits=512,mask_bits=512;
    // Already physically present inside unchanged ot_qwen_rom_tile_w12.
    static constexpr unsigned capture_register_bits_per_tile=1+7+512+512;
    static constexpr unsigned SRAM_instances_per_tile=2;
    static constexpr unsigned SRAM_depth=128,SRAM_width=256;
};
// Invoke while the core clock is LOW and settled, BEFORE the common rising
// edge. Then the enclosing binding assigns the same clk to wrapper and all
// tiles before evaluating them. Never use hclk for this connection. It is
// not an extra pipeline register; it connects the existing wrapper register.
// The wrapper rst_n and tile rst_n are the SAME actual reset net. Resetting
// or replaying a tile separately would destroy accepted KV capture state.
template<class CombinedDie,class Tile>
inline void wire_tile_capture_inputs(const CombinedDie& die,Tile& tile,
                                     unsigned tile_index,bool actual_rst_n) {
    if(tile_index>=TileCaptureSourceShape::tile_count)
        throw std::out_of_range("full-shape tile capture index");
    tile.rst_n=actual_rst_n;
    const auto enable=(uint32_t(die.kvw_ce[tile_index/32])>>(tile_index%32))&1u;
    tile.kvw_ce=enable;
    if(!enable) return; // Same hold behavior as the pinned native fabric.
    const std::size_t bit=std::size_t(tile_index)*7;
    const unsigned offset=bit%32;
    const std::size_t word=bit/32;
    uint32_t addr=uint32_t(die.kvw_addr[word])>>offset;
    // Unaligned 7-bit addresses may straddle two Verilated 32-bit words.
    if(offset>25) addr|=uint32_t(die.kvw_addr[word+1])<<(32-offset);
    tile.kvw_addr=addr&127u;
    for(unsigned k=0;k<16;++k) {
        tile.kvw_data[k]=die.kvw_data[std::size_t(tile_index)*16+k];
        tile.kvw_mask[k]=die.kvw_mask[std::size_t(tile_index)*16+k];
    }
}
// No state-retirement function belongs here. Existing service kv_ok covers
// fill/capture inflight; kv_write_drained separately covers tagged HBM ACKs.
// Binding retirement must retain BOTH plus row drain and actual core done.
// Generation/reverse/clock-domain admission remains with the real producer.
} // namespace qwen_combined
