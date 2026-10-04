#pragma once
#include <memory>
#include "s81_source_caller_plan.hpp"
#include "s81_wavefront_c8_group_step.hpp"
#include "s81_wavefront_c8_port_join.hpp"
#include "s81_wavefront_result_ledger.hpp"

// Actual source-plan executor around ONE caller-owned clock edge. A caller
// must supply the complete stage node order, including nonfield operators.
// FIELD+END/component manifests cannot replace that complete source order.
class DsromS81WaveStagePoller {
public:
    using NodeOrder=std::vector<std::array<std::string,4>>;
    using Visibility=std::function<bool(const DsromC8SourceOffer&)>;
    using ReadResult=std::function<std::optional<DsromS81WaveStageResult>(const DsromC8SourceOffer&)>;
private:
    DsromS81Runtime& runtime;
    DsromS81WaveResultLedger& ledger;
    DsromS81SourcePlan plan;
    Visibility kv_visible,index_visible,remote_visible,allcopy_visible;
    ReadResult read_result;
    std::vector<std::unique_ptr<DsromS81SourceCallerHooks>> carry;
    std::array<bool,4> retired{};
    std::array<size_t,4> prime_index{};
    std::array<bool,4> prime_take{};
    std::unique_ptr<DsromS81C8GroupStep> group_step;
    size_t group=0;
    enum State {CAPTURE,PRIME,DISPATCH,FENCES,HELD,ACCEPTED} state=CAPTURE;
    bool stopped=false,edge_pending=false;
    bool restore_sample=false,restore_recorded=false;
    uint64_t request_sequence;
    std::optional<DsromS81WaveStageResult> held;
    static void require(bool b,const char* why){if(!b)throw std::runtime_error(why);}
    // Guard every explicitly retained producer clock too. A restore/carry
    // callback must return pending, never recursively advance these runtimes.
    struct NoNestedTick {
        std::vector<std::pair<DsromS81Runtime*,std::function<void()>>> clocks;
        explicit NoNestedTick(DsromS81Runtime& target,const DsromS81SourcePlan& p) {
            std::vector<DsromS81Runtime*> owners{&target};
            for(const auto& g:p.groups)for(const auto& r:g.ranks)for(const auto& s:r.saved)
                if(s.producer&&std::find(owners.begin(),owners.end(),s.producer)==owners.end())owners.push_back(s.producer);
            for(auto* owner:owners)clocks.push_back({owner,owner->tick});
            for(auto& c:clocks)c.first->tick=[](){throw std::runtime_error("nested stage/provider tick forbidden");};
        }
        ~NoNestedTick(){for(auto& c:clocks)c.first->tick=std::move(c.second);}
    };
    void begin_group() {
        carry.clear();retired.fill(false);group_step.reset();
        auto& g=plan.groups.at(group);
        for(auto& r:g.ranks) {
            if(r.saved.empty())carry.emplace_back();
            else carry.emplace_back(new DsromS81SourceCallerHooks(runtime,r.offer,r.saved,
                r.retained_source_span,r.input_visible,r.remote_drained,r.all_copies_drained));
        }
    }
    bool restore(const DsromC8SourceOffer& o) {
        auto& r=plan.groups[group].ranks[o.die_id%4];
        if(r.restore_inputs&&!r.restore_inputs(o))return false;
        if(carry[o.die_id%4]&&!carry[o.die_id%4]->restore(o))return false;
        const bool visible=r.input_visible(o);
        if(group==0&&o.die_id%4==0&&visible)restore_sample=true;
        return visible;
    }
    bool drain(const DsromC8SourceOffer& o) {
        const unsigned rank=o.die_id%4;
        if(carry[rank])return carry[rank]->drain(o);
        auto& die=*runtime.dies.at(rank);uint64_t identity=0;
        if(die.c8_retired(identity)) {
            require(identity==o.identity,"foreign stage C8 retirement");retired[rank]=true;
        }
        auto& r=plan.groups[group].ranks[rank];
        return retired[rank]&&die.capture_visible(o.identity)&&r.remote_drained(o)&&r.all_copies_drained(o);
    }
public:
    DsromS81WaveStagePoller(DsromS81Runtime& native,DsromS81WaveResultLedger& accepted_ledger,DsromS81SourcePlan source,
        const NodeOrder& complete_source_stage_nodes,uint64_t sequence,
        Visibility kv,Visibility index,Visibility remote,Visibility allcopy,ReadResult output):
        runtime(native),ledger(accepted_ledger),plan(std::move(source)),kv_visible(std::move(kv)),index_visible(std::move(index)),
        remote_visible(std::move(remote)),allcopy_visible(std::move(allcopy)),read_result(std::move(output)),
        request_sequence(sequence) {
        require(!plan.groups.empty()&&complete_source_stage_nodes.size()==plan.groups.size(),
                "complete source stage schedule required; component is not stage authority");
        require(runtime.stage>=0&&runtime.stage<81&&runtime.dies.size()==4&&runtime.tick&&
                kv_visible&&index_visible&&remote_visible&&allcopy_visible&&read_result,
                "native stage/result visibility providers required");
        for(size_t i=0;i<plan.groups.size();i++)for(unsigned r=0;r<4;r++) {
            const auto& rank=plan.groups[i].ranks[r];const auto& o=rank.offer;
            DsromC8SourceDispatch checked(o);
            require(runtime.dies[r]&&o.die_id==4*runtime.stage+int(r)&&
                    o.identity==plan.groups[i].ranks[0].offer.identity&&
                    o.token==plan.groups[i].ranks[0].offer.token&&
                    o.identity==plan.groups[0].ranks[0].offer.identity&&
                    o.user==plan.groups[0].ranks[0].offer.user&&
                    o.position==plan.groups[0].ranks[0].offer.position,
                    "full-stage TP4 source owner/order mismatch");
            require(!rank.source_node.empty()&&rank.source_node==complete_source_stage_nodes[i][r],
                    "missing/reordered source stage node");
            require(rank.input_visible&&rank.remote_drained&&rank.all_copies_drained&&
                    (!rank.saved.empty()||rank.restore_inputs)&&
                    (rank.saved.empty()||rank.retained_source_span),"source stage input/receipt authority missing");
        }
        begin_group();
    }
    // Returns whether after_edge must be called for the enclosing shared edge.
    bool before_edge() {
        require(!stopped&&!edge_pending,"stage poll edge reused/quarantined");
        try {
            NoNestedTick clock_guard(runtime,plan);
            restore_sample=false;
            for(auto* die:runtime.dies)require(!die->fault(),"native full-stage fault");
            if(state==CAPTURE) {
                bool captured=true;for(auto& c:carry)if(c)captured=c->capture_sources()&&captured;
                if(!captured)return false;
                for(auto& r:plan.groups[group].ranks)if(r.begin)r.begin(r.offer);
                state=PRIME;
            }
            if(state==PRIME) {
                bool pending=false;
                for(unsigned r=0;r<4;r++) {
                    auto& die=*runtime.dies[r];const bool valid=prime_index[r]<die.primes.size();
                    pending|=valid;die.prime(valid,valid?die.primes[prime_index[r]]:0);
                    prime_take[r]=valid&&die.prime_ready();
                }
                if(pending){edge_pending=true;return true;}
                std::array<DsromC8SourceOffer,4> offers;
                for(unsigned r=0;r<4;r++)offers[r]=plan.groups[group].ranks[r].offer;
                group_step.reset(new DsromS81C8GroupStep(offers,[this](const auto& o){
                    if(group==0&&o.die_id%4==0)ledger.accepted(o,request_sequence);
                }));state=DISPATCH;
            }
            if(state==DISPATCH) {
                auto restore_fn=[this](const auto& o){return restore(o);};
                auto drain_fn=[this](const auto& o){return drain(o);};
                if(group_step->before_edge(runtime,restore_fn,drain_fn)){edge_pending=true;return true;}
                if(++group<plan.groups.size()){state=CAPTURE;begin_group();return false;}
                state=FENCES;
            }
            if(state==FENCES) {
                // Explicit terminal producer identities; links_empty/local
                // quiet cannot substitute for these four independent fences.
                for(const auto& g:plan.groups)for(const auto& r:g.ranks)
                    if(!kv_visible(r.offer)||!index_visible(r.offer)||!remote_visible(r.offer)||!allcopy_visible(r.offer))return false;
                held=read_result(plan.groups.back().ranks[0].offer);
                if(!held)return false;
                require(held->request_sequence==request_sequence&&
                        held->identity==plan.groups.back().ranks[0].offer.identity&&held->next_token<(1u<<21),
                        "native full-stage result ownership mismatch");
                state=HELD;
            }
            return false;
        }catch(...){stopped=true;throw;}
    }
    void after_edge() {
        require(!stopped&&edge_pending,"stage acceptance has no sampled shared edge");
        if(state==PRIME){for(unsigned r=0;r<4;r++)if(prime_take[r])prime_index[r]++;}
        else {require(state==DISPATCH,"stage edge state");group_step->after_edge();}
        if(restore_sample&&!restore_recorded) {
            ledger.restored(plan.groups[0].ranks[0].offer.identity,request_sequence);
            restore_recorded=true;
        }
        edge_pending=false;
    }
    std::optional<DsromS81WaveStageResult> result()const{return stopped?std::nullopt:held;}
    void accepted(const DsromS81WaveStageResult& value) {
        require(!stopped&&state==HELD&&held&&value.request_sequence==held->request_sequence&&
                value.identity==held->identity&&value.next_token==held->next_token&&
                value.next_value==held->next_value,"foreign or premature WAVE stage acceptance");
        held.reset();state=ACCEPTED;
    }
    void warm_quarantine(){stopped=true;ledger.warm_quarantine();}
    bool fault()const{return stopped;}
};
