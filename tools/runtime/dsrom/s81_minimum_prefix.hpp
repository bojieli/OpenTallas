#pragma once
#include "s81_minimum_embedding.hpp"
#include <array>
#include <stdexcept>
#include <utility>

// Port orchestration only. Arithmetic, reads, writes and ACKs belong to actual
// native SU/HE and target-VM participants supplied by the caller. This header
// does not supply those missing models or compute an activation in software.
struct DsromS81PrefixOperation {
    unsigned index=0, unit=0;
    const char* template_sha256=nullptr;
    std::array<uint32_t,64> instruction{}; // literal full-shape 2048-bit ISA
};
const std::array<DsromS81PrefixOperation,7>& dsrom_s81_l0_prefix_operations();

struct DsromS81PrefixNativeEngine {
    DsromS81MinimumParticipant participant;
    std::function<bool()> ready,idle;
    // Poll/admit this operation's real native operand prefetch. Returns true
    // only with the required source leases and fixed-latency endpoint ready.
    // Progress uses participant edges; this callback never clocks a model.
    std::function<bool(const DsromS81PrefixOperation&)> inputs_ready;
    // Drives literal decoded ports plus GO. Does not eval/clock a model.
    std::function<void(const DsromS81PrefixOperation&,bool go)> drive;
};
struct DsromS81PrefixVm {
    // Version transition on this instruction's real pre-edge GO acceptance,
    // after operand prefetch and before native leaf rising evaluation.
    std::function<void(uint64_t,unsigned)> instruction_accepted;
    // Same actual target as EmbeddingMacroSink: matched H publication plus
    // native cold producers for SSX[40960] and identity PF[41152..41155].
    // SSX must come from a native golden-order reducer, never host arithmetic.
    std::function<bool(uint64_t)> cold_inputs_visible;
    // Full native output extent and all matching receipts, not engine idle.
    std::function<bool(uint64_t,unsigned instruction)> outputs_visible;
    std::function<bool()> fault;
    // Polls the native target read-span participant. Address fixed to XN,
    // length 16; no embedding-local probe or host activation image accepted.
    std::function<std::optional<std::array<uint32_t,16>>(
        uint64_t,uint32_t)> xn_span;
};

class DsromS81MinimumPrefix {
    DsromS81MinimumRuntime& runtime;
    DsromS81MinimumEmbedding& embedding;
    DsromS81PrefixNativeEngine su,he;
    DsromS81PrefixVm vm;
    uint64_t identity;
    unsigned next=0;
    bool reset_seen=false,started=false,inflight=false,go=false,stopped=false;
    static void require(bool ok,const char* why) {
        if(!ok)throw std::runtime_error(why);
    }
    static bool valid(const DsromS81PrefixNativeEngine& e) {
        return !e.participant.name.empty()&&e.participant.prepare&&
            e.participant.rising&&e.participant.falling&&e.participant.fault&&
            e.ready&&e.idle&&e.inputs_ready&&e.drive;
    }
    DsromS81PrefixNativeEngine& engine() {
        return dsrom_s81_l0_prefix_operations()[next].unit==5?he:su;
    }
    void prepare(const DsromS81PairResult& result) {
        try {
            require(!fault(),"native prefix quarantined; source/publication debt retained");
            go=false;
            // Withdraw both old GO pins before selecting this edge's engine,
            // including the SU->HE boundary and the final XN drain edge.
            su.drive(dsrom_s81_l0_prefix_operations()[0],false);
            he.drive(dsrom_s81_l0_prefix_operations()[1],false);
            if(started&&next<7) {
                require(runtime.identity&&*runtime.identity==identity,
                        "native prefix lost admitted context");
                if(inflight&&engine().idle()&&vm.outputs_visible(identity,next)) {
                    inflight=false;++next;
                }
                if(next<7) {
                    auto& e=engine();
                    go=!inflight&&embedding.complete()&&
                        vm.cold_inputs_visible(identity)&&
                        e.inputs_ready(dsrom_s81_l0_prefix_operations()[next])&&
                        e.ready()&&e.idle();
                    e.drive(dsrom_s81_l0_prefix_operations()[next],go);
                }
            }
            su.participant.prepare(result);he.participant.prepare(result);
        }catch(...){stopped=true;throw;}
    }
    void rising(bool released) {
        try {
            if(!released) {
                require(!started&&!inflight&&!go,
                        "prefix reset would erase admitted native debt");
                reset_seen=true;
            } else if(go) {
                require(reset_seen&&!inflight&&next<7&&engine().ready(),
                        "prefix GO lacks native pre-edge acceptance");
                vm.instruction_accepted(identity,next);
                inflight=true;
            }
            su.participant.rising(released);he.participant.rising(released);
        }catch(...){stopped=true;throw;}
    }
public:
    DsromS81MinimumPrefix(DsromS81MinimumRuntime& r,DsromS81MinimumEmbedding& e,
                         uint64_t id,DsromS81PrefixNativeEngine s,
                         DsromS81PrefixNativeEngine h,DsromS81PrefixVm v)
    :runtime(r),embedding(e),su(std::move(s)),he(std::move(h)),vm(std::move(v)),identity(id) {
        require(r.stage==0&&id<(1ull<<47)&&valid(su)&&valid(he)&&
                vm.instruction_accepted&&vm.cold_inputs_visible&&
                vm.outputs_visible&&vm.fault&&vm.xn_span,
                "actual native SU/HE, cold reducers and same-VM publication/read participants required");
        require(su.participant.name!=he.participant.name,
                "prefix SU and HE must name distinct actual participants");
        for(const auto& p:r.participants)
            require(p.name!=su.participant.name&&p.name!=he.participant.name,
                    "native prefix leaf already registered; duplicate clock forbidden");
        // This participant owns these two leaf callbacks. Do not also register
        // them separately: the host supplies exactly one shared edge each.
        r.participants.push_back({"native-L0-I0-I6-prefix",
            [this](const auto& p){prepare(p);},
            [this](bool reset){rising(reset);},
            [this](bool reset){
                try{su.participant.falling(reset);he.participant.falling(reset);}
                catch(...){stopped=true;throw;}
            },[this](){return fault();}});
    }
    DsromS81MinimumPrefix(const DsromS81MinimumPrefix&)=delete;
    DsromS81MinimumPrefix& operator=(const DsromS81MinimumPrefix&)=delete;
    void start() {
        require(!started&&reset_seen&&!fault()&&runtime.identity&&
                *runtime.identity==identity,"prefix start lacks shared reset/context");
        started=true;
    }
    bool fault() const {
        return stopped||su.participant.fault()||he.participant.fault()||vm.fault();
    }
    bool complete() const {return started&&next==7&&!inflight&&!fault();}
    unsigned next_instruction() const {return next;}
    std::optional<std::array<uint32_t,16>> xn_span(uint32_t address) {
        require(complete()&&address>=46464&&address+16<=51584&&!(address&15),
                "L0.I7 read lacks full native XN publication or aligned extent");
        return vm.xn_span(identity,address);
    }
};
