#pragma once
#include <cstdint>
#include <stdexcept>

namespace dsrom {
// Uses the actual DieBase C8 methods. The enclosing runtime owns all evals,
// clocks, reset, field/attention/link propagation and the source restore writer.
// Call before_edge before the rising eval; after_edge after all models settle.
class NativeEntryDriver {
    uint32_t token_, pos_, user_;
    uint16_t epoch_, entry_;
    uint64_t identity_;
    bool accepted_=false, launched_=false, retired_=false;
    bool offer_sample_=false, restore_sample_=false;
public:
    NativeEntryDriver(uint32_t token,uint32_t pos,uint32_t user,
                      uint16_t epoch,uint16_t entry)
        : token_(token),pos_(pos),user_(user),epoch_(epoch),entry_(entry),
          identity_((uint64_t(epoch)<<31)|(uint64_t(user)<<21)|pos) {
        if(token>=(1u<<21)||pos>=(1u<<21)||user>=(1u<<10)||entry>=(1u<<14))
            throw std::runtime_error("native entry descriptor bounds");
    }
    template<class Die,class Restore> void before_edge(Die& die,Restore& restore) {
        if(die.fault())throw std::runtime_error("native entry caller fault");
        offer_sample_=false; restore_sample_=false;
        die.c8_restored(false);
        die.c8_offer(!accepted_&&!retired_,token_,pos_,user_,epoch_,entry_);
        if(!accepted_&&!retired_)offer_sample_=die.c8_ready();
        if(accepted_&&!launched_&&!retired_) {
            uint64_t identity; uint32_t token; uint16_t entry;
            if(die.c8_context(identity,token,entry)) {
                if(identity!=identity_||token!=token_||entry!=entry_)
                    throw std::runtime_error("native context differs from accepted entry");
                // Provider returns true only on its actual source-owned input /
                // context write completion. No expected-state copy or timer ACK.
                restore_sample_=restore(die,identity,token,entry);
                die.c8_restored(restore_sample_);
            }
        }
    }
    template<class Die> void after_edge(Die& die) {
        if(die.fault())throw std::runtime_error("native entry runtime fault");
        accepted_|=offer_sample_; launched_|=restore_sample_;
        uint64_t identity;
        if(die.c8_retired(identity)) {
            if(!launched_||retired_||identity!=identity_)
                throw std::runtime_error("unmatched native retirement");
            retired_=true;
        }
        offer_sample_=false; restore_sample_=false;
    }
    bool accepted() const {return accepted_;}
    bool launched() const {return launched_;}
    bool retired() const {return retired_;}
    uint64_t identity() const {return identity_;}
};
} // namespace dsrom
