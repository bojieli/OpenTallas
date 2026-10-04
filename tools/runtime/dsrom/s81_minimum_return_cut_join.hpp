#pragma once
#include "s81_minimum_return_participant.hpp"

namespace dsrom_s81_minimum {
// Literal packed Vcut root inputs. Modify ONLY the enrolled region; missing
// peer roots remain obligations. This helper never evaluates or clocks Vcut.
template<class Packed> inline void root_pin_field(Packed& pins,unsigned offset,
                                                 unsigned width,uint32_t value) {
    if(!width||width>32||(width<32&&(value>>width)))
        throw std::runtime_error("native root pin width");
    for(unsigned i=0;i<width;i++) {
        const unsigned bit=offset+i,word=bit/32;
        const uint32_t mask=uint32_t(1)<<(bit%32);
        pins[word]=(pins[word]&~mask)|(((value>>i)&1)?mask:0);
    }
}

template<class Cut,class Return> DsromS81MinimumParticipant
join_return_to_input_cut(Cut& cut,Return& returned) {
    auto participant=returned.participant();
    auto prepare=participant.prepare;
    participant.prepare=[&cut,&returned,prepare](const DsromS81PairResult& result) {
        // Participant order: input -> return -> bank; ALL prepares precede
        // ANY rising evaluation. Sagan remains the only Vcut eval owner.
        prepare(result);
        // Shared cold_start invokes prepare before any admitted context.
        // No region identity or peer completion may be invented then.
        if(!returned.has_admitted_phase())return;
        const unsigned region=returned.root_region();
        if(region>=128)throw std::runtime_error("native root region aperture");
        const auto ports=returned.root_output();
        root_pin_field(cut.fr_v,region,1,ports.valid);
        root_pin_field(cut.fr_e,region,1,ports.error);
        root_pin_field(cut.fr_row,16*region,16,ports.row);
        root_pin_field(cut.fr_pos,3*region,3,ports.position);
        root_pin_field(cut.fr_fp32,32*region,32,ports.fp32);
        root_pin_field(cut.fr_bf16,16*region,16,ports.bf16);
        // Sticky fault retains an existing peer fault. Never replace it with
        // a selected-root-only quiet or phase-idle completion assertion.
        cut.fr_fault=bool(cut.fr_fault)||returned.fault();
    };
    return participant;
}
} // namespace dsrom_s81_minimum
