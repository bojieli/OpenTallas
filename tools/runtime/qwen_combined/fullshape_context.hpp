#pragma once
// Additive driver support for the source-exact Qwen W12 / REAL_MEM layout.
// This only maps raw bytes and identities. It never serves an HBM response,
// converts numerical values, asserts a drain, or grants generation reuse.
#include <cstdint>
#include <stdexcept>
namespace qwen_combined {
constexpr unsigned groups=6144, tiles=groups/4, sw=64;
constexpr unsigned ranks=4, layers=36, positions=8192, heads_per_rank=2, hd=128;
constexpr unsigned nw=18, segment_bits=6, collective_tag_bits=2+2*nw+segment_bits;
constexpr unsigned sector_bytes=32, layer_sectors=131072;
enum class Kind { K, V };
struct Context {
    unsigned rank, layer, position, token;
    void check() const {
        if(rank>=ranks || layer>=layers || position>=positions || token>=151936)
            throw std::out_of_range("full-shape checkpoint context");
    }
};
struct Location {
    // The write input is local to a layer; the REAL_MEM service adds lbase.
    uint32_t scalar_address, sector_address;
    unsigned stack, byte_in_sector, tile, slice_word, byte_in_slice;
};
inline Location locate(const Context& c, Kind kind, unsigned head, unsigned dim) {
    c.check();
    if(head>=heads_per_rank || dim>=hd) throw std::out_of_range("KV head/dimension");
    const unsigned p=c.position,t=p/16,q=dim/16;
    uint32_t word; unsigned lane,tile,local,slice_byte;
    if(kind==Kind::K) {
        word=head*65536+t*128+dim; lane=p%16;
        tile=(t%48)*32+dim/4; local=(t/48)*2+head;
        slice_byte=(dim%4)*16+lane;
    } else if(kind==Kind::V) {
        word=131072+head*65536+p*8+q; lane=dim%16;
        tile=q*128+(p%512)/4; local=22+(p/512)*2+head;
        slice_byte=(p%4)*16+lane;
    } else throw std::invalid_argument("KV kind");
    const uint32_t sector=c.layer*layer_sectors+word/2;
    if(tile>=tiles || local>=128 || slice_byte>=64 || sector>=(1u<<24))
        throw std::out_of_range("actual physical endpoint capacity");
    return {word*16+lane,sector,(sector>>9)&3,(word%2)*16+lane,tile,local,slice_byte};
}
inline uint64_t collective_tag(const Context& c,unsigned generation,unsigned segment) {
    c.check();
    if(generation>=4 || segment>=64) throw std::out_of_range("collective identity");
    // Literal TAG_FULL sys/async_sys order: {gen, pos, token, segment}.
    // Packing a value is not permission to reuse its generation namespace.
    return (uint64_t(generation)<<(2*nw+segment_bits)) |
           (uint64_t(c.position)<<(nw+segment_bits)) |
           (uint64_t(c.token)<<segment_bits) | segment;
}
inline void require_join_geometry(unsigned g,unsigned stream_width,unsigned count_width,
                                  unsigned tag_width,bool real_mem,bool tag_full) {
    if(g!=groups || stream_width!=sw || count_width!=nw || tag_width<collective_tag_bits || !real_mem || !tag_full)
        throw std::invalid_argument("reduced/tied/position-aliasing source is not the selected full-shape join");
}
} // namespace qwen_combined
