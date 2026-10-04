#pragma once
#include <array>
#include <cstdint>
#include <optional>

namespace dsrom_s81_minimum {
// Passive shared-edge observations. No rate/clock inference and no controller
// state/credits. Bytes here are actual sector transfers, not semantic FP bytes.
struct HbmObservedTransfers {
    uint64_t beats=0,bytes=0;
    std::optional<long> first_cycle,last_cycle;
    void add(long cycle,uint64_t n,uint64_t b) {
        if(!n)return;
        beats+=n;bytes+=b;if(!first_cycle)first_cycle=cycle;last_cycle=cycle;
    }
};
struct HbmOwnerTraffic {
    uint64_t accepted_read_requests=0;
    HbmObservedTransfers accepted_read,delivered_read,accepted_write;
    // Masked writes still carry a 32-byte sector on the physical port.
    uint64_t accepted_write_carrier_bytes=0;
};
struct HbmStackTraffic {
    HbmOwnerTraffic total;
    // Native C8 master-tag [15:14]: WINDOW=0, CKV=1, RoPE=2, invalid=3.
    std::array<HbmOwnerTraffic,4> owner{};
    uint64_t observed_write_done=0;
    std::optional<long> first_write_done_cycle,last_write_done_cycle;
};
struct NativeHbmTrafficSnapshot {
    std::array<HbmStackTraffic,4> stack{};
    std::optional<long> first_observed_cycle,last_observed_cycle;
    // B/indexer inputs are tied inactive in DsromS81Hbm. This is NOT a
    // measured zero-traffic index implementation or an index bandwidth result.
    bool index_b_active=false;
};
class NativeHbmTrafficCounters {
    NativeHbmTrafficSnapshot stats;
    static unsigned enabled_bytes(uint32_t mask) {
        unsigned n=0;while(mask){mask&=mask-1;++n;}return n;
    }
public:
    void sample(long cycle,uint8_t accepted,uint8_t returned,uint8_t committed,
        uint8_t write_mask,const std::array<unsigned,4>& lengths,
        const std::array<unsigned,4>& request_owner,
        const std::array<unsigned,4>& response_owner,
        const std::array<uint32_t,4>& strobes) {
        if(!stats.first_observed_cycle)stats.first_observed_cycle=cycle;
        stats.last_observed_cycle=cycle;
        for(unsigned s=0;s<4;s++) {
            auto& st=stats.stack[s];unsigned bit=1u<<s;
            if(accepted&bit) {
                auto add=[&](HbmOwnerTraffic& t) {
                    if(write_mask&bit) {
                        t.accepted_write.add(cycle,1,enabled_bytes(strobes[s]));
                        t.accepted_write_carrier_bytes+=32;
                    } else {
                        ++t.accepted_read_requests;
                        t.accepted_read.add(cycle,lengths[s],32ull*lengths[s]);
                    }
                };
                add(st.total);add(st.owner[request_owner[s]&3]);
            }
            if(returned&bit) {
                st.total.delivered_read.add(cycle,1,32);
                st.owner[response_owner[s]&3].delivered_read.add(cycle,1,32);
            }
            if(committed&bit) {
                ++st.observed_write_done;
                if(!st.first_write_done_cycle)st.first_write_done_cycle=cycle;
                st.last_write_done_cycle=cycle;
            }
        }
    }
    NativeHbmTrafficSnapshot snapshot()const{return stats;}
};
} // namespace dsrom_s81_minimum
