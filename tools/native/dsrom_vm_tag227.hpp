#pragma once
#include <array>
#include <cstdint>
#include <set>
#include <stdexcept>

// New COMPONENT wire ABI v1, not a recovered native full-C8 encoder.
// Root-selected experiment layout. This is NOT production fullctx169.
// Fields are supplied from the actual compiled selection / held source lease.
namespace dsrom { namespace component_tag227 {
using Tag227 = std::array<std::uint32_t, 8>;
struct ComponentContext {
    std::uint64_t identity47, token17, stage7, rank2, pair12, phase10, entry14;
};
struct Envelope {
    ComponentContext context;
    std::uint64_t reset_era, batch, request_id;
};
constexpr const char* ABI = "COMPONENT_TAG227_V1";
inline void require_width(std::uint64_t value, unsigned width) {
    if (value >= (std::uint64_t{1} << width))
        throw std::out_of_range("TAG227 field overflow; truncation prohibited");
}
inline void put(Tag227& out, unsigned offset, unsigned width, std::uint64_t value) {
    require_width(value, width);
    for (unsigned i=0; i<width; ++i)
        if ((value >> i) & 1u) out[(offset+i)/32] |= std::uint32_t{1} << ((offset+i)%32);
}
inline std::uint64_t get(const Tag227& in, unsigned offset, unsigned width) {
    std::uint64_t value=0;
    for (unsigned i=0; i<width; ++i)
        value |= std::uint64_t((in[(offset+i)/32] >> ((offset+i)%32)) & 1u) << i;
    return value;
}
inline void validate(const Tag227& in) {
    if ((in[7] & ~std::uint32_t{7}) || get(in,109,32) || get(in,141,28))
        throw std::invalid_argument("COMPONENT_TAG227 reserved/padding bits must be zero");
    if(get(in,64,7)>80 || get(in,73,12)>2416)
        throw std::out_of_range("COMPONENT_TAG227 stage/pair source range");
}
// Component context [108:0], RESERVED [168:109] (60 bits, NOT fullctx payload).
// identity47[46:0], token17[63:47], stage7[70:64], rank2[72:71],
// pair12[84:73], phase10[94:85], entry14[108:95].
// era[200:169], batch[216:201], request_id[226:217]; storage [255:227]=0.
inline Tag227 pack(const Envelope& e) {
    if(e.context.stage7>80 || e.context.pair12>2416)
        throw std::out_of_range("COMPONENT_TAG227 stage/pair source range");
    Tag227 out{};
    put(out,0,47,e.context.identity47); put(out,47,17,e.context.token17);
    put(out,64,7,e.context.stage7); put(out,71,2,e.context.rank2);
    put(out,73,12,e.context.pair12); put(out,85,10,e.context.phase10);
    put(out,95,14,e.context.entry14); put(out,169,32,e.reset_era);
    put(out,201,16,e.batch); put(out,217,10,e.request_id);
    return out;
}
inline Envelope unpack(const Tag227& in) {
    validate(in);
    return {{get(in,0,47),get(in,47,17),get(in,64,7),get(in,71,2),get(in,73,12),
             get(in,85,10),get(in,95,14)},
            get(in,169,32),get(in,201,16),get(in,217,10)};
}
// Root-authorized experiment identity only: epoch1/user0/position0/token0.
// Selection fields have NO defaults; callers supply actual compiled values.
inline ComponentContext experiment_context(std::uint64_t stage, std::uint64_t rank,
                                          std::uint64_t pair, std::uint64_t phase,
                                          std::uint64_t entry) {
    ComponentContext ctx{std::uint64_t{1}<<31,0,stage,rank,pair,phase,entry};
    (void)pack({ctx,1,0,0});return ctx;
}
// Backend rd_owner is eight little-endian 32-bit words (VlWide<8> compatible).
template<class Wide> inline void copy_to(const Tag227& tag, Wide& dst) {
    validate(tag); for (unsigned i=0;i<8;++i) dst[i]=tag[i];
}
template<class Wide> inline Tag227 read_from(const Wide& src) {
    Tag227 tag{};for(unsigned i=0;i<8;++i)tag[i]=src[i];validate(tag);return tag;
}
// wr_owner/ack_owner contains FOUR concatenated 227-bit tags, NOT four aligned
// eight-word tags. Bank b begins at bit b*227 (total 908 bits / 29 words).
template<class Wide> inline void copy_bank_to(const Tag227& tag, unsigned bank, Wide& dst) {
    validate(tag);if(bank>=4)throw std::out_of_range("TAG227 bank");
    for(unsigned i=0;i<227;++i){
        unsigned bit=bank*227+i;auto mask=std::uint32_t{1}<<(bit%32);
        dst[bit/32]=(dst[bit/32]&~mask)|(((tag[i/32]>>(i%32))&1u)?mask:0u);
    }
}
template<class Wide> inline Tag227 read_bank_from(const Wide& src,unsigned bank) {
    if(bank>=4)throw std::out_of_range("TAG227 bank");
    Tag227 tag{};
    for(unsigned i=0;i<227;++i){unsigned bit=bank*227+i;
        if((src[bit/32]>>(bit%32))&1u)tag[i/32]|=std::uint32_t{1}<<(i%32);
    }return tag;
}
// Software callback counter/identity ledger only; does not add RTL state or
// qualify raw N+3 visibility. Caller invokes actual_accept only on PRE rst_n &&
// backend accept strobe; qualified_retire only after its actual retirement proof.
class AcceptedIdLedger {
    ComponentContext context_;std::uint64_t era_,batch_,next_=0;
    std::set<std::uint16_t> live_;
public:
    AcceptedIdLedger(ComponentContext context,std::uint64_t era,std::uint64_t batch)
        :context_(context),era_(era),batch_(batch) {(void)offer_tag();}
    Tag227 offer_tag() const {return pack({context_,era_,batch_,next_});}
    void actual_accept(const Tag227& offered) {
        if(offered!=offer_tag())throw std::invalid_argument("TAG227 changed/stale offered identity");
        live_.insert(static_cast<std::uint16_t>(next_));++next_;
    }
    void qualified_retire(const Tag227& returned) {
        auto e=unpack(returned);
        if(pack({context_,era_,batch_,e.request_id})!=returned || !live_.count(e.request_id))
            throw std::invalid_argument("TAG227 stale/wrong/duplicate retirement");
        live_.erase(e.request_id);
    }
    std::size_t outstanding()const{return live_.size();}
    void next_batch() {
        if(!live_.empty())throw std::logic_error("TAG227 batch still owns accepted debt");
        require_width(batch_+1,16);++batch_;next_=0;
    }
    void reset_after_quiescence(std::uint64_t new_era,bool source_quiescent) {
        if(!source_quiescent||!live_.empty()||new_era<=era_)
            throw std::logic_error("TAG227 reset cannot erase debt or reuse era");
        require_width(new_era,32);era_=new_era;batch_=0;next_=0;
    }
};
}} // namespace dsrom::component_tag227
