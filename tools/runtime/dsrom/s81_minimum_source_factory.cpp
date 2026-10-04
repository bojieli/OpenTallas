#include "s81_minimum_source_plan.hpp"
#include "s81_minimum_source_bindings.hpp"
#include "s81_minimum_input_participant.hpp"
#include "s81_minimum_return_cut_join.hpp"
#include "s81_published_span_accept_sink.hpp"
#include "Vnative_vm.h"
#include "Vretn.h"
#include "Vroot.h"
#include <fstream>
#include <cstdlib>
#include <cstdio>

namespace {
using namespace dsrom_s81_minimum;
constexpr uint64_t ID=uint64_t(1)<<31;
constexpr uint32_t OUTPUT_BASE=419776,OUTPUT_ROWS=320,CUT_ALIAS=32768;
using Target=PublishedSpanAcceptSink<Vnative_vm>;
using Return=NativeReturnParticipant<Vretn,Vroot>;

std::vector<uint64_t> words(const std::string& path) {
    std::ifstream input(path);
    if(!input)throw std::runtime_error("missing literal selected native control: "+path);
    std::vector<uint64_t> out;std::string word;
    while(input>>word) {
        size_t end=0;auto value=std::stoull(word,&end,16);
        if(end!=word.size())throw std::runtime_error("invalid literal native control word");
        out.push_back(value);
    }
    if(!input.eof())throw std::runtime_error("native control read failed");
    return out;
}

struct Source : std::enable_shared_from_this<Source> {
    DsromS81MinimumRuntime& runtime;
    std::shared_ptr<Vnative_vm> vm;
    DsromS81MinimumSourceTags tags;
    PrefixPublication publication{ID};
    std::unique_ptr<Target> target;
    std::unique_ptr<Vcut> cut;
    std::unique_ptr<NativeInputParticipant> input;
    std::unique_ptr<Return> returned;
    std::unique_ptr<MacroAckAdapter<Vnative_vm>> field;
    std::unique_ptr<DsromS81MinimumPrefix> prefix;
    DsromS81MinimumPrefixBinding engines;
    DsromS81MinimumParticipant prefix_bank,field_bank;
    std::array<uint64_t,2> phrom{};
    std::vector<uint64_t> stream;
    std::string cfg;
    bool attached=false,armed=false,field_selected=false;
    bool read_pending=false;
    uint32_t read_address=0;
    std::array<uint32_t,8> read_owner{};

