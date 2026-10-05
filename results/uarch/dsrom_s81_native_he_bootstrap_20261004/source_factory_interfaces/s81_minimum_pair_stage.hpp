#pragma once
#include <array>
#include <cstdint>
#include <deque>
#include <stdexcept>
#include "s81_native_drain.hpp"
#include "s81_minimum_runtime.hpp"
#include "s81_embedding_abi.h"

// Simulation cuts only: no arithmetic, private clock, core or field replicas.
// The caller supplies the retained spine broadcast and clocks a real Vpq/Vpb.
// It must supply the exact source pair CFG/ROM DPI provider before model eval.
namespace dsrom_s81_minimum {
// One public typed ABI, owned by the minimum native element host.
using PairDrive = DsromS81PairDrive;
using PairResult = DsromS81PairResult;
struct Partial {
    bool valid=false, error=false;
    uint32_t fp32_bits=0;
    uint16_t row=0;
    uint8_t segment=0, segments=0, position=0;
};
inline Partial partial(const PairResult& r,unsigned leaf) {
    if(leaf>=2)throw std::runtime_error("complete NB2 pair leaf bounds");
    return {bool((r.valid>>leaf)&1),bool((r.error>>leaf)&1),
        uint32_t(r.values>>(32*leaf)),uint16_t(r.rows>>(16*leaf)),
        uint8_t((r.segments>>(5*leaf))&31),
        uint8_t((r.segment_counts>>(5*leaf))&31),
        uint8_t((r.positions>>(3*leaf))&7)};
}
// Raw backend ports: element address19 -> 512-bit word address15.
// Tags are the ACTUAL source-owned TAG_W227 encoding, never synthesized here.
struct VmWord {
    uint16_t address=0, mask=0;
    std::array<uint32_t,16> data{};
    std::array<uint32_t,8> owner{};
};
struct VmReceipt {
    uint16_t address=0, mask=0;
    std::array<uint32_t,8> owner{};
};
struct CaptureOwner {
    uint64_t identity=0;
    uint16_t phase=0, row=0;
    uint8_t root=0, position=0;
    uint32_t element_address=0;
};
// This minimum vehicle submits one captured field word per native masked write.
// Merged multi-root publication requires explicit per-member receipts, not a
// scalar count supplied by the host, and is deliberately refused here.
// Observer of accepted native backend commands and matched old-head ACKs.
// The four entries per bank are a bounded TEST receipt ledger, not hardware
// write seats. offer() cannot release capture or assert physical visibility.
class NativeVmReceipts {
    struct Held {VmWord word;CaptureOwner source;uint8_t field_words;};
    std::array<std::deque<Held>,4> pending{};
    bool quarantined=false;
    uint64_t accepted_count=0,visible_count=0;
    static void validate(unsigned bank,const VmWord& w,const CaptureOwner& s,unsigned n) {
        if(bank>=4 || w.address>=32768 || (w.address&3)!=bank || !w.mask ||
           (w.owner[7]&~7u) || s.identity>=(1ull<<47) || s.phase>=1024 ||
           s.root>=128 || s.position>=8 || s.element_address>=(1u<<19) ||
           (s.element_address>>4)!=w.address || n!=1 ||
           n>unsigned(__builtin_popcount(w.mask)))
            throw std::runtime_error("source bank4 word/owner/mask/address bounds");
    }
public:
    bool can_observe_accept(unsigned bank) const {
        return bank<4 && !quarantined && pending[bank].size()<4;
    }
    void accepted(unsigned bank,const VmWord& w,const CaptureOwner& s,
                  unsigned field_words,bool actual_wr_accept) {
        if(!actual_wr_accept)throw std::runtime_error("no native positive write acceptance");
        validate(bank,w,s,field_words);
        if(!can_observe_accept(bank))throw std::runtime_error("native receipt ledger overflow/quarantine");
        pending[bank].push_back({w,s,uint8_t(field_words)});accepted_count+=field_words;
    }
    unsigned visible(unsigned bank,const VmReceipt& r,bool actual_wr_ack) {
        if(bank>=4 || !actual_wr_ack || pending[bank].empty())
            throw std::runtime_error("native visible ACK lacks accepted old owner");
        const auto h=pending[bank].front();
        if(h.word.address!=r.address || h.word.mask!=r.mask || h.word.owner!=r.owner)
            throw std::runtime_error("native visible ACK wrong owner/address/mask");
        pending[bank].pop_front();visible_count+=h.field_words;
        return h.field_words; // caller feeds matched counted reverse receipts
    }
    void warm_reset(){quarantined=true;} // accepted debts remain; never clears
    void cold_fenced(bool actual_all_copy_fence) {
        if(!actual_all_copy_fence || outstanding()!=0)
            throw std::runtime_error("cold reset lacks zero-debt all-copy fence");
        quarantined=false;
    }
    uint64_t outstanding() const {return accepted_count-visible_count;}
    bool empty() const {return outstanding()==0;}
    bool quarantine() const {return quarantined;}
};
// Existing embedding ABI supplies raw leaf ports; no full parent image/core.
// Caller uses the LIVE source reader/socket and actual downstream commit_ready.
class EmbeddingLeaf {
    void* instance;
public:
    EmbeddingLeaf():instance(s81_embedding_create()) {
        if(!instance)throw std::runtime_error("native embedding model unavailable");
    }
    ~EmbeddingLeaf(){s81_embedding_destroy(instance);}
    EmbeddingLeaf(const EmbeddingLeaf&)=delete;
    EmbeddingLeaf& operator=(const EmbeddingLeaf&)=delete;
    S81EmbeddingOutput evaluate(const S81EmbeddingInput& in) {
        S81EmbeddingOutput out{};s81_embedding_eval(instance,&in,&out);return out;
    }
    S81EmbeddingOutput edge(const S81EmbeddingInput& in) {
        S81EmbeddingOutput out{};s81_embedding_edge(instance,&in,&out);return out;
    }
};
// Popper's observer stays on REAL endpoints. A single-pair experiment must
// not declare imaginary peer offers/retirements to make group_complete true.
using NativeDrain=DsromS81NativeDrain;
} // namespace dsrom_s81_minimum
