#pragma once
// Caller-only enrollment. No clocks, publication authority or guessed EIDs.
#include "s81_minimum_source_bindings.hpp"
#include "s81_qe_checkpoint_word_reader.hpp"
#include <memory>
#include <string>
#include <vector>

struct DsromS81DelayedEidEnrollment {
    std::string node,source_node_sha256;
    unsigned rank=0,fragment=0;
    uint64_t identity=0;
    unsigned capture_producer=0;
    uint32_t capture_vm_base=0;
};

class DsromS81DelayedEidSessions {
public:
    static constexpr uint32_t I93_EID_BASE=366688; // SELECT src366304/n384/k6, wait2.
    using Eids=std::array<unsigned,6>;
    using RawCapture=std::array<uint32_t,6>;
    // Must call the actual rank's matching native-output publisher, not a
    // helper-owned flag, callback invocation count or software offer receipt.
    using CapturePublished=std::function<bool(unsigned,uint64_t,unsigned)>;
private:
    struct Session {
        DsromS81DelayedEidEnrollment source;
        std::shared_ptr<DsromS81QeCheckpointWordReader> reader;
        Eids eids{};
        RawCapture raw{};
        unsigned read_index=0;
        bool captured=false,bound=false;
    };
    std::vector<Session> sessions_;
    std::array<DsromS81MinimumSourceIo,4> io_;
    CapturePublished published_;
    bool stopped_=false;
    static void require(bool ok,const char* message) {
        if(!ok)throw std::runtime_error(message);
    }
    Session& find(const std::string& node,unsigned rank,unsigned fragment) {
        for(auto& s:sessions_)if(s.source.node==node&&s.source.rank==rank&&s.source.fragment==fragment)return s;
        throw std::runtime_error("dynamic source session not enrolled");
    }
    bool capture_visible(const Session& s)const {
        const auto& e=s.source;
        return published_(e.rank,e.identity,e.capture_producer)&&
               io_[e.rank].span_lease(e.identity,e.capture_vm_base,6);
    }
public:
    // Construct ONCE before native-model worker threads. Every enrollment must
    // come from the actual source catalogue/accepted program, never a default
    // expert. Constructor blocks for each fixed child's checkpoint/source READY.
    DsromS81DelayedEidSessions(const std::string& python,const std::string& script,
        const std::string& owner,const std::string& checkpoint,
        const std::vector<DsromS81DelayedEidEnrollment>& actual_nodes,
        std::array<DsromS81MinimumSourceIo,4> actual_io,CapturePublished published)
        :io_(std::move(actual_io)),published_(std::move(published)) {
        require(bool(published_),"actual captured-publication callback required");
        require(!actual_nodes.empty(),"no actual dynamic nodes enrolled");
        for(const auto& e:actual_nodes) {
            require(e.rank<4&&e.identity<(1ull<<47)&&e.capture_producer<(1u<<14)&&
                    e.capture_vm_base==I93_EID_BASE&&!e.node.empty()&&e.source_node_sha256.size()==64,
                    "invalid actual dynamic source enrollment");
            require(bool(io_[e.rank].read_word)&&bool(io_[e.rank].span_lease),"actual rank SourceIo required");
            for(const auto& s:sessions_)require(s.source.node!=e.node||s.source.rank!=e.rank||
                                               s.source.fragment!=e.fragment,"duplicate dynamic source session");
            Session s;s.source=e;
            s.reader=std::make_shared<DsromS81QeCheckpointWordReader>(python,script,owner,checkpoint,
                         e.node,e.rank,e.fragment,std::vector<unsigned>{},true);
            sessions_.push_back(std::move(s));
        }
    }
    DsromS81DelayedEidSessions(const DsromS81DelayedEidSessions&)=delete;
    // Invoke from the actual producer's captured-output callback. IDs and raw
    // VM payload MUST refer to the SAME accepted I93 result. The source XU
    // writes {16'd0,so_idx} at dst+nw: six RAW unsigned IDs at366688, never FP32
    // indices. This helper performs no decode, sort or selection. Held identical callback
    // repetition changes nothing; a changed capture quarantines the sessions.
    void captured(unsigned rank,uint64_t identity,unsigned producer,uint32_t vm_base,
                  const Eids& native_eids,const RawCapture& actual_stored_bits) {
        try {
            require(!stopped_,"dynamic sessions quarantined");
            for(unsigned i=0;i<6;++i)require(native_eids[i]<384&&(!i||native_eids[i]>native_eids[i-1]),
                                             "six actual ascending native EIDs required");
            require(vm_base==I93_EID_BASE,"EID capture is not actual I93 destination");
            for(unsigned i=0;i<6;++i)require(actual_stored_bits[i]==native_eids[i],
                                             "I93 stored bits differ from captured raw native ID");
            bool matched=false;
            for(auto& s:sessions_) {
                const auto& e=s.source;
                if(e.rank!=rank||e.identity!=identity||e.capture_producer!=producer||e.capture_vm_base!=vm_base)continue;
                matched=true;
                if(s.captured)require(s.eids==native_eids&&s.raw==actual_stored_bits,"changed held native EID capture");
                else {s.eids=native_eids;s.raw=actual_stored_bits;s.captured=true;}
            }
            require(matched,"native EID capture has no matching source session");
        } catch(...) {stopped_=true;throw;}
    }
    // Connect ONLY to the accepted native I93 SELECT output/capture callback,
    // using the same context and mapped producer as its matching publisher.
    // Capture observation alone is not binding: advance waits for publication
    // and all six actual SourceIo reads at the precise destination.
    void captured_i93(unsigned rank,uint64_t identity,unsigned actual_producer,const Eids& native_eids) {
        RawCapture raw{};
        for(unsigned i=0;i<6;++i)raw[i]=native_eids[i];
        captured(rank,identity,actual_producer,I93_EID_BASE,native_eids,raw);
    }
    // Poll from the caller's existing participant edges/inputs_ready path.
    // Actual reads advance only via SourceIo's native participant; no private
    // eval/tick or synthetic ready. Bind only after matched publication AND
    // exact raw capture readback under the actual six-word lease.
    bool advance_captured_bindings() {
        try {
            require(!stopped_,"dynamic sessions quarantined");
            bool all=true;
            std::array<bool,4> rank_read_pending{};
            for(auto& s:sessions_) {
                if(s.bound)continue;
                if(rank_read_pending[s.source.rank]){all=false;continue;}
                if(!s.captured||!capture_visible(s)){all=false;continue;}
                const auto& e=s.source;
                while(s.read_index<6) {
                    auto bits=io_[e.rank].read_word(e.identity,e.capture_vm_base+s.read_index);
                    if(!bits) {
                        // Shared SourceIo retains this address until it replies.
                        // No later session on this rank may change that held
                        // request during this poll; other ranks can progress.
                        rank_read_pending[e.rank]=true;
                        break;
                    }
                    require(*bits==s.raw[s.read_index],"native EID capture/publication readback mismatch");
                    ++s.read_index;
                }
                if(s.read_index<6){all=false;continue;}
                require(capture_visible(s),"native EID source lease lost before binding");
                s.reader->bind_captured_eids(std::vector<unsigned>(s.eids.begin(),s.eids.end()),
                                             e.source_node_sha256,e.rank,e.fragment);
                s.bound=true;
            }
            return all;
        } catch(...) {stopped_=true;throw;}
    }
    bool bound(const std::string& node,unsigned rank,unsigned fragment=0) {
        auto& s=find(node,rank,fragment);
        return !stopped_&&s.bound&&capture_visible(s);
    }
    // Keep this session owner alive through the native operator's full drain.
    // Read closure does NOT own the session manager; factory must retain it.
    std::function<std::array<uint32_t,9>(int,int,int,int)>
    word_reader(const std::string& node,unsigned rank,unsigned fragment=0) {
        auto& s=find(node,rank,fragment);
        const auto index=size_t(&s-sessions_.data());
        return [this,index](int stage,int r,int macro,int row) {
            auto& held=sessions_.at(index);
            require(!stopped_&&held.bound&&capture_visible(held),"dynamic read before capture/lease or after quarantine");
            return held.reader->read(stage,r,macro,row);
        };
    }
    bool fault()const{return stopped_;}
};
