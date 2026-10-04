#include "s81_source_caller_plan.hpp"
#include "dsrom_s81_source_scheduler.hpp"
#include <cstdio>
#include <filesystem>
#include <memory>

namespace {
void check_rank(const DsromS81SourceRank& rank,DsromS81Runtime& runtime,int lane) {
    const auto& offer=rank.offer;
    DsromC8SourceDispatch checked(offer);
    if(runtime.stage<0 || runtime.stage>=81 || runtime.dies.size()!=4 ||
       offer.die_id!=4*runtime.stage+lane || !runtime.dies.at(lane))
        throw std::runtime_error("source plan native stage/rank owner mismatch");
    if(!rank.input_visible || !rank.remote_drained || !rank.all_copies_drained ||
       (rank.saved.empty() && !rank.restore_inputs) ||
       (!rank.saved.empty() && !rank.retained_source_span))
        throw std::runtime_error("source plan actual input/lease/remote/allcopy authorities missing");
}

// A cold source uses its actual producer, while a carried source uses Sagan's
// native VM hooks. Both require the same positive input and drain authorities.
class RankRun {
    DsromS81Runtime& runtime;
    DsromS81SourceRank& source;
    std::unique_ptr<DsromS81SourceCallerHooks> carry;
    bool retired=false;
public:
    RankRun(DsromS81Runtime& r,DsromS81SourceRank& s):runtime(r),source(s) {
        if(!s.saved.empty())carry.reset(new DsromS81SourceCallerHooks(r,s.offer,s.saved,
            s.retained_source_span,s.input_visible,s.remote_drained,s.all_copies_drained));
    }
    bool capture() {return !carry || carry->capture_sources();}
    bool restore(const DsromC8SourceOffer& offer) {
        // Dispatch calls this only for a matching accepted native C8 context.
        // Real producer writes may stall; no timer or expected-VM fallback.
        if(source.restore_inputs && !source.restore_inputs(offer))return false;
        if(carry && !carry->restore(offer))return false;
        return source.input_visible(offer);
    }
    bool drain(const DsromC8SourceOffer& offer) {
        if(carry)return carry->drain(offer);
        auto& die=*runtime.dies.at(offer.die_id%4);
        uint64_t identity;
        if(die.c8_retired(identity)) {
            if(identity!=offer.identity)throw std::runtime_error("foreign cold-source retirement");
            retired=true;
        }
        if(die.fault())throw std::runtime_error("actual cold-source native fault");
        return retired && die.capture_visible(offer.identity) &&
            source.remote_drained(offer) && source.all_copies_drained(offer);
    }
};
}

extern "C" int dsrom_s81_source_main(DsromS81Runtime& runtime,const char* output) {
    auto plan=dsrom_s81_bind_source(runtime);
    if(plan.groups.empty() || !runtime.tick || !runtime.cycle)
        throw std::runtime_error("actual source program and native clock required");
    // Check the complete bound schedule before issuing the first offer.
    for(auto& group:plan.groups)for(int rank=0;rank<4;rank++) {
        check_rank(group.ranks[rank],runtime,rank);
        const auto& offer=group.ranks[rank].offer;
        const auto& first=group.ranks[0].offer;
        if(offer.identity!=first.identity || offer.token!=first.token)
            throw std::runtime_error("source plan TP4 context mismatch");
    }
    if(!output || !*output)throw std::runtime_error("actual source output directory required");
    std::filesystem::create_directories(output);
    const auto path=std::filesystem::path(output)/"source_dispatch.tsv";
    std::unique_ptr<FILE,decltype(&fclose)> journal(fopen(path.c_str(),"wx"),fclose);
    if(!journal)throw std::runtime_error("preserve existing source dispatch results / output unavailable");
    fprintf(journal.get(),"group\tstage\tidentity\ttoken\tentry0\tentry1\tentry2\tentry3\tbegin_cycle\tdrained_cycle\n");
    fflush(journal.get());
    size_t index=0;
    std::array<size_t,4> next_prime{};
    for(auto& group:plan.groups) {
        std::vector<std::unique_ptr<RankRun>> ranks;
        std::vector<DsromC8SourceOffer> offers;
        for(auto& rank:group.ranks) {
            ranks.emplace_back(new RankRun(runtime,rank));offers.push_back(rank.offer);
        }
        const long begin=runtime.cycle();
        // Capture every old producer BEFORE any next-context offer can replace
        // its capture identity, including same-group saved VM carry.
        for(;;) {
            bool captured=true;
            for(const auto& rank:group.ranks)for(const auto& span:rank.saved)
                if(span.producer->dies.at(span.producer_die%4)->fault())
                    throw std::runtime_error("actual saved-context producer fault");
            for(auto& rank:ranks)captured=rank->capture() && captured;
            if(captured)break;
            runtime.tick();
        }
        for(auto& rank:group.ranks)if(rank.begin)rank.begin(rank.offer);
        // Preserve the native window priming handshake for source-bound rows.
        // All ranks are driven before each single shared rising edge.
        for(;;) {
            bool pending=false;
            std::array<bool,4> accepted{};
            for(int rank=0;rank<4;rank++) {
                auto& die=*runtime.dies.at(rank);
                pending |= next_prime[rank]<die.primes.size();
                const bool valid=next_prime[rank]<die.primes.size();
                die.prime(valid,valid?die.primes[next_prime[rank]]:0);
                accepted[rank]=valid && die.prime_ready();
            }
            if(!pending)break;
            runtime.tick();
            for(int rank=0;rank<4;rank++)if(accepted[rank])next_prime[rank]++;
        }
        auto restore=[&](const DsromC8SourceOffer& offer){return ranks.at(offer.die_id%4)->restore(offer);};
        auto drain=[&](const DsromC8SourceOffer& offer){return ranks.at(offer.die_id%4)->drain(offer);};
        dsrom_s81_run_group(runtime,offers,restore,drain);
        const auto& first=offers[0];
        fprintf(journal.get(),"%zu\t%d\t%llu\t%u\t%u\t%u\t%u\t%u\t%ld\t%ld\n",
            index++,runtime.stage,(unsigned long long)first.identity,first.token,
            offers[0].entry,offers[1].entry,offers[2].entry,offers[3].entry,begin,runtime.cycle());
        if(fflush(journal.get()) || ferror(journal.get()))
            throw std::runtime_error("source dispatch output write failed");
    }
    return 0;
}