    static void require(bool ok,const char* why) {
        if(!ok)throw std::runtime_error(why);
    }
    Source(DsromS81MinimumRuntime& r,std::shared_ptr<Vnative_vm> v):runtime(r),vm(std::move(v)),
        tags(dsrom_s81_bind_minimum_source_tags(r,ID)) {
        require(r.stage==0&&r.rank==0&&r.pair==0&&r.bf16,
                "selected L0.I7 requires actual stage0/rank0/BF-site pair0");
        require(tags.record&&tags.read_owner&&tags.root_owner&&tags.scalar_accept&&tags.read_accept,
                "actual reserved source tags and backend acceptance hooks required");
        const char* selected=std::getenv("DSROM_S81_MINIMUM_SELECTED_DIR");
        require(selected&&*selected,"literal selected CFG/PHROM/STREAM directory required");
        const std::string dir=selected;cfg=dir+"/e0.cfg.hex";
        auto phases=words(dir+"/spine_phase.hex");stream=words(dir+"/spine_stream.hex");
        require(phases.size()==2&&phases[0]==22517998140008448ull&&phases[1]==0&&stream.size()==192,
                "actual selected L0.I7 PHROM/STREAM binding differs");
        phrom={phases[0],phases[1]};
        target=std::make_unique<Target>(*vm,ID,0,
            [this](const auto& out,unsigned lane) {
                return out.vm_address<20480?tags.record(out,lane):publication.record(out,lane);
            },
            [this](auto id,auto a,auto n){return publication.source_span_lease(id,a,n);},
            [this](auto id,auto a,auto n){return publication.write_allowed(id,a,n);},
            [this](const auto& c,const auto& receipt){publication.on_prefix_scalar_ack(c,receipt);},
            Target::AcceptObservers{true,tags.scalar_accept,tags.read_accept});
        prefix_bank=target->participant();
    }
    DsromS81MinimumSourceIo io() {
        return {
            [this](auto id,auto address){return read(id,address);},
            [this](auto id,auto address,auto count){return target->source_span_lease(id,address,count);},
            [this](const auto& out,unsigned count){return target->offer_prefix(out,count);},
            [this](const auto& out,unsigned count){return target->visible_prefix(out,count);}
        };
    }
    std::optional<uint32_t> read(uint64_t id,uint32_t address) {
        require(id==ID&&!field_selected,"prefix/XN read after field-bank handoff or wrong context");
        // Reserve exactly once for the held request, not once per polling call.
        if(!read_pending) {
            read_owner=tags.read_owner(id,address);read_address=address;read_pending=true;
        }
        require(address==read_address,"changed held source native read address");
        auto bits=target->target_word(address,read_owner);
        if(bits)read_pending=false;
        return bits;
    }
    void attach(DsromS81MinimumEmbedding& embedding) {
        require(!attached,"minimum source attached twice");
        engines=dsrom_s81_bind_minimum_prefix_engines(runtime,ID,publication,io(),tags);
        require(engines.start_bootstrap&&engines.bootstrap.prepare&&engines.bootstrap.rising&&
                engines.bootstrap.falling&&engines.bootstrap.fault,
                "actual native SSX/PF bootstrap participant required");
        runtime.participants.push_back(engines.bootstrap);
        DsromS81PrefixVm hooks;
        hooks.instruction_accepted=[this](auto id,unsigned i){publication.begin(id,i);};
        hooks.cold_inputs_visible=[this](auto id) {
            return publication.complete(PrefixPublication::SSX)&&publication.complete(PrefixPublication::PF)&&
                target->source_span_lease(id,0,20480)&&target->source_span_lease(id,40960,1)&&
                target->source_span_lease(id,41152,4);
        };
        hooks.outputs_visible=[this](auto id,unsigned i){return publication.complete(id,i);};
        hooks.fault=[this](){return publication.fault()||target->fault();};
        // The input sender polls individual actual target words through io().
        // This aligned span interface remains usable by prefix consumers.
        struct Span {bool active=false;uint32_t address=0,n=0;std::array<uint32_t,16> data{};};
        auto span=std::make_shared<Span>();
        hooks.xn_span=[this,span](uint64_t id,uint32_t address)->std::optional<std::array<uint32_t,16>> {
            if(!target->source_span_lease(id,address,16))return std::nullopt;
            if(!span->active){span->active=true;span->address=address;span->n=0;}
            require(span->address==address,"changed outstanding XN span");
            auto bits=read(id,address+span->n);if(!bits)return std::nullopt;
            span->data[span->n++]=*bits;
            if(span->n<16)return std::nullopt;
            span->active=false;return span->data;
        };
        prefix=std::make_unique<DsromS81MinimumPrefix>(runtime,embedding,ID,
            engines.su,engines.he,std::move(hooks));
        cut=std::make_unique<Vcut>(runtime.context,"selected_native_input_cut");
        input=std::make_unique<NativeInputParticipant>(runtime,*cut,
            [this](auto id,auto address){return read(id,address);},
            [this](auto id,auto address,auto count){return target->source_span_lease(id,address,count);});
        returned=std::make_unique<Return>(runtime,[this](const auto& phase,const auto& owner) {
            require(owner.element_address==input->actual_output_address(owner.row,owner.position),
                    "root output canonical19-bit route mismatch");
            return tags.root_owner(phase,owner);
        });
        runtime.participants.push_back(input->participant());
        runtime.participants.push_back(join_return_to_input_cut(input->native_cut(),*returned));
        field=std::make_unique<MacroAckAdapter<Vnative_vm>>(*vm,
            [this](const auto& result){return returned->supply(result);},
            [this](auto bank,const auto& command){returned->accepted(bank,command);tags.scalar_accept(bank,command);},
            [this](auto bank,const auto& command,const auto& receipt){returned->visible(bank,command,receipt);});
        field_bank=field->participant();
        // Select once in prepare; use that SAME participant for this edge's
        // rising/falling. There is exactly one native bank clock owner.
        runtime.participants.push_back({"selected-single-native-bank",
            [this](const auto& result) {
                if(armed&&input->inputs_loaded()) {
                    require(!read_pending&&prefix->complete(),"field handoff before actual XN read drain");
                    field_selected=true;
                }
                (field_selected?field_bank:prefix_bank).prepare(result);
            },
            [this](bool reset){(field_selected?field_bank:prefix_bank).rising(reset);},
            [this](bool reset){(field_selected?field_bank:prefix_bank).falling(reset);},
            [this](){return target->fault()||field->fault();}});
        auto self=shared_from_this();
        runtime.publication_ready=[self](auto id) {
            return id==ID&&self->attached&&!self->publication.fault()&&!self->target->fault()&&
                !self->field->fault()&&!self->returned->fault();
        };
        runtime.publication_drained=[self](auto id){return id==ID&&self->complete();};
        attached=true;
    }
    void begin() {engines.start_bootstrap();prefix->start();}
    void advance() {
        if(!armed&&prefix->complete()) {
            const auto alias=NativeInputParticipant::declare_input_only_alias(ID,0,OUTPUT_BASE,OUTPUT_ROWS,CUT_ALIAS);
            input->arm(ID,0,phrom,stream,OUTPUT_BASE,OUTPUT_ROWS,alias);
            ReturnPhaseBinding bound{};
            bound.stage=0;bound.rank=0;bound.pair=0;bound.root=0;bound.phase=0;
            bound.identity=ID;bound.phrom0=phrom[0];bound.phrom1=phrom[1];
            bound.output_base=input->actual_output_address(0,0);bound.output_position_stride=OUTPUT_ROWS;
            bound.emitted_key="0";bound.cfg_path=cfg;
            bound.source_matrix_sha256="1d3f5077217e5627aa4f6c318bd97d2fa86f622790163d17fa7b7c8c624d7a8f";
            bound.region_pair_begin=0;bound.region_pair_end=18;
            bound.branch_a_leaf=0;bound.branch_b_leaf=1;bound.component_rows={0,1};
            returned->admit(bound);armed=true;
        }
    }
    bool complete() const {
        return attached&&armed&&field_selected&&prefix->complete()&&!read_pending&&
            input->input_finished()&&returned->local_drained()&&field->drained()&&
            !engines.bootstrap.fault()&&!target->fault()&&!publication.fault()&&runtime.result().quiet;
    }
};
}

