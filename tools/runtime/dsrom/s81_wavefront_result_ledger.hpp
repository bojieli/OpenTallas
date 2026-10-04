#pragma once
#include <algorithm>
#include <vector>
#include "s81_wavefront_c8_port_join.hpp"

// Caller-owned accepted-context ledger, not physical queue/credit storage.
// Untagged native RESULT user/position must resolve to ONE retained source
// generation in its actual accepted issue order. No constructor/admission
// attempt, local FIFO empty, or rejected-token pulse records completion.
class DsromS81WaveResultLedger {
    struct Entry {
        DsromC8SourceOffer offer;
        uint64_t sequence,order;
        bool restored=false,result=false,cancel=false,fabric=false,allcopy=false;
    };
    std::vector<Entry> entries;
    size_t capacity;
    uint64_t next_order=0;
    bool quarantine=false;
    Entry& match(uint64_t identity,uint64_t sequence) {
        Entry* found=nullptr;
        for(auto& e:entries)if(e.offer.identity==identity&&e.sequence==sequence) {
            if(found)throw std::runtime_error("ambiguous source generation ledger");
            found=&e;
        }
        if(!found)throw std::runtime_error("missing/stale accepted source generation");
        return *found;
    }
    static void require(bool b,const char* why){if(!b)throw std::runtime_error(why);}
    void release() {
        entries.erase(std::remove_if(entries.begin(),entries.end(),[](const Entry& e){
            return e.restored&&(e.result||e.cancel)&&e.fabric&&e.allcopy;
        }),entries.end());
    }
public:
    explicit DsromS81WaveResultLedger(size_t source_live_bound):capacity(source_live_bound) {
        require(capacity>0,"explicit selected source live-context bound required");
    }
    // Call ONLY after actual C8 offer acceptance; first fragment/rank0 once
    // per WAVE request. Restoration is an additional actual sampled event.
    void accepted(const DsromC8SourceOffer& offer,uint64_t sequence) {
        require(!quarantine,"new accepted context under warm quarantine");
        DsromC8SourceDispatch checked(offer);
        require(entries.size()<capacity,"accepted RESULT ledger source bound exceeded");
        for(const auto& e:entries)require(e.sequence!=sequence&&e.offer.identity!=offer.identity,
            "duplicate accepted request/source generation still retained");
        entries.push_back({offer,sequence,next_order++});
    }
    void restored(uint64_t identity,uint64_t sequence) {
        auto& e=match(identity,sequence);require(!e.restored,"duplicate restored source event");e.restored=true;
    }
    DsromS81WaveResultOrigin lookup(uint32_t user,uint32_t position) const {
        require(user<(1u<<10)&&position<(1u<<21),"native RESULT owner bounds");
        const Entry* candidate=nullptr;const Entry* head=nullptr;
        unsigned matches=0;
        for(const auto& e:entries) {
            if(e.offer.user==user&&!e.result&&(!head||e.order<head->order))head=&e;
            // Keep already consumed but not fully fenced generations in the
            // ambiguity check: they can still own stale fabric copies.
            if(e.offer.user==user&&e.offer.position==position){candidate=&e;matches++;}
        }
        require(matches==1&&candidate,"missing/ambiguous native RESULT generation");
        require(candidate->restored&&!candidate->result&&candidate==head,
                "stale/unrestored/out-of-order native RESULT");
        return {candidate->offer.identity,user,position};
    }
    // Direct Boole 51790130c Lookup binding; filters source generation/order
    // BEFORE supplying the native observational provider's candidate vector.
    template<class NativeResultKey>
    std::vector<DsromS81WaveResultOrigin> lookup_candidates(const NativeResultKey& key)const {
        return {lookup(key.user,key.position)};
    }
    void result_received(const DsromS81WaveResultOrigin& owner) {
        const auto expected=lookup(owner.user,owner.position);
        require(owner.identity==expected.identity,"RESULT differs from saved accepted generation");
        for(auto& e:entries)if(e.offer.identity==owner.identity){e.result=true;release();return;}
        throw std::runtime_error("RESULT ledger disappeared");
    }
    // This is an actual counted cancel RECEIPT, not wf_reject/wf_squash.
    void cancel_received(uint64_t identity,uint64_t sequence) {
        auto& e=match(identity,sequence);require(e.restored&&!e.cancel,
            "duplicate/unrestored cancel receipt");e.cancel=true;release();
    }
    void fabric_drained(uint64_t identity,uint64_t sequence) {
        match(identity,sequence).fabric=true;release();
    }
    void all_copies_drained(uint64_t identity,uint64_t sequence) {
        match(identity,sequence).allcopy=true;release();
    }
    void warm_quarantine(){quarantine=true;}
    size_t retained()const{return entries.size();}
};
