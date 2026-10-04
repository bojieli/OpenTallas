#pragma once
#include "s81_qe_checkpoint_word_reader.hpp"
#include <functional>
#include <memory>

// Reuse the existing private released-byte transport. This callback belongs in
// Arch's ONE phase-selected pair-source closure, before the shared cold start.
// No native model, Vcut, tick, roots or publication authority is owned here.
using DsromL20MeCheckpointReader = DsromS81QeCheckpointWordReader;
using DsromL20MeMatrixRead = std::function<std::array<uint32_t,9>(unsigned,unsigned)>;
inline DsromL20MeMatrixRead dsrom_L20_me_matrix_read(
    std::shared_ptr<DsromL20MeCheckpointReader> source,
    unsigned stage,unsigned rank,unsigned pair) {
    if(!source || stage!=37 || rank>=4 || pair>=2417)
        throw std::runtime_error("L20 ME selected source owner");
    return [source=std::move(source),stage,rank,pair](unsigned bank,unsigned row) {
        if(bank>=4 || row>=4096)
            throw std::runtime_error("L20 ME native bank/row");
        return source->read(stage,rank,4*pair+bank,row);
    };
}
// Reader ctor script must select dsrom_L20_native_me_matrix_provider.py;
// node is L20.I24/I30/I42/I68/I69/I86, fragment is 0 or ordered wo_a 0/1.
// Keep the shared callback until accepted native reads/returns drain. CFG is
// supplied by the same existing selected canonical dispatch, not this reader.

#include "s81_minimum_runtime.hpp"
#include <optional>
#include <map>

// Decoder is the generated ot_chip_v41x_woa_fp8_decode, unchanged. Sixteen
// instances share the caller's context/edge, one registered conversion edge.
// Not a private tick loop. Prefetch/request before BF macro consumption; the
// caller must stall phase admission until ready(), never force field ready.
template<class Decoder> class DsromL20MeNativeConversion {
    DsromL20MeMatrixRead raw;
    std::array<std::unique_ptr<Decoder>,16> lanes;
    std::array<uint32_t,9> input{},output{};
    unsigned bank_=0,row_=0;
    bool pending=false,complete=false,bad=false;
public:
    DsromL20MeNativeConversion(VerilatedContext* context,DsromL20MeMatrixRead released):raw(std::move(released)) {
        if(!raw||!context)throw std::runtime_error("ME raw provider/context required");
        for(auto& lane:lanes)lane=std::make_unique<Decoder>(context);
    }
    void request(unsigned bank,unsigned row) {
        if(pending||complete||bad)throw std::runtime_error("ME decoder word still owned");
        input=raw(bank,row);bank_=bank;row_=row;pending=true;
    }
    bool ready()const{return complete&&!bad;}
    std::array<uint32_t,9> read(unsigned bank,unsigned row)const {
        if(!ready()||bank!=bank_||row!=row_)throw std::runtime_error("ME native conversion not completed/matched");
        return output;
    }
    // Retire only after the caller's actual macro capture. Request/convert do
    // not release the word; no new ACK or source ownership ledger is invented.
    void retire(unsigned bank,unsigned row) {
        (void)read(bank,row);complete=false;
    }
    DsromS81MinimumParticipant participant() {
        return {"L20_ME_raw_FP8_native_BF16",
          [this](const DsromS81PairResult&) {
            for(unsigned i=0;i<16;++i){auto& d=*lanes[i];
                const auto packed=(input[i/2]>>(16*(i%2)))&65535;
                d.in_v=pending;d.code=packed&255;d.scale=packed>>8;}
          },
          [this](bool reset) {
            if(!reset&&(pending||complete))throw std::runtime_error("reset with owned ME decoder word");
            bool launched=pending;
            for(auto& lane:lanes){lane->rst_n=reset;lane->clk=1;lane->eval();}
            if(reset&&launched){output.fill(0);
              for(unsigned i=0;i<16;++i){auto& d=*lanes[i];
                if(!d.out_v||d.fault)bad=true;
                output[i/2]|=uint32_t(d.value)<<(16*(i%2));}
              pending=false;complete=true;}
          },
          [this](bool reset){for(auto& lane:lanes){lane->rst_n=reset;lane->clk=0;lane->eval();}},
          [this](){return bad;}};
    }
};

// Optional finite simulation ROM image: prefill ONLY by completed native
// decoder words before accepting the field phase. No host dequantization.
// One object per exact node/rank/fragment/borrowed pair; keep it through original phase drain.
// max_words = provider.word_requests(pair).size(), from selected canonical plans.
template<class Decoder> class DsromL20MeConvertedMatrix {
    DsromL20MeNativeConversion<Decoder> conversion;
    const size_t max_words;
    std::map<std::pair<unsigned,unsigned>,std::array<uint32_t,9>> words;
    std::optional<std::pair<unsigned,unsigned>> requested;
    bool sealed=false;
public:
    DsromL20MeConvertedMatrix(VerilatedContext* context,DsromL20MeMatrixRead raw,size_t source_word_count)
        :conversion(context,std::move(raw)),max_words(source_word_count) {
        if(!max_words||max_words>4*4096*2417ull)
            throw std::runtime_error("ME canonical word extent required");
    }
    void request(unsigned bank,unsigned row) {
        if(sealed||requested||words.size()==max_words||words.count({bank,row}))
            throw std::runtime_error("ME immutable conversion image ownership");
        conversion.request(bank,row);requested={{bank,row}};
    }
    bool ready()const{return conversion.ready();}
    void materialize() {
        if(!requested)throw std::runtime_error("ME no requested word");
        const auto [bank,row]=*requested;
        auto native=conversion.read(bank,row); // fail before insertion on fault/early
        if(!words.emplace(*requested,native).second)throw std::runtime_error("ME duplicate native word");
        conversion.retire(bank,row);requested.reset();
    }
    void seal() {
        if(requested||words.size()!=max_words)throw std::runtime_error("ME incomplete native image");
        sealed=true;
    }
    std::array<uint32_t,9> read(unsigned bank,unsigned row)const {
        if(!sealed)throw std::runtime_error("ME image not native-complete before field admission");
        auto found=words.find({bank,row});
        if(found==words.end())throw std::runtime_error("ME unowned source ROM word");
        return found->second;
    }
    DsromS81MinimumParticipant participant(){return conversion.participant();}
};
