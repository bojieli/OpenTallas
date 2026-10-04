#pragma once
#include "s81_wavefront_stage_poller.hpp"
#include "s81_wavefront_native_result_read.hpp"

// One enclosing caller edge for both native terminal observation and the
// source-stage executor. Observation MUST continue on edges where the poller
// has no admission work (waiting for terminal END, retirement or fences).
// No eval/tick/reset is owned here.
template<class Reader,class Stage=DsromS81WaveStagePoller> class DsromS81WaveNativeStageJoin {
    std::shared_ptr<Reader> reader;
    std::unique_ptr<Stage> stage;
    bool prepared=false, stage_pending=false, stopped=false;
public:
    DsromS81WaveNativeStageJoin(std::shared_ptr<Reader> native_reader,
                               std::unique_ptr<Stage> executor):
        reader(std::move(native_reader)),stage(std::move(executor)) {
        if(!reader||!stage)throw std::runtime_error("native reader and source-stage executor required");
    }
    void before_edge() {
        if(stopped||prepared)throw std::runtime_error("native stage shared edge reused/quarantined");
        try {
            stage_pending=stage->before_edge();
            reader->sample_before_edge();
            prepared=true;
        }catch(...){warm_quarantine();throw;}
    }
    void after_edge() {
        if(stopped||!prepared)throw std::runtime_error("native stage missing preedge sample");
        try {
            reader->after_edge();
            if(stage_pending)stage->after_edge();
            prepared=false;
        }catch(...){warm_quarantine();throw;}
    }
    auto result()const{return stage->result();}
    void accepted(const DsromS81WaveStageResult& value){stage->accepted(value);}
    void warm_quarantine(){stopped=true;reader->warm_quarantine();stage->warm_quarantine();}
    bool fault()const{return stopped||reader->fault()||stage->fault();}
};

// Bind the actual terminal die BEFORE its type is erased to DieBase, and
// verify the reader's terminal against the complete source plan. The factory
// supplies ReadResult itself; a permissive fallback cannot replace it.
template<class NativeDie>
auto dsrom_s81_bind_native_stage_join(
    NativeDie& terminal_die,DsromS81NativeResultTerminal terminal,
    DsromS81Runtime& runtime,DsromS81WaveResultLedger& ledger,
    DsromS81SourcePlan plan,const DsromS81WaveStagePoller::NodeOrder& nodes,
    uint64_t sequence,DsromS81WaveStagePoller::Visibility kv,
    DsromS81WaveStagePoller::Visibility index,DsromS81WaveStagePoller::Visibility remote,
    DsromS81WaveStagePoller::Visibility allcopy,bool enable=false) {
    if(plan.groups.empty())throw std::runtime_error("complete terminal source plan required");
    const auto& last=plan.groups.back().ranks[0];
    const auto& a=last.offer;const auto& b=terminal.offer;
    if(last.source_node!=terminal.source_node||a.die_id!=b.die_id||a.identity!=b.identity||
       a.token!=b.token||a.position!=b.position||a.user!=b.user||a.epoch!=b.epoch||a.entry!=b.entry)
        throw std::runtime_error("native terminal differs from actual last source node/offer");
    if(runtime.dies.size()!=4||runtime.dies[0]!=&terminal_die)
        throw std::runtime_error("native terminal die is not selected rank-zero provider");
    auto reader=dsrom_s81_bind_native_result_read(terminal_die,std::move(terminal),sequence,enable);
    using Reader=typename decltype(reader)::element_type;
    auto executor=std::make_unique<DsromS81WaveStagePoller>(runtime,ledger,std::move(plan),nodes,sequence,
        std::move(kv),std::move(index),std::move(remote),std::move(allcopy),
        dsrom_s81_native_read_result_callback(reader));
    return std::make_unique<DsromS81WaveNativeStageJoin<Reader>>(std::move(reader),std::move(executor));
}
