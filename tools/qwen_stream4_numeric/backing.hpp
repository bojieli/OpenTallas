#pragma once
// Host-only preload/readback of the canonical numerical provider's public mem.
// Pass rm_hbm_mem(rank_root) from the generated canonical 5.050 accessor.
// The caller selects rank0..3; each backing holds all 36 layer histories.
// Preload before ticking the protocol; read back after genuine ACK/debt drain.
#include <cstddef>
#include <cstdint>
#include <stdexcept>
namespace qwen_s4_numeric {
constexpr std::size_t layers=36, sectors=131072, word_bytes=32;
template<class Backing> inline void extent(const Backing&) {
    static_assert(sizeof(Backing)==layers*sectors*word_bytes,
                  "STREAM4 numerical backing must contain all36 layers");
}
template<class Backing> inline void preload_history_layer(
    Backing& mem, unsigned layer, const std::uint8_t* src, std::size_t bytes) {
    extent(mem);
    if(layer>=layers || !src || bytes!=sectors*word_bytes)
        throw std::runtime_error("released STREAM4 history extent/layer mismatch");
    for(std::size_t s=0;s<sectors;++s) for(unsigned w=0;w<8;++w) {
        const auto* p=src+s*word_bytes+w*4;
        mem[layer*sectors+s][w]=std::uint32_t(p[0])|
            (std::uint32_t(p[1])<<8)|(std::uint32_t(p[2])<<16)|(std::uint32_t(p[3])<<24);
    }
}
template<class Backing> inline void readback_word(
    const Backing& mem, unsigned layer, unsigned sector, std::uint8_t* dst) {
    extent(mem);
    if(layer>=layers || sector>=sectors || !dst)
        throw std::runtime_error("STREAM4 readback address/target mismatch");
    for(unsigned w=0;w<8;++w) {
        const std::uint32_t v=mem[layer*sectors+sector][w];
        for(unsigned b=0;b<4;++b) dst[w*4+b]=std::uint8_t(v>>(8*b));
    }
}
} // namespace qwen_s4_numeric