DsromS81MinimumSourcePlan dsrom_s81_bind_minimum_source(
    DsromS81MinimumRuntime& runtime,std::shared_ptr<Vnative_vm> vm) {
    auto source=std::make_shared<Source>(runtime,std::move(vm));
    DsromS81MinimumSourcePlan plan;
    plan.identity=ID;plan.embedding_library="/tmp/dsrom-s81-embedding-8f65ab021/libdsrom_s81_embedding.so";
    plan.embedding_socket="/tmp/dsrom-s81-embedding-cbe13bd57.sock";
    plan.embedding_sink=source->target->sink();
    const auto offer=plan.embedding_sink.offer;
    plan.embedding_sink.offer=[source,offer](const auto& out) {
        try{return offer(out);}catch(...) {
            fprintf(stderr,"EMBEDDING_NATIVE_OFFER_FAULT cycle=%ld address=%u committed_words=%u published=%u accepted=%u acknowledged=%u\n",
                source->runtime.cycle(),out.vm_address,out.committed_words,
                source->target->published_words(),source->target->accepted_words(),
                source->target->acknowledged_words());
            throw;
        }
    };
    plan.attach=[source](auto& embedding){source->attach(embedding);};
    plan.begin_prefix=[source](){source->begin();};
    plan.advance=[source](){source->advance();};
    plan.complete=[source](){return source->complete();};
    return plan;
}
