#pragma once
// Standalone future-driver validation. No hardware or universal service bound.
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
#include <optional>

namespace w17_future {
inline uint64_t decimal(const char* raw, uint64_t maximum, bool zero, const char* name) {
    if (!raw || !*raw) throw std::invalid_argument(std::string(name)+": empty");
    uint64_t n=0;
    for (const unsigned char* p=reinterpret_cast<const unsigned char*>(raw);*p;++p) {
        if (*p<'0'||*p>'9') throw std::invalid_argument(std::string(name)+": unsigned decimal required");
        unsigned d=*p-'0';
        if (d>maximum || n>(maximum-d)/10) throw std::out_of_range(std::string(name)+": overflow/range");
        n=n*10+d;
    }
    if (!zero && n==0) throw std::invalid_argument(std::string(name)+": positive required");
    return n;
}
inline long cycles(const char* s,const char* name) {
    return static_cast<long>(decimal(s,std::numeric_limits<long>::max(),false,name));
}
inline int positive_int(const char* s,const char* name) {
    return static_cast<int>(decimal(s,std::numeric_limits<int>::max(),false,name));
}
inline int latency(const char* s,const char* name) {
    return static_cast<int>(decimal(s,std::numeric_limits<int>::max(),true,name));
}
inline bool boolean(const char* s,const char* name) { return decimal(s,1,true,name)!=0; }
inline long due_at(long now,int latency) {
    if(now<0||latency<0||now>std::numeric_limits<long>::max()-latency)
        throw std::out_of_range("link timestamp overflow");
    return now+latency;
}
inline long next_cycle(long now) {
    if(now<0||now==std::numeric_limits<long>::max()) throw std::out_of_range("cycle overflow");
    return now+1;
}
struct LinkAge { long enqueued, due, age, overdue; size_t queued; };
// Called AFTER link_step delivery. Original FIFO entry stores due, not enqueue;
// fixed original link latency reconstructs enqueue without changing scheduling.
inline LinkAge link_age(long now,long due,int latency,size_t count) {
    if(now<0||latency<0||due<latency) throw std::invalid_argument("invalid due timestamp");
    long enqueued=due-latency;
    if(enqueued>now||count==0) throw std::invalid_argument("future enqueue/empty queue");
    return {enqueued,due,now-enqueued,now>due?now-due:0,count};
}
struct Snapshot {
    uint32_t pc=0,busy=0,issue=0,fault=0,words=0,sticky_sources=0;
    uint64_t state=0;
    bool done=false;
};
struct Rank {
    bool seen=false,done=false,diagnostic_reported=false;
    uint32_t pc=0,sticky_fault=0;
    long last_pc=0;
    bool deadline_failed=false;
};
struct Verdict {
    bool all_done=false,success=false,fault=false,deadline=false,maxc=false;
    bool bound_missing=true;
    std::vector<size_t> pc_silent;
};
class Monitor {
    std::vector<Rank> ranks_;
    long start_,maxc_,diag_,last_cycle_;
    std::optional<long> operation_bound_; // none in actual future copy
    bool maxc_failed_=false;
public:
    Monitor(size_t ranks,long start,long maxc,long diagnostic,
            std::optional<long> test_only_operation_bound=std::nullopt)
      :ranks_(ranks),start_(start),maxc_(maxc),diag_(diagnostic),last_cycle_(start>=0?start-1:-1),
       operation_bound_(test_only_operation_bound) {
        if(!ranks||start<0||maxc<=0||diagnostic<=0||
           (operation_bound_&&*operation_bound_<=0)) throw std::invalid_argument("invalid monitor contract");
        for(auto& r:ranks_) r.last_pc=start;
    }
    Verdict sample(long cycle,const std::vector<Snapshot>& samples) {
        if(cycle<start_||cycle<=last_cycle_||samples.size()!=ranks_.size())
            throw std::invalid_argument("nonmonotonic/incomplete sample");
        for(const auto& s:samples)
            if(s.pc>=16384||s.busy>=32||s.issue>=8||s.fault>=256)
                throw std::invalid_argument("pinned port width");
        Verdict v;v.bound_missing=!operation_bound_;
        for(size_t i=0;i<ranks_.size();++i) {
            auto& r=ranks_[i];const auto& s=samples[i];
            // Fault first, including same-edge DONE and packed sticky sources.
            r.sticky_fault|=s.fault|s.sticky_sources|static_cast<uint32_t>(s.state>>32);
            if(!r.done && operation_bound_ && cycle-start_>*operation_bound_) r.deadline_failed=true;
            if(s.done) r.done=true;
            if(!r.seen||s.pc!=r.pc) {r.pc=s.pc;r.last_pc=cycle;r.seen=true;r.diagnostic_reported=false;}
            if(!r.done && cycle-r.last_pc>diag_ && !r.diagnostic_reported) {
                v.pc_silent.push_back(i);r.diagnostic_reported=true;
            }
            v.fault|=r.sticky_fault!=0;v.deadline|=r.deadline_failed;
        }
        v.all_done=true;for(const auto& r:ranks_)v.all_done&=r.done;
        // MAXC is an execution ceiling, not a service/liveness proof. Exactly
        // maxc may complete; an unfinished or late completion is sticky failure.
        maxc_failed_|=cycle>maxc_ || (cycle==maxc_&&!v.all_done);
        v.maxc=maxc_failed_;
        v.success=v.all_done&&!v.fault&&!v.deadline&&!v.maxc;
        last_cycle_=cycle;return v;
    }
    const std::vector<Rank>& ranks() const {return ranks_;}
};
} // namespace w17_future
