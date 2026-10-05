#include "s81_wavefront_result_ledger.hpp"
#include <cassert>

template<class F> void refuses(F f) {
    bool failed=false;try{f();}catch(const std::runtime_error&){failed=true;}assert(failed);
}
DsromC8SourceOffer source(unsigned epoch,unsigned position) {
    return {0,13,position,7,uint16_t(epoch),4,(uint64_t(epoch)<<31)|(uint64_t(7)<<21)|position};
}
int main() {
    // Ledger unit only: event calls below exercise the exact handlers used
    // by native group acceptance/restoration and Boole's source observer.
    DsromS81WaveResultLedger ledger(8);
    const auto a=source(1,8),b=source(1,9),retry=source(2,8);
    refuses([&](){ledger.lookup(7,8);});
    ledger.accepted(a,0);refuses([&](){ledger.lookup(7,8);});
    ledger.restored(a.identity,0);ledger.accepted(b,1);ledger.restored(b.identity,1);
    refuses([&](){ledger.lookup(7,9);}); // accepted but not next actual RESULT
    const auto owner=ledger.lookup(7,8);assert(owner.identity==a.identity);
    ledger.result_received(owner);assert(ledger.retained()==2);
    refuses([&](){ledger.lookup(7,8);}); // stale/duplicate even before drain
    ledger.accepted(retry,2);ledger.restored(retry.identity,2);
    refuses([&](){ledger.lookup(7,8);}); // retained old generation ambiguous
    ledger.fabric_drained(a.identity,0);assert(ledger.retained()==3);
    ledger.all_copies_drained(a.identity,0);assert(ledger.retained()==2);
    ledger.cancel_received(b.identity,1);assert(ledger.retained()==2);
    // Cancel receipt alone cannot discard a legitimate in-flight RESULT
    // that the actual controller will squash in its retained issue order.
    const auto canceled_result=ledger.lookup(7,9);assert(canceled_result.identity==b.identity);
    ledger.result_received(canceled_result);assert(ledger.retained()==2);
    ledger.fabric_drained(b.identity,1);ledger.all_copies_drained(b.identity,1);
    assert(ledger.retained()==1&&ledger.lookup(7,8).identity==retry.identity);
    ledger.warm_quarantine();assert(ledger.retained()==1);
    refuses([&](){ledger.accepted(source(3,10),3);});
}
