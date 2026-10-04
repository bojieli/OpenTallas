#include "s81_wavefront_native_stage_join.hpp"
#include <cassert>
struct Ports {
    bool rst_n=true,native_result_selected=true,native_result_active=true;
    bool native_result_producer_take=false,native_result_am_any=false;
    bool native_result_end_take=false,native_result_done=false,c8_retire_v=false;
    uint32_t native_result_entry=4,native_result_pc=4,native_result_token=0,native_result_value=0;
    uint64_t native_result_identity=0,c8_retire_identity=0;
    uint32_t fault=0,c8_stage_quarantine=0,c8_write_quarantine=0,c8_write_fault=0;
};

struct NativeDie : DieBase {std::unique_ptr<Ports> d=std::make_unique<Ports>();};

// Instantiates the actual factory with the native DieBase/provider type; no model build.
auto compile_actual_factory(NativeDie& die, DsromS81Runtime& runtime,
    DsromS81WaveResultLedger& ledger, DsromS81SourcePlan plan,
    const DsromS81WaveStagePoller::NodeOrder& order, DsromS81NativeResultTerminal terminal,
    DsromS81WaveStagePoller::Visibility fence) {
    return dsrom_s81_bind_native_stage_join(die,std::move(terminal),runtime,ledger,
        std::move(plan),order,17,fence,fence,fence,fence,false);
}
struct Reader {
    int pre=0,post=0;bool stopped=false;
    void sample_before_edge(){++pre;}
    void after_edge(){++post;}
    void warm_quarantine(){stopped=true;}
    bool fault()const{return stopped;}
};
struct Stage {
    bool pending=false,stopped=false;int pre=0,post=0;
    bool before_edge(){++pre;return pending;}
    void after_edge(){++post;}
    std::optional<DsromS81WaveStageResult> result()const{return std::nullopt;}
    void accepted(const DsromS81WaveStageResult&){}
    void warm_quarantine(){stopped=true;}
    bool fault()const{return stopped;}
};
int main(){
    auto r=std::make_shared<Reader>();auto s=std::make_unique<Stage>();auto* observed=s.get();
    DsromS81WaveNativeStageJoin<Reader,Stage> join(r,std::move(s));
    // Waiting stage still observes every real edge; no unpaired poller after_edge.
    join.before_edge();join.after_edge();assert(r->pre==1&&r->post==1&&observed->post==0);
    observed->pending=true;join.before_edge();join.after_edge();assert(observed->post==1&&r->post==2);
    join.warm_quarantine();assert(join.fault()&&r->stopped&&observed->stopped);
    bool refused=false;try{join.before_edge();}catch(const std::runtime_error&){refused=true;}assert(refused);
}
