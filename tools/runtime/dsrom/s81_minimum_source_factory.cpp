#include "s81_minimum_source_plan.hpp"
#include "s81_minimum_source_bindings.hpp"
#include "s81_minimum_input_participant.hpp"
#include "s81_minimum_return_cut_join.hpp"
#include "s81_minimum_xu.hpp"
#include "s81_minimum_l20_bank.hpp"
#include "s81_minimum_prefix_providers.hpp"
#include "s81_minimum_su256_ports.hpp"
#include "s81_minimum_l20_index_writer.hpp"
#include "s81_minimum_index_source_l20.hpp"
#include "VDsromS81IndexScorer.h"
#include "s81_published_span_accept_sink.hpp"
#include "Vnative_vm.h"
#include "Vretn.h"
#include "Vroot.h"
#ifdef DSROM_S81_NATIVE_CONTINUATION_HEADER
#include DSROM_S81_NATIVE_CONTINUATION_HEADER
#endif
#include <fstream>
#include <cstdio>
#include <cstdlib>
#ifdef DSROM_S81_HEAD_WINNER_BINDING_HEADER
#include <filesystem>
#include <spawn.h>
#include <sys/wait.h>
#include <cerrno>
extern char** environ;
#include "s81_native_bf_head_factory.hpp"
#include "s81_native_head_argmax.hpp"
#include "VDsromS81CoreEnd.h"
#include "VDsromS81CoreEnd___024root.h"
#ifdef DSROM_S81_NATIVE_HEAD_STREAM
#include "VDsromHeadStreamR1.h"
#include "VDsromHeadStreamR2.h"
#include "VDsromHeadStreamR3.h"
#define DSROM_S81_RETAINED_HEAD_STREAM_BIND_ONLY
#include "../../../rtl/test/s81_native_bf_head_producer/retained_smoke.cpp"
#undef DSROM_S81_RETAINED_HEAD_STREAM_BIND_ONLY
#endif
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#endif
#ifdef DSROM_S81_L20_KV_ENCLOSING
#include "s81_minimum_l20_kv_factory.hpp"
#endif

namespace {
using namespace dsrom_s81_minimum;
constexpr uint64_t ID=uint64_t(1)<<31;
constexpr uint32_t OUTPUT_BASE=419776,OUTPUT_ROWS=320,CUT_ALIAS=32768;
// 9 + canonical ordered source-node index of L0.I7 (not its PHROM phase).
constexpr unsigned FIELD_PRODUCER=16;
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
    // QE enrollment extends these observers AFTER target construction. The
    // target forwards to their current value so actual acceptance/old-head
    // visibility reaches every owning actor without a second retirement.
    std::function<void(unsigned,const MacroWrite&,const VmReceipt&)> factory_visibility;
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
    bool attached=false,armed=false,field_selected=false,field_returned=false;
    bool field_publication_begun=false;
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
        factory_visibility=[this](unsigned bank,const auto& c,const auto& receipt){
            publication.on_prefix_scalar_ack(c,receipt);
            dsrom_s81_retire_source_scalar_tag(runtime,bank,c,receipt);
        };
        target=std::make_unique<Target>(*vm,ID,0,
            [this](const auto& out,unsigned lane) {
                return out.vm_address<20480?tags.record(out,lane):publication.record(out,lane);
            },
            [this](auto id,auto a,auto n){return publication.source_span_lease(id,a,n);},
            [this](auto id,auto a,auto n){return publication.write_allowed(id,a,n);},
            [this](const auto& c,const auto& receipt){
                factory_visibility(c.word.address&3,c,receipt);
            },
            Target::AcceptObservers{true,
                [this](auto bank,const auto& c){tags.scalar_accept(bank,c);},
                [this](auto address,const auto& owner){tags.read_accept(address,owner);}});
        prefix_bank=target->participant();
        publication.enroll_literal(FIELD_PRODUCER,{{OUTPUT_BASE,OUTPUT_ROWS}});
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
        require(id==ID&&!field_selected,"native read while field owns shared bank or wrong context");
        // Reserve exactly once for the held request, not once per polling call.
        if(!read_pending) {
            read_owner=tags.read_owner(id,address);read_address=address;read_pending=true;
        }
        require(address==read_address,"changed held source native read address");
        auto bits=target->target_word(address,read_owner);
        if(bits) {
            dsrom_s81_retire_source_read_tag(runtime,address,read_owner);
            read_pending=false;
        }
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
            engines.su,engines.he,std::move(hooks),
            std::vector<DsromS81PrefixOperation>{},
            std::map<unsigned,DsromS81PrefixNativeEngine>{{4,
                dsrom_s81_bind_minimum_xu(runtime,ID,publication,io(),tags)}});
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
            [this](auto bank,const auto& command){
                returned->accepted(bank,command);tags.scalar_accept(bank,command);
                // An actual selected root write has reached VM acceptance.
                // No source output version or payload is installed at host arm.
                if(!field_publication_begun) {
                    publication.begin(ID,FIELD_PRODUCER);field_publication_begun=true;
                }
                publication.native_scalar(FIELD_PRODUCER,command,true);
            },
            [this](auto bank,const auto& command,const auto& receipt){
                returned->visible(bank,command,receipt);
                target->external_scalar_visible(command,receipt);
            });
        field_bank=field->participant();
        // Select once in prepare; use that SAME participant for this edge's
        // rising/falling. There is exactly one native bank clock owner.
        runtime.participants.push_back({"selected-single-native-bank",
            [this](const auto& result) {
                if(armed&&!field_returned&&input->inputs_loaded()) {
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
        if(field_selected&&input->input_finished()&&returned->local_drained()&&
                field->drained()&&runtime.result().quiet) {
            require(!read_pending,"field/native handoff has accepted read debt");
            field_selected=false;field_returned=true;
#ifdef DSROM_S81_NATIVE_CONTINUATION_HEADER
            // Generated from literal source operations. Missing engine maps,
            // dynamic inputs or full output extents still refuse admission.
            require(publication.complete(FIELD_PRODUCER),
                    "literal continuation lacks complete source field output; component rows are insufficient");
            s81_native_operations_enroll(publication);
            prefix->load_program(s81_native_operations());
#endif
        }
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
        return attached&&armed&&field_returned&&prefix->complete()&&!read_pending&&
            input->input_finished()&&returned->local_drained()&&field->drained()&&
            !engines.bootstrap.fault()&&!target->fault()&&!publication.fault()&&runtime.result().quiet;
    }
};

// First native replacement in the working SIM_ONLY L20 chain. This is one
// source operation, not a claim that the remaining 143 operations are native.
#ifdef DSROM_S81_HEAD_WINNER_BINDING_HEADER
// Existing component owners composed on ONE enclosing clock. No expected
// logits, private edge loop, new runtime fields or replacement arithmetic.
struct HeadBytes {
    int fd=-1;size_t size=0;unsigned char* mapped=nullptr;uint64_t offset=0;
    HeadBytes() {
        const char* path=std::getenv("DSROM_S81_NATIVE_HEAD_SHARD");
        const char* base=std::getenv("DSROM_S81_NATIVE_HEAD_BYTE_OFFSET");
        Source::require(path&&*path&&base&&*base,"actual released head shard/byte offset required");
        size_t used=0;offset=std::stoull(base,&used,10);
        Source::require(used==std::string(base).size()&&base[0]!='-',"head byte offset must unsigned decimal");
        fd=open(path,O_RDONLY);struct stat stat{};
        if(fd<0||fstat(fd,&stat))throw std::runtime_error("actual released head shard unavailable");
        size=size_t(stat.st_size);
        Source::require(offset<=size&&129280ull*5120*2<=size-offset,"released head byte extent");
        mapped=static_cast<unsigned char*>(mmap(nullptr,size,PROT_READ,MAP_PRIVATE,fd,0));
        if(mapped==MAP_FAILED){mapped=nullptr;close(fd);fd=-1;throw std::runtime_error("head raw mapping failed");}
    }
    ~HeadBytes(){if(mapped)munmap(mapped,size);if(fd>=0)close(fd);}
    std::array<uint32_t,9> word(unsigned rank,unsigned row,unsigned h,unsigned lane)const {
        Source::require(rank<4&&row<32320&&h<40&&lane<16,"released native BF head source address");
        std::array<uint32_t,9> out{};
        for(unsigned b=0;b<8;++b) {
            auto a=offset+((uint64_t(rank)*32320+row)*5120+h*128+lane*8+b)*2;
            const uint16_t value=uint16_t(mapped[a])|(uint16_t(mapped[a+1])<<8);
            out[b/2]|=uint32_t(value)<<((b%2)*16);
        }
        return out; // exact raw BF16; native arithmetic owns every rounding
    }
};

struct HeadRank {
    DsromS81MinimumRuntime rt{};
    std::shared_ptr<Vnative_vm> vm;
    DsromS81MinimumSourceTags tags;
    PrefixPublication publication{ID};
    std::unique_ptr<Target> target;
    DsromS81MinimumSourceIo io;
    DsromS81MinimumParticipant bank;
    DsromS81PrefixNativeEngine su;
    std::unique_ptr<DsromS81MinimumPrefixOutputBatch> batch;
    std::array<DsromS81PrefixOperation,5> ops{};
    std::vector<uint32_t> h,pf;
    std::array<uint32_t,5120> xn{};
    uint32_t read_address=0;
    DsromS81MinimumSourceTags::Owner read_owner{};
    unsigned input_batch=0,norm=0,prefetched=0,logits=0;
    unsigned accepted_this_edge=0;
    bool initialized=false,inputs_done=false,pf_captured=false,norm_live=false,norm_offer=false;
    bool normalizations_done=false,publication_begun=false;
    bool read_pending=false;
    S81EmbeddingOutput loading{};
    bool loading_held=false,loading_offered=false;

    static std::vector<uint32_t> raw(const std::string& path,unsigned count) {
        std::ifstream f(path,std::ios::binary);Source::require(bool(f),"actual produced head input missing");
        std::vector<uint32_t> out(count);
        for(auto& v:out){unsigned char b[4];f.read(reinterpret_cast<char*>(b),4);
            Source::require(f.gcount()==4,"head raw input truncated");
            v=uint32_t(b[0])|(uint32_t(b[1])<<8)|(uint32_t(b[2])<<16)|(uint32_t(b[3])<<24);}
        Source::require(f.peek()==std::char_traits<char>::eof(),"head raw input extent differs");return out;
    }
    HeadRank(DsromS81MinimumRuntime& enclosing,unsigned rank,std::shared_ptr<Vnative_vm> actual_vm,
             const std::string& dir):vm(std::move(actual_vm)) {
        rt.stage=80;rt.rank=rank;rt.pair=11;rt.bf16=true;rt.context=enclosing.context;
        rt.cycle=enclosing.cycle;rt.tick=enclosing.tick;rt.result=enclosing.result;rt.drive=enclosing.drive;
        tags=dsrom_s81_bind_minimum_source_tags(rt,ID);
        target=std::make_unique<Target>(*vm,ID,0,
            [this](const auto& out,unsigned lane){return out.vm_address<20480?tags.record(out,lane):publication.record(out,lane);},
            [this](auto id,auto a,auto n){return publication.source_span_lease(id,a,n);},
            [this](auto id,auto a,auto n){return publication.write_allowed(id,a,n);},
            [this](const auto& c,const auto& receipt){publication.on_prefix_scalar_ack(c,receipt);
                dsrom_s81_retire_source_scalar_tag(rt,c.word.address&3,c,receipt);},
            Target::AcceptObservers{true,
                [this](unsigned b,const auto& c){tags.scalar_accept(b,c);accepted_this_edge|=1u<<b;},
                [this](auto a,const auto& owner){tags.read_accept(a,owner);}});
        io={
            [this](auto id,uint32_t a)->std::optional<uint32_t>{
                Source::require(id==ID,"head source read identity differs");
                if(!read_pending){read_owner=tags.read_owner(id,a);read_address=a;read_pending=true;}
                Source::require(read_address==a,"head changed held actual VM read");
                auto value=target->target_word(a,read_owner);
                if(value){dsrom_s81_retire_source_read_tag(rt,a,read_owner);read_pending=false;}return value;},
            [this](auto id,auto a,auto n){return target->source_span_lease(id,a,n);},
            [this](const auto& out,unsigned n){return target->offer_prefix(out,n);},
            [this](const auto& out,unsigned n){return target->visible_prefix(out,n);}};
        // Optional actual L20 END operands; normalization instructions and
        // CROM stay in the existing released input home. Files do not grant
        // publication: load() still offers every word to the actual VM/ACK path.
        const char* carry=std::getenv("DSROM_S81_NATIVE_HEAD_CARRY_DIR");
        const std::string operand_dir=carry&&*carry?carry:dir;
        h=raw(operand_dir+"/H_rank"+std::to_string(rank)+".u32",20480);
        pf=raw(operand_dir+"/PF_rank"+std::to_string(rank)+".u32",4);
        std::ifstream literal(dir+"/normalization.words");
        const std::array<std::vector<std::pair<uint32_t,uint32_t>>,5> extents{{
            {{20480,5120}},{{20480,5120}},{{41344,5120},{51584,1}},{{51616,1}},{{46464,5120}}}};
        for(unsigned i=0;i<5;++i){auto& op=ops[i];literal>>std::dec>>op.index;op.unit=2;
            for(auto& w:op.instruction)literal>>std::hex>>w;
            Source::require(bool(literal)&&op.index==4887+i,"literal native head normalization identity differs");
            publication.enroll_literal(op.index,extents[i]);}
        publication.enroll_literal(4892,{{486848,32320}});
        su=dsrom_s81_bind_minimum_su256(rt,ID,publication,io,tags);
        batch=std::make_unique<DsromS81MinimumPrefixOutputBatch>(rt,ID,publication,io,tags);
        bank=target->participant();
    }
    void initialize(){Source::require(!initialized,"head rank initialized twice");
        Source::require(!rt.identity,"head rank already has context");rt.identity=ID;initialized=true;}
    void load() {
        if(inputs_done)return;
        if(input_batch<1280){
            if(!loading_held){loading={};loading.vm_valid=1;loading.vm_identity=ID;
                loading.vm_address=(input_batch%4)*5120+(input_batch/4)*16;
                std::copy_n(h.begin()+loading.vm_address,16,loading.vm_data);loading_held=true;loading_offered=false;}
            if(!loading_offered)loading_offered=target->offer(loading);
            if(loading_offered&&target->visible(loading)){loading_held=false;++input_batch;}return;
        }
        if(!pf_captured){publication.begin(ID,PrefixPublication::PF);
            loading={};loading.vm_valid=1;loading.vm_identity=ID;loading.vm_address=41152;
            for(unsigned n=0;n<4;++n){loading.vm_data[n]=pf[n];
                dsrom_s81_capture_minimum_prefix_scalar(rt,publication,PrefixPublication::PF,loading,n,true);}
            pf_captured=true;loading_offered=false;}
        if(!loading_offered)loading_offered=io.offer(loading,4);
        if(loading_offered&&io.visible(loading,4))inputs_done=true;
    }
    void normalize() {
        if(!inputs_done)return;
        if(norm_live){if(!su.idle()||!publication.complete(ID,ops[norm].index))return;
            su.drive(ops[norm],false);norm_live=false;++norm;}
        if(norm<5){if(!su.inputs_ready(ops[norm])||!su.ready())return;
            su.drive(ops[norm],true);norm_live=true;norm_offer=true;return;}
        if(prefetched<5120){auto value=io.read_word(ID,46464+prefetched);if(value)xn[prefetched++]=*value;return;}
        normalizations_done=true;
    }
    bool normalization_visible() const {
        // Host progress alone is not a source-span grant. HEAD admission must
        // retain the same actual input ACKs and final native SU writer version
        // that produced the held XN readbacks in this bank/context.
        return initialized&&inputs_done&&normalizations_done&&prefetched==5120&&
            !read_pending&&!fault()&&publication.complete(ID,PrefixPublication::PF)&&
            target->source_span_lease(ID,0,20480)&&
            io.span_lease(ID,41152,4)&&publication.complete(ID,ops[4].index)&&
            io.span_lease(ID,46464,5120);
    }
    void prepare(){accepted_this_edge=0;su.participant.prepare(rt.result());}
    void prepare_bank(){bank.prepare(rt.result());
        // Same bank owner's LOW combinational settle, no extra rising edge.
        vm->clk=0;vm->rst_n=initialized;vm->eval();}
    void rising(bool released){const bool go=released&&norm_offer&&su.ready();
        bank.rising(released);su.participant.rising(released);
        if(go){publication.begin(ID,ops[norm].index);su.drive(ops[norm],false);norm_offer=false;}}
    void falling(bool released){bank.falling(released);su.participant.falling(released);}
    bool fault()const{return target->fault()||publication.fault()||su.participant.fault();}
    bool published()const{return logits==32320&&!read_pending&&!batch->pending()&&
        publication.complete(ID,4892)&&io.span_lease(ID,486848,32320)&&!fault();}
};

struct SourceHeadEnd:std::enable_shared_from_this<SourceHeadEnd> {
    DsromS81MinimumRuntime& runtime;
    std::shared_ptr<VDsromS81CoreEnd> core;
    std::shared_ptr<HeadBytes> bytes;
    std::array<std::unique_ptr<HeadRank>,4> ranks;
    std::array<DsromS81MinimumSourceIo,4> ios;
    std::shared_ptr<DsromS81NativeHeadArgmax> argmax;
#ifdef DSROM_S81_NATIVE_HEAD_STREAM
    std::unique_ptr<VDsromHeadStreamR1> stream1;
    std::unique_ptr<VDsromHeadStreamR2> stream2;
    std::unique_ptr<VDsromHeadStreamR3> stream3;
    std::array<DsromS81MinimumParticipant,3> stream_participants;
    std::array<bool,4> native_write_taken{};
    std::shared_ptr<DsromS81NativeHeadCollective> stream_collective;
    DsromS81MinimumParticipant stream_transport;
    static uint64_t positive_delay(const char* name) {
        const char* value=std::getenv(name);
        Source::require(value&&*value,"native stream needs explicit selected positive transport cycles");
        uint64_t result=0;
        for(const char* c=value;*c;++c){
            Source::require(*c>='0'&&*c<='9'&&result<=(UINT64_MAX-unsigned(*c-'0'))/10,
                "native stream transport cycles invalid/overflow");
            result=result*10+unsigned(*c-'0');
        }
        Source::require(result>0,"native stream cannot use zero transport cycles");return result;
    }
    template<class Native> void bind_stream(Native& native,unsigned rank) {
        stream_participants[rank-1]=dsrom_s81_retained_head_stream_participant(runtime,native,*ranks[rank]->vm,
            rank,ID,1,[this,rank](){return dot&&current==rank&&!ranks[rank]->publication_begun&&cut.go&&cut.ready;},
            [this,rank]()->const NativeBfHeadRoots*{return current==rank&&held?&*held:nullptr;},
            [this,rank]()->const uint32_t*{return current==rank&&held&&!taken&&tail_stage>=4?&join_bits:nullptr;},
            [this,rank](){return ranks[rank]->publication_begun;},
            [this,rank](){Source::require(current==rank&&held&&!native_write_taken[rank],
                "native stream duplicate/foreign accepted logit");native_write_taken[rank]=true;});
    }
#endif
    Vcut cut;Vretn pad1,pad2,join;
    std::unique_ptr<DsromS81NativeHeadBinding> head;
    DsromS81MinimumParticipant input,returned,cold_return;
    std::optional<NativeBfHeadRoots> held;
    std::optional<DsromS81HeadArgmaxResult> winner;
    std::optional<DsromS81NativeHeadRecord> local_packet;
    DsromS81NativeHeadRecord sampled_packet;
    unsigned current=0,tail_stage=0;
    uint32_t join_tag=0,join_bits=0;
    bool attached=false,initialized=false,dot=false,taken=false,root_sent=false,observed_head_go=false;
    bool sampled_root=false,sampled_packet_take=false,sampled_final=false,winner_taken=false,consumed=false;
    bool argmax_started=false,replay=false,sim_actual_xn=false;
    std::optional<unsigned> replay_row;
    std::array<std::vector<uint32_t>,4> returned_outputs;
    bool returned_rows()const{return replay||sim_actual_xn;}
    unsigned row()const{return returned_rows()?*replay_row:held->local_row;}
    bool pending()const{return returned_rows()?bool(replay_row):bool(held);}
    static void pinned_file(const std::string& path,const char* expected) {
        std::ifstream f(path,std::ios::binary);Source::require(bool(f),"native boundary source pin missing");
        f.seekg(0,std::ios::end);const auto size=f.tellg();
        Source::require(size>=0&&size<=4*1024*1024,"native boundary metadata/output extent differs");
        f.seekg(0);std::vector<unsigned char> bytes(static_cast<size_t>(size));
        f.read(reinterpret_cast<char*>(bytes.data()),bytes.size());
        Source::require(size_t(f.gcount())==bytes.size(),"native boundary source pin read failed");
        unsigned char digest[SHA256_DIGEST_LENGTH];SHA256(bytes.data(),bytes.size(),digest);
        static constexpr char hex[]="0123456789abcdef";std::string actual;
        for(auto b:digest){actual+=hex[b>>4];actual+=hex[b&15];}
        Source::require(actual==expected,"native boundary source/terminal/output SHA differs");
    }
    unsigned expected_accept=0;
    std::array<std::optional<uint32_t>,2> xread_pipe{};
    std::optional<uint32_t> sampled_xread;

    template<class Packed> static void pin(Packed& out,unsigned offset,unsigned width,uint64_t value){
        for(unsigned n=0;n<width;++n){auto mask=uint32_t(1)<<((offset+n)%32);
            out[(offset+n)/32]=(out[(offset+n)/32]&~mask)|(((value>>n)&1u)<<((offset+n)%32));}}
    template<class Packed> static uint64_t get(const Packed& data,unsigned offset,unsigned width){
        uint64_t out=0;for(unsigned n=0;n<width;++n)out|=uint64_t((data[(offset+n)/32]>>((offset+n)%32))&1u)<<n;
        return out;}
    SourceHeadEnd(DsromS81MinimumRuntime& r,std::shared_ptr<Vnative_vm> vm,std::shared_ptr<VDsromS81CoreEnd> c)
        :runtime(r),core(std::move(c)),
         cut(r.context,"head_shared_native_input"),pad1(r.context,"head_shared_pad1"),
         pad2(r.context,"head_shared_pad2"),join(r.context,"head_shared_join") {
        Source::require(r.stage==80&&r.rank==0&&r.pair==11&&r.bf16&&!r.identity&&core&&
            core->contextp()==r.context,"native HEAD-END requires cold stage80/rank0/pair11 shared core");
        const char* input_dir=std::getenv("DSROM_S81_NATIVE_HEAD_INPUT_DIR");
        Source::require(input_dir&&*input_dir,"actual produced four-rank H/PF input directory required");
        const std::string dir=input_dir;
        const char* crom=std::getenv("DSROM_S81_MINIMUM_CROM_HEX");
        Source::require(crom&&std::string(crom)==dir+"/norm.crom.hex","head requires the released normalization CROM");
        for(unsigned rank=0;rank<4;++rank){
            auto bank=rank==0?vm:std::make_shared<Vnative_vm>(r.context,("head_native_vm_r"+std::to_string(rank)).c_str());
            ranks[rank]=std::make_unique<HeadRank>(r,rank,std::move(bank),dir);ios[rank]=ranks[rank]->io;
        }
        const char* sim=std::getenv("DSROM_S81_SIM_ONLY_HEAD_RETURN");
        Source::require(!sim||std::string(sim)=="0"||std::string(sim)=="1","HEAD return selector must explicit 0/1");
        replay=sim&&std::string(sim)=="1";
        const char* actual_xn=std::getenv("SIM_ONLY_HEAD_ACTUAL_XN");
        Source::require(!actual_xn||std::string(actual_xn)=="0"||std::string(actual_xn)=="1",
            "actual-XN math selector must explicit 0/1");
        sim_actual_xn=actual_xn&&std::string(actual_xn)=="1";
        Source::require(!(replay&&sim_actual_xn),"actual-XN math cannot consume archived logits");
#ifdef DSROM_S81_NATIVE_HEAD_STREAM
        Source::require(!returned_rows(),"native stream requires actual roots; SIM_ONLY returns are not native enrollment");
#endif
        if(replay) {
            const char* archive=std::getenv("DSROM_S81_NATIVE_HEAD_RETURN_DIR");
            Source::require(archive&&*archive,"SIM_ONLY HEAD return requires explicit actual native archive");
            const std::string path=archive;
            // Exact completed native source/terminal, not its reference oracle.
            pinned_file(path+"/source.json","53a83c84c1d43582ab666282c205d94502bf2fba4d3d81600b8b53c4cbf63811");
            pinned_file(path+"/terminal.json","b611dd547ab568a9036de63ecd642d3b916fc87064ab91ce3dfe85bfb3a75ebd");
            const std::array<const char*,4> pins{{
                "38ff35daf21de4c234b4891c8a499009aea34189c16385fccaafefcf60ca0aae",
                "4830a0563b31349055bdad7d4ccd1be4e575d5542d5a7fb1281ae985021e22a1",
                "9d3e73a645c34ee389a47f41a2b1cab1bee33fd7b67ffe5a6a06185f6ae4da93",
                "d2402bb6f734d3b4bfdd70980592b79230ce4b89e5dd0d59cbe1bc295c7fb540"}};
            for(unsigned rank=0;rank<4;++rank){
                const auto file=path+"/logits_rank"+std::to_string(rank)+".u32";pinned_file(file,pins[rank]);
                returned_outputs[rank]=HeadRank::raw(file,32320);
                for(auto bits:returned_outputs[rank])Source::require((bits&0x7f800000u)!=0x7f800000u,"native archived nonfinite HEAD value");
            }
        }else if(sim_actual_xn) {
            bytes=std::make_shared<HeadBytes>(); // released source extent, never a logit oracle
        }else {
        bytes=std::make_shared<HeadBytes>();
        head=std::make_unique<DsromS81NativeHeadBinding>(r,cut,ios,
            [source=bytes](auto rank,auto row,auto h,auto lane){return source->word(rank,row,h,lane);},
            [this](const NativeBfHeadRoots& roots){
                auto& rank=*ranks.at(current);
                Source::require(roots.identity==ID&&roots.request_sequence==1&&roots.rank==current&&
                    roots.local_row==rank.logits-(taken?1u:0u),"native HEAD held root owner/order differs");
                if(!held){held=roots;tail_stage=0;taken=false;root_sent=false;
#ifdef DSROM_S81_NATIVE_HEAD_STREAM
                    native_write_taken[current]=false;
#endif
                    return false;}
                Source::require(held->root4096==roots.root4096&&held->root1024==roots.root1024,
                    "native HEAD changed root before positive VM ACK");
                if(!taken)return false;
#ifdef DSROM_S81_NATIVE_HEAD_STREAM
                Source::require(current==0||native_write_taken[current],"producer release without actual native stream take");
#endif
                held.reset();tail_stage=0;taken=false;root_sent=false;return true;});
        input=head->selected_input_participant();returned=head->selected_return_participant();cold_return=head->return_participant();
        }
#ifdef DSROM_S81_NATIVE_HEAD_STREAM
        stream1=std::make_unique<VDsromHeadStreamR1>(r.context,"head_stream_rank1");
        stream2=std::make_unique<VDsromHeadStreamR2>(r.context,"head_stream_rank2");
        stream3=std::make_unique<VDsromHeadStreamR3>(r.context,"head_stream_rank3");
        bind_stream(*stream1,1);bind_stream(*stream2,2);bind_stream(*stream3,3);
        const auto link=positive_delay("DSROM_S81_NATIVE_HEAD_LINK_CYCLES");
        const auto final=positive_delay("DSROM_S81_NATIVE_HEAD_FINAL_CYCLES");
        stream_collective=std::make_shared<DsromS81NativeHeadCollective>(
            std::array<DsromS81NativeHeadPorts,4>{dsrom_s81_native_head_ports(*core),
                dsrom_s81_retained_head_stream_ports(*stream1),dsrom_s81_retained_head_stream_ports(*stream2),
                dsrom_s81_retained_head_stream_ports(*stream3)},ID,
            std::array<uint64_t,3>{link,link,link},std::array<uint64_t,4>{final,final,final,final},true);
        stream_transport=dsrom_s81_native_head_collective_participant(r,stream_collective,ID);
#else
        argmax=std::make_shared<DsromS81NativeHeadArgmax>(r,ID,ios,486848);
#endif
        for(auto* node:{&pad1,&pad2,&join}){node->clk=0;node->rst_n=0;node->a_v=node->b_v=0;node->a_e=node->b_e=0;}
    }
    void drive_tail(Vretn& node,uint32_t a,uint32_t b){const unsigned row=current*32320+held->local_row;
        node.a_v=node.b_v=1;node.a_t=(row<<13)|2;node.b_t=(row<<13)|258;node.a_d=a;node.b_d=b;}
    void prepare(const DsromS81PairResult& old) {
        // Coarse diagnostics go to the caller's existing runtime journal.
        // Reuse actual source counters; do not add polling or ownership state.
        if(runtime.identity && runtime.cycle()%65536==0) {
            bool all_published=true;
            for(const auto& rank:ranks)all_published=all_published&&rank->published();
            fprintf(stderr,"HEAD_NATIVE_PROGRESS cycle=%ld phase=%s math=%s rank=%u I5_accepted=%u "
                "norm_ops=%u,%u,%u,%u published_rows=%u,%u,%u,%u "
                "final_accepted=%u END_done=%u\n",
                runtime.cycle(),!dot?"normalization":all_published?"collective-END":"DOT",
                sim_actual_xn?"SIM_ONLY_HEAD_ACTUAL_XN":replay?"native-archive-return":"native",
                current,unsigned(dot),ranks[0]->norm,ranks[1]->norm,ranks[2]->norm,ranks[3]->norm,
                ranks[0]->logits,ranks[1]->logits,ranks[2]->logits,ranks[3]->logits,
                unsigned(winner_taken),unsigned(core->done));
            fflush(stderr);
        }
        for(auto& rank:ranks)rank->prepare();
        if(head){input.prepare(old);returned.prepare(old);}else runtime.drive({});
        if(returned_rows()&&dot&&current<4&&!replay_row&&ranks[current]->logits<32320) {
            replay_row=ranks[current]->logits;join_bits=returned_outputs[current][*replay_row];tail_stage=4;root_sent=false;
        }
        for(auto* node:{&pad1,&pad2,&join}){node->a_v=node->b_v=0;node->a_e=node->b_e=0;}
        if(held&&!taken){
            if(tail_stage==0){drive_tail(pad1,held->root1024,0);tail_stage=1;}
            else if(tail_stage==1&&pad1.o_v){Source::require(!pad1.o_e,"native HEAD pad1 error");drive_tail(pad2,pad1.o_d,0);tail_stage=2;}
            else if(tail_stage==2&&pad2.o_v){Source::require(!pad2.o_e,"native HEAD pad2 error");drive_tail(join,held->root4096,pad2.o_d);tail_stage=3;}
            else if(tail_stage==3&&join.o_v){
                Source::require(!join.o_e&&join.o_t==(((current*32320+row())<<13)|34u),"native HEAD join tag/error");
                join_tag=join.o_t;join_bits=join.o_d;tail_stage=4;
            }
        }
        std::fill_n(&core->rom_fr[0],276,0u);
        std::fill_n(&core->capture_vm_accept[0],4,0u);
        expected_accept=0;sampled_root=false;sampled_packet_take=false;sampled_final=false;
        sampled_xread=core->rom_xre?std::optional<uint32_t>(core->rom_xaddr):std::nullopt;
        if(xread_pipe[1]) {
            const auto base=*xread_pipe[1];
            Source::require(base>=46464&&uint64_t(base)+64<=51584,"native HEAD core X read outside accepted staged XN");
            for(unsigned lane=0;lane<64;++lane)core->rom_xq[lane]=ranks[0]->xn[base-46464+lane];
        }
        if(pending()&&!taken&&tail_stage>=4){
            auto& rank=*ranks[current];
            Source::require(rank.publication_begun,"native HEAD output precedes actual phase GO");
            if(current==0){
                const unsigned root=(row()%256)/2;
                if(tail_stage==4&&!root_sent&&core->capture_live){
                    // Source-static root map, actual native joined FP32 value.
                    // No payload is published here; the ORIGINAL core capture
                    // must emit its own live writer before bank admission.
                    const unsigned off=root*69;
                    pin(core->rom_fr,off+17,32,join_bits);pin(core->rom_fr,off+52,16,row());
                    pin(core->rom_fr,off+68,1,1);sampled_root=true;
                }
                unsigned writers=0;
                for(unsigned k=0;k<128;++k)if(get(core->rom_we,k,1)){
                    ++writers;Source::require(root_sent&&k==root&&
                        get(core->rom_waddr,30*k,30)==486848+row()&&
                        get(core->rom_wdata,32*k,32)==join_bits,
                        "live core HEAD writer differs from retained native join");
                }
                Source::require(writers<=1,"native HEAD emitted an unowned simultaneous writer");
                if(writers&&!rank.batch->pending()) {
                    S81EmbeddingOutput out{};out.vm_valid=1;out.vm_identity=ID;out.vm_address=486848+row();
                    out.vm_data[0]=uint32_t(get(core->rom_wdata,root*32,32));rank.batch->capture(4892,out,1,true);
                }
                if(rank.batch->pending()&&rank.batch->progress()){++rank.logits;taken=true;}
                for(auto& owner:ranks)owner->prepare_bank();
                if(writers){
                    const unsigned bank=((486848+row())>>4)&3u;
                    Source::require(rank.vm->wr_accept_v&(1u<<bank),"core capture writer lacks same-edge actual VM acceptance");
                    pin(core->capture_vm_accept,root,1,1);expected_accept=1u<<bank;
                }
            }else {
                if(returned_rows()&&!rank.batch->pending()) {
                    S81EmbeddingOutput out{};out.vm_valid=1;out.vm_identity=ID;out.vm_address=486848+row();out.vm_data[0]=join_bits;
                    rank.batch->capture(4892,out,1,true); // explicit SIM_ONLY boundary writer, not a new native join observation
                }
                const bool ack=returned_rows()?rank.batch->progress():
                    dsrom_s81_publish_minimum_head_logit(rank.rt,*rank.batch,ID,current,row(),join_tag,join_bits,true);
                if(ack){++rank.logits;taken=true;}
                for(auto& owner:ranks)owner->prepare_bank();
                Source::require(get(core->rom_we,0,64)==0&&get(core->rom_we,64,64)==0,"late core HEAD writer after rank0 drain");
            }
        }else {
            for(auto& rank:ranks)rank->prepare_bank();
            Source::require(get(core->rom_we,0,64)==0&&get(core->rom_we,64,64)==0,"core HEAD writer without native retained owner");
        }
#ifdef DSROM_S81_NATIVE_HEAD_STREAM
        // All banks have settled OLD acceptance. This gates their live wr_v
        // before the SAME sole bank rising edge and drives the native tuple.
        for(auto& participant:stream_participants)participant.prepare(old);
        if(core->head_dn_valid&&core->head_dn_ready){
            sampled_packet={};sampled_packet.identity=core->head_dn_identity;sampled_packet.last=core->head_dn_last;
            for(unsigned i=0;i<16;++i)sampled_packet.data[i]=core->head_dn_data[i];
            Source::require(!local_packet&&sampled_packet.identity==ID&&sampled_packet.last&&
                get(sampled_packet.data,16,4)==6&&get(sampled_packet.data,160,1)&&
                get(sampled_packet.data,128,32)<32320,"native core rank0 packet source differs");
            sampled_packet_take=true;
        }
        if(stream3->downstream_valid&&stream3->downstream_ready){
            Source::require(!winner&&stream3->downstream_identity==ID&&stream3->downstream_last&&
                get(stream3->downstream_data,16,4)==6&&get(stream3->downstream_data,160,1)&&
                get(stream3->downstream_data,128,32)<129280,
                "native carried global winner source differs");
            // A real native carried packet, not a host argmax or a VM scan.
            winner=DsromS81HeadArgmaxResult{ID,1,uint32_t(get(stream3->downstream_data,128,32)),
                uint32_t(get(stream3->downstream_data,96,32))};
        }
#else
        core->head_dn_ready=0;core->head_final_valid=0;
        auto actual=argmax->result();
        if(actual){
            if(winner)Source::require(winner->identity==actual->identity&&winner->sequence==actual->sequence&&
                winner->global_id==actual->global_id&&winner->bits==actual->bits,"native held winner changed");
            else winner=actual;
            if(!local_packet&&core->head_dn_valid){
                sampled_packet={};sampled_packet.identity=core->head_dn_identity;sampled_packet.last=core->head_dn_last;
                for(unsigned i=0;i<16;++i)sampled_packet.data[i]=core->head_dn_data[i];
                const uint32_t id=uint32_t(get(sampled_packet.data,128,32)),bits=uint32_t(get(sampled_packet.data,96,32));
                Source::require(sampled_packet.identity==ID&&sampled_packet.last&&get(sampled_packet.data,16,4)==6&&
                    get(sampled_packet.data,160,1)&&id<32320&&(bits&0x7f800000u)!=0x7f800000u,
                    "actual native core local argmax packet owner/type differs");
                auto value=ios[0].read_word(ID,486848+id);
                if(value){Source::require(*value==bits,"native local head packet differs from actual published VM value");
                    core->head_dn_ready=1;sampled_packet_take=true;}
            }
            auto frame=dsrom_s81_native_head_winner_frame(*winner);
            core->head_final_valid=!winner_taken;core->head_final_identity=frame.identity;
            for(unsigned i=0;i<16;++i)core->head_final_data[i]=frame.data[i];
        }
#endif
    }
    void rising(bool released) {
        observed_head_go=released&&core->rootp->ot_dsrom_s81_actual_core_end__DOT__rom_m_go&&
            core->rootp->ot_dsrom_s81_actual_core_end__DOT__me_amax&&
            core->rootp->ot_dsrom_s81_actual_core_end__DOT__me_nout==32320;
        const bool first=released&&head&&dot&&!ranks[current]->publication_begun&&cut.go&&cut.ready;
        for(auto& rank:ranks)rank->rising(released);
#ifdef DSROM_S81_NATIVE_HEAD_STREAM
        for(auto& participant:stream_participants)participant.rising(released);
#endif
        if(released&&expected_accept)Source::require((ranks[0]->accepted_this_edge&expected_accept)==expected_accept,
            "native core capture acceptance did not occur on its same bank edge");
        if(head){input.rising(released);returned.rising(released);}
        if(first){Source::require(cut.i_ph==0,"native first HEAD phase differs");
            ranks[current]->publication.begin(ID,4892);ranks[current]->publication_begun=true;}
        if(sampled_root&&released)root_sent=true;
        if(sampled_packet_take&&released)local_packet=sampled_packet;
        // Raw-core participant is LAST: it settles LOW before this callback.
        // Sample its real OLD ready; leave the complete tuple unchanged.
        if(released&&core->head_final_valid&&core->head_final_ready){
            Source::require(winner&&local_packet&&!winner_taken,"native HEAD final has no retained provider debt");
            sampled_final=true;winner_taken=true;
        }
        if(!released&&head){cut.clk=1;cut.rst_n=0;cut.eval();cold_return.rising(false);}
        for(auto* node:{&pad1,&pad2,&join}){node->clk=1;node->rst_n=released;node->eval();}
        xread_pipe[1]=xread_pipe[0];xread_pipe[0]=sampled_xread;
    }
    void falling(bool released){for(auto& rank:ranks)rank->falling(released);
#ifdef DSROM_S81_NATIVE_HEAD_STREAM
        for(auto& participant:stream_participants)participant.falling(released);
#endif
        if(head){input.falling(released);returned.falling(released);}
        if(!released&&head){cut.clk=0;cut.eval();cold_return.falling(false);head->observe_shared_cold_reset();}
        for(auto* node:{&pad1,&pad2,&join}){node->clk=0;node->eval();}}
    bool fault()const{
#ifdef DSROM_S81_NATIVE_HEAD_STREAM
        if(core->fault||(head&&(input.fault()||returned.fault()))||pad1.fault||pad2.fault||join.fault||
            stream_collective->fault())return true;
        for(const auto& participant:stream_participants)if(participant.fault())return true;
#else
        if(core->fault||(head&&(input.fault()||returned.fault()))||pad1.fault||pad2.fault||join.fault||argmax->fault())return true;
#endif
        for(const auto& rank:ranks)if(rank->fault())return true;
        return false;}
    bool publications_drained()const {if(!dot||pending()||(!returned_rows()&&!head->all_roots_accepted())||fault())return false;
        for(const auto& rank:ranks)if(!rank->published())return false;
        return true;}
    void initialize(){Source::require(attached&&!initialized&&runtime.identity&&*runtime.identity==ID,
        "HEAD source initialization before actual shared reset/context");
        for(auto& rank:ranks)rank->initialize();
        initialized=true;}
    bool inputs_visible(){Source::require(initialized,"HEAD inputs before cold initialization");
        bool ready=true;for(auto& rank:ranks){rank->load();rank->normalize();ready=ready&&rank->normalization_visible();}return ready;}
    void calculate_actual_xn_rows() {
        const char* helper=std::getenv("DSROM_S81_SIM_ONLY_HEAD_DOT_HELPER");
        const char* output=std::getenv("DSROM_S81_SIM_ONLY_HEAD_DOT_DIR");
        const char* python=std::getenv("DSROM_S81_SIM_ONLY_HEAD_DOT_PYTHON");
        Source::require(helper&&*helper&&output&&*output,
            "actual-XN math requires explicit DOT-only helper and fresh output directory");
        const std::filesystem::path root(output),input=root/"xn",result=root/"dot";
        Source::require(std::filesystem::create_directory(root),"preserve actual-XN math output");
        Source::require(std::filesystem::create_directory(input),"actual-XN input directory unavailable");
        for(unsigned rank=0;rank<4;++rank) {
            auto& owner=*ranks[rank];
            Source::require(owner.normalization_visible(),
                "actual-XN math before matched H/PF/native XN publication and read leases");
            std::ofstream raw(input/("XN_rank"+std::to_string(rank)+".u32"),std::ios::binary);
            Source::require(bool(raw),"actual-XN source output unavailable");
            for(uint32_t value:owner.xn) {
                Source::require(!(value&65535u)&&((value>>23)&255)!=255,
                    "actual-XN math requires finite native BF16-widened readbacks");
                const char b[]={char(value),char(value>>8),char(value>>16),char(value>>24)};
                raw.write(b,4);
            }
            raw.close();Source::require(bool(raw),"actual-XN source output failed");
        }
        // The existing helper computes only released-weight DOT from these
        // actual native readbacks. It cannot normalize, select, or grant ACKs.
        std::vector<std::string> args={python&&*python?python:"python3",helper,
            "--input-dir",input.string(),"--head-shard",std::getenv("DSROM_S81_NATIVE_HEAD_SHARD"),
            "--head-byte-offset",std::to_string(bytes->offset),"--output-dir",result.string()};
        std::vector<char*> argv;for(auto& a:args)argv.push_back(a.data());argv.push_back(nullptr);
        pid_t child;Source::require(posix_spawnp(&child,argv[0],nullptr,nullptr,argv.data(),environ)==0,
            "actual-XN DOT-only helper launch failed");
        int status=0;pid_t waited;
        do {waited=waitpid(child,&status,0);} while(waited<0&&errno==EINTR);
        Source::require(waited==child&&WIFEXITED(status)&&WEXITSTATUS(status)==0,
            "actual-XN DOT-only helper failed; accepted command retained");
        for(unsigned rank=0;rank<4;++rank) {
            returned_outputs[rank]=HeadRank::raw((result/("logits_rank"+std::to_string(rank)+".u32")).string(),32320);
            for(auto value:returned_outputs[rank])Source::require(((value>>23)&255)!=255,
                "actual-XN DOT-only helper returned nonfinite row");
        }
        fprintf(stderr,"HEAD_MATH_SCOPE SIM_ONLY_HEAD_ACTUAL_XN native_normalization=1 native_DOT=0 native_selector=1\n");
        fflush(stderr);
    }
    void start(){Source::require(initialized&&!dot&&observed_head_go,
        "HEAD DOT requires actual accepted original core I5");
        for(const auto& rank:ranks)Source::require(rank->normalization_visible(),
            "HEAD DOT before matched input/native normalization/XN span visibility");
        if(sim_actual_xn)calculate_actual_xn_rows();
        dot=true;current=0;
        if(returned_rows()){for(auto& rank:ranks){rank->publication.begin(ID,4892);rank->publication_begun=true;}}
        else head->start(ID,1,current);}

    void advance(){if(!dot)return;
        if(returned_rows()){
            if(taken){replay_row.reset();taken=false;tail_stage=0;root_sent=false;}
            if(!replay_row&&current<3&&ranks[current]->published())++current;
        }else {
            head->advance();
            if(!held&&head->all_roots_accepted()&&current<3){Source::require(ranks[current]->published(),"HEAD rank rearm before actual publication drain");
                ++current;head->start(ID,1,current);}
        }
        bool all=true;for(const auto& rank:ranks)all=all&&rank->published();
#ifndef DSROM_S81_NATIVE_HEAD_STREAM
        if(all&&!argmax_started&&argmax->inputs_ready()){argmax->start(1);argmax_started=true;}
#endif
    }
    bool complete(){
        if(consumed)return true;
        // Invoked as the existing accepted result consumer ONLY after source.cpp
        // verified real DONE, not as speculative polling of an idle model.
        if(!core->done)return false;
        Source::require(publications_drained()&&winner_taken&&winner&&local_packet&&
            core->next_token==winner->global_id&&core->next_val==winner->bits&&
            winner->identity==ID&&winner->sequence==1,"real END differs from held native winner/publication");
#ifdef DSROM_S81_NATIVE_HEAD_STREAM
        Source::require(stream_collective->complete(),
            "real END before all native carried final deliveries retired");
#else
        argmax->acknowledge(*winner);
#endif
        consumed=true;local_packet.reset();return true;
    }
    void attach(){Source::require(!attached,"HEAD source attached twice");auto self=shared_from_this();
#ifdef DSROM_S81_NATIVE_HEAD_STREAM
        runtime.participants.push_back(stream_transport); // sample OLD native ports before any leaf/core rises
#endif
        runtime.participants.push_back({"native-HEAD-four-source-homes",
            [self](const auto& p){self->prepare(p);},[self](bool r){self->rising(r);},
            [self](bool r){self->falling(r);},[self](){return self->fault();}});
#ifndef DSROM_S81_NATIVE_HEAD_STREAM
        runtime.participants.push_back(argmax->participant());
#endif
        runtime.publication_ready=[self](auto id){return id==ID&&!self->fault();};
        runtime.publication_drained=[self](auto id){return id==ID&&self->publications_drained();};attached=true;
    }
};
#endif

// The opt-in path uses the existing seeded entry, bank and publication owner.
struct SourceL20I0 : std::enable_shared_from_this<SourceL20I0> {
    DsromS81MinimumRuntime& runtime;
    DsromS81MinimumL20Bank bank;
    DsromS81PrefixNativeEngine su;
    DsromS81PrefixOperation operation=DsromS81PrefixOperation{2470,2,"0a8042d53254c972480a5c7c05cf676d0c5e3cbea44e456aa5537b16ce93e622",{0x2u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x800004u,0x0u,0x280u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x4050140u,0xa02u,0x0u,0x0u,0x0u,0x0u,0x8d40000u,0x3c79ca1u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}};
    bool attached=false,started=false,accepted=false,go=false,finished=false;
    bool mutable_h=false;
    std::optional<DsromS81PrefixOperation> h_successor;
    unsigned selected_pc=0; // source PC is distinct from publication producer ID
    uint32_t output_address=40992;
    std::vector<std::pair<uint32_t,uint32_t>> output_spans{{40992,1}};
    long first=-1,last=-1;
    std::optional<uint32_t> output;
    SourceL20I0(DsromS81MinimumRuntime& r,std::shared_ptr<Vnative_vm> vm)
      :runtime(r),bank(r,ID,std::move(vm),dsrom_s81_bind_minimum_source_tags(r,ID),
        std::getenv("DSROM_S81_NATIVE_L20_SU_PC")&&
        std::string(std::getenv("DSROM_S81_NATIVE_L20_SU_PC"))!="0") {
        // Bounded nonfield source selection; ordinary I0 remains the default.
        // These are the unchanged retained L20 H-producing SU literals, not
        // field work, I55, HEAD, or software-computed activations.
        const char* pc=std::getenv("DSROM_S81_NATIVE_L20_SU_PC");
        if(pc&&std::string(pc)!="0") {
            if(std::string(pc)=="76")
                operation=DsromS81PrefixOperation{2547,2,"b697342bd2e9299a0cc2a141a25b26c011f4830af680c74cd7ec21357c5fd820",{0x2u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x10u,0x8000000au,0x528u,0x400000u,0x0u,0x0u,0x4000a08u,0x0u,0x0u,0x2800u,0x8000280u,0x0u,0x0u,0x0u,0x0u,0x6008040u,0x0u,0x1000050u,0x50000000u,0x14000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0xa03u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}};
            else if(std::string(pc)=="142")
                operation=DsromS81PrefixOperation{2613,2,"8aa055e9953fb574d1c9505c6c0d3283c4db8e96c4d2f3d38ca9a778a7411c63",{0x2u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x10u,0x8000000au,0x19f7u,0x400000u,0x0u,0x0u,0x4000a0eu,0x0u,0x0u,0x2800u,0x8000280u,0x0u,0x0u,0x0u,0x0u,0x6008040u,0x0u,0x1000050u,0x50000000u,0x14000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0xa03u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}};
            else throw std::runtime_error("native L20 SU selector must be 0, 76 or 142");
            // Produce the last T version natively on this SAME bank before
            // its H consumer. Upstream operand leases remain mandatory;
            // no expected T/H restoration or borrowed cross-bank ACK exists.
            selected_pc=std::string(pc)=="76"?76:142;
            h_successor=operation;
            if(std::string(pc)=="76")
                operation=DsromS81PrefixOperation{2546,2,"fab801f2bcbcd4cdff06867c95bb963c9d1dd59a7416dd7a5460a4ad3322804d",{0x2u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x10u,0xau,0xf0u,0x400000u,0x0u,0xc0000000u,0x4000a0au,0x0u,0x0u,0x2800u,0x8000280u,0x0u,0x0u,0x0u,0x0u,0x4008040u,0x500u,0x1000050u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x80000000u,0x2800u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}};
            else
                operation=DsromS81PrefixOperation{2612,2,"c60f0f4efd0f3401b2ecb779c588bc675143deb557a953395563fa563c3c05e5",{0x2u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x10u,0xau,0xf0u,0x400000u,0x0u,0xc0000000u,0x4000a10u,0x0u,0x0u,0x2800u,0x8000280u,0x0u,0x0u,0x0u,0x0u,0x4008040u,0x500u,0x1000050u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x80000000u,0x2800u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}};
            output_spans={{20480,20480}}; // literal four-copy T output
        }
        // Goodall: optional SIM_ONLY computed prefix uses THIS bank's actual
        // tagged VM writes/ACKs; never admits a lease directly from files.
        if(const char* input=std::getenv("DSROM_S81_NATIVE_L20_PRE_I75_INPUT")) {
            require(pc&&std::string(pc)=="76"&&*input,
                    "pre-I75 inputs require native PC76; PC142 needs its own actual boundary");
            bank.entry().install_sim_only_pre_i75(input);
        }
        if(!mutable_h)bank.publication().enroll_literal(operation.index,output_spans);
        su=dsrom_s81_bind_minimum_su256(r,ID,bank.publication(),bank.io(),bank.tags());
    }
    void attach() {
        require(!attached,"L20 I0 factory attached twice");
        runtime.participants.push_back(bank.bank_participant());
        runtime.participants.push_back(bank.entry_participant());
        // Control samples ready before the sole native SU rising evaluation.
        // No private tick, simulator output injection or assumed write ACK.
        runtime.participants.push_back({"source-L20-I0-native-SU",
          [this](const auto& result) {
            go=false;
            if(started&&!accepted)go=bank.inputs_visible()&&su.inputs_ready(operation)&&su.ready()&&
                (!mutable_h||(su.idle()&&bank.native_target().mutable_write_drained()));
            su.drive(operation,go);su.participant.prepare(result);
          },
          [this](bool released) {
            if(!released)require(!started&&!accepted,"reset erases accepted L20 I0 work");
            else if(go) {
                require(!accepted&&su.ready(),"L20 I0 lost actual native acceptance");
                if(mutable_h) {
                    // inputs_ready has captured every operand through SourceIo;
                    // idle excludes native/staged SU output debt, and the same
                    // target excludes outstanding reads and real ACK debt.
                    const bool readers_drained=su.idle()&&bank.native_target().mutable_write_drained();
                    bank.admit_mutable_h_writer(operation.index,output_spans,
                        go&&su.ready(),readers_drained);
                }else bank.publication().begin(ID,operation.index);
                accepted=true;first=runtime.cycle();
            }
            su.participant.rising(released);
          },
          [this](bool released){su.participant.falling(released);},
          [this](){return bank.fault()||su.participant.fault();}});
        auto self=shared_from_this();
        runtime.publication_ready=[self](auto id){return id==ID&&!self->bank.fault()&&!self->su.participant.fault();};
        runtime.publication_drained=[self](auto id){return id==ID&&self->finished;};
        attached=true;
    }
    void start() {
        require(attached&&!started&&bank.inputs_visible(),"L20 I0 start before actual seeded VM visibility");
        started=true;
    }
    void advance() {
        if(!accepted||finished)return;
        require(!bank.fault()&&!su.participant.fault(),"L20 I0 native failure");
        if(!su.idle()||!bank.publication().complete(ID,operation.index))return;
        if(h_successor) {
            // Native SU idle includes its output queue/ACK drain. Re-read the
            // published T through the same SourceIo on the next admission;
            // do not carry staged operands or source GO into another literal.
            require(bank.native_target().mutable_write_drained()&&
                    bank.io().span_lease(ID,20480,20480),
                    "H successor lacks its native same-bank T publication");
            su.drive(operation,false);
            operation=*h_successor;h_successor.reset();
            output_spans={{0,20480},{40960,1}};
            output_address=0;mutable_h=true;accepted=false;go=false;
            return;
        }
        // Read back ONLY the published native result through the same held
        // bank request path. This is the operand for the following operation.
        output=bank.io().read_word(ID,output_address);
        if(output){finished=true;last=runtime.cycle();}
    }
    void write(const std::string& directory) {
        require(finished&&output&&first>=0&&last>=first,"L20 I0 has no terminal native operand");
        const auto pc=selected_pc;
        std::ofstream file(directory+"/native_L20_I"+std::to_string(pc)+".tsv",std::ios::out|std::ios::app);
        require(bool(file),"L20 I0 measurement output unavailable");
        file<<"scope\tposition\trank\tproducer\taccepted_cycle\tvisible_read_cycle\taddress\traw32\n"
            <<"L20.I"<<pc<<".native-component\t1048575\t"<<runtime.rank<<'\t'<<operation.index
            <<'\t'<<first<<'\t'<<last<<'\t'<<output_address<<'\t'<<*output<<'\n';
        require(bool(file),"L20 I0 measurement write failed");
    }
    static void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
};

// Selected next minimum component: actual I36 encoding/publication followed by
// the unchanged canonical I44 full scan. Boundary inputs are produced by the
// current SIM_ONLY prefix, never comparison/reference values or current-key
// checkpoint images. Both engines read those values through the real bank.
struct SourceL20Index : std::enable_shared_from_this<SourceL20Index> {
    DsromS81MinimumRuntime& runtime;
    DsromS81MinimumL20Bank bank;
    DsromS81NativeSuPorts su_ports;
    DsromS81PrefixNativeEngine su,scan;
    std::shared_ptr<NativeIndexHbm> backend;
    std::shared_ptr<L20IndexWriter> writer;
    std::shared_ptr<VDsromS81IndexScorer> scorer;
    std::shared_ptr<DsromS81IndexSourceL20<VDsromS81IndexScorer>> index;
    DsromS81PrefixOperation key_operation=DsromS81PrefixOperation{2507,2,"436e442bdf1b4743ac79abc55ab08892561afe7bfdf29803d631ed531180c072",{0x22u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x40000004u,0x80000000u,0x5c4u,0x400000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0xc000000u,0x0u,0x0u,0x1000000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x80000000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}};
    DsromS81PrefixOperation scan_operation=DsromS81PrefixOperation{2515,1,"901ec7b483f2be4d78aa2165831f719a8b748991b026b9c8c5cf772c6ecc85f1",{0x31u,0x10000000u,0x400u,0x10000u,0x80u,0x0u,0xc0d00u,0x647au,0xaa400001u,0x40u,0x800u,0x2cu,0x0u,0x4002u,0x8u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x191c08u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}};
    struct Input {unsigned producer;uint32_t base;std::vector<uint32_t> data;};
    std::vector<Input> inputs;
    std::vector<uint32_t> native_scores=std::vector<uint32_t>(262144);
    size_t input=0,offset=0;
    bool started=false,loading=false,held=false,offered=false,attached=false;
    bool key_accepted=false,scan_accepted=false,finished=false,key_go=false,scan_go=false;
    S81EmbeddingOutput out{};
    unsigned count=0;
    long key_first=-1,key_visible=-1,scan_first=-1,last=-1;
    static void require(bool v,const char* message){if(!v)throw std::runtime_error(message);}
    template<class Wide> static uint32_t bits(const Wide& data,unsigned first,unsigned width) {
        uint32_t value=0;
        for(unsigned j=0;j<width;++j)value|=((data[(first+j)/32]>>((first+j)%32))&1u)<<j;
        return value;
    }
    static std::vector<uint32_t> load(const std::string& file,size_t words) {
        std::ifstream f(file,std::ios::binary);
        require(bool(f),"actual SIM_ONLY-produced index operand file missing");
        std::vector<unsigned char> bytes(words*4);
        f.read(reinterpret_cast<char*>(bytes.data()),bytes.size());
        require(size_t(f.gcount())==bytes.size()&&f.peek()==std::char_traits<char>::eof(),
                "source index operand extent differs");
        std::vector<uint32_t> data(words);
        for(size_t j=0;j<words;++j)data[j]=uint32_t(bytes[4*j])|(uint32_t(bytes[4*j+1])<<8)|
            (uint32_t(bytes[4*j+2])<<16)|(uint32_t(bytes[4*j+3])<<24);
        return data; // opaque actual source VM bits, no FP conversion
    }
    SourceL20Index(DsromS81MinimumRuntime& r,std::shared_ptr<Vnative_vm> vm)
      :runtime(r),bank(r,ID,std::move(vm),dsrom_s81_bind_minimum_source_tags(r,ID)) {
        require(r.rank==3&&!r.identity,"current global key belongs to native rank3 before cold admission");
        const char* directory=std::getenv("DSROM_S81_NATIVE_L20_INDEX_INPUT");
        require(directory&&*directory,"actual produced I35/I41/I43 operand directory required");
        const std::string dir=directory;
        inputs={{2506,94496,load(dir+"/I35.IKQ.u32",128)},
                {2512,98720,load(dir+"/I41.IQQ.u32",4096)},
                {2514,102848,load(dir+"/I43.WTS.u32",32)}};
        for(const auto& i:inputs)bank.publication().enroll_literal(i.producer,{{i.base,uint32_t(i.data.size())}});
        bank.publication().enroll_literal(key_operation.index,{}); // KV output, not a VM extent
        bank.publication().enroll_literal(scan_operation.index,{{102880,262144}});
        su=dsrom_s81_bind_minimum_su256(r,ID,bank.publication(),bank.io(),bank.tags(),su_ports);
        // Actual target context fixes only selectors needed by these two
        // literal operations. Unknown selectors remain unavailable.
        su_ports.actual_dynamic=[](unsigned selector)->std::optional<uint32_t> {
            if(selector==4)return 1048575;
            if(selector==36)return 262144; // source SC1=ceil((POS+1)/TP4)
            if(selector==42)return 16384;  // source ceil(SC1/16)
            return std::nullopt;
        };
        backend=std::make_shared<NativeIndexHbm>(r,"native_L20_rank3_index_backend");
        backend->preload_ring(dir+"/ring_prior_r3");
        writer=std::make_shared<L20IndexWriter>(r,ID,su_ports,backend,key_operation);
        scorer=std::make_shared<VDsromS81IndexScorer>(r.context,"native_L20_rank3_fullscan");
        backend->bind_wiring([this](VDsromS81IndexHbm& m) {
            // Record coordinates alone map GLOBAL POS to rank3's released
            // local quarter. All native encoded bits retain their source.
            writer->join_backend(m);
            m.r_v=scorer->h_req_v;m.r_addr=scorer->h_req_addr;m.r_len=scorer->h_req_len;
            m.r_tag=scorer->h_req_tag;m.r_rsp_rdy=scorer->h_rsp_rdy;m.eval();
            scorer->h_req_rdy=m.r_rdy;scorer->h_rsp_v=m.r_rsp_v;
            scorer->h_rsp_tag=m.r_rsp_tag;scorer->h_rsp_beat=m.r_rsp_beat;
            scorer->h_rsp_data=m.r_rsp_data;scorer->eval();
        });
        index=std::make_shared<DsromS81IndexSourceL20<VDsromS81IndexScorer>>(
            r,ID,bank.publication(),bank.io(),scorer,scan_operation,su_ports.actual_dynamic,
            [this](auto&){backend->join_ports();},
            [this](){return writer->source_idle()&&backend->current_committed(262143);},true);
        scan=dsrom_s81_bind_index_source_l20(index);
    }
    bool inputs_visible() {
        if(input!=inputs.size()||held)return false;
        for(const auto& i:inputs)
            if(!bank.publication().complete(ID,i.producer)||!bank.io().span_lease(ID,i.base,i.data.size()))return false;
        return !bank.fault();
    }
    void attach() {
        require(!attached,"index factory attached twice");
        runtime.participants.push_back(bank.bank_participant());
        runtime.participants.push_back({"source-L20-I36-I44-native-control",
          [this](const auto& result) {
            key_go=scan_go=false;
            if(started&&!key_accepted)key_go=su.inputs_ready(key_operation)&&su.ready();
            if(started&&key_accepted&&!scan_accepted&&writer->source_idle()&&backend->current_committed(262143)) {
                if(key_visible<0)key_visible=runtime.cycle();
                scan_go=scan.inputs_ready(scan_operation)&&scan.ready();
            }
            su.drive(key_operation,key_go);scan.drive(scan_operation,scan_go);
            su.participant.prepare(result);scan.participant.prepare(result);
          },
          [this](bool released) {
            if(!released)require(!started&&!key_accepted&&!scan_accepted,"reset erases native index work");
            if(released&&key_go){bank.publication().begin(ID,key_operation.index);key_accepted=true;key_first=runtime.cycle();}
            if(released&&scan_go){bank.publication().begin(ID,scan_operation.index);scan_accepted=true;scan_first=runtime.cycle();}
            su.participant.rising(released);scan.participant.rising(released);
            // The source adapter just validated/captured these same native
            // registered outputs. Persist their raw bits for the existing
            // continuation only; no oracle or second publication witness.
            if(released&&scan_accepted)for(unsigned port=0;port<8;++port)
                if((scorer->o_we>>port)&1u) {
                    const auto word=bits(scorer->o_addr,30*port,30);
                    for(unsigned lane=0;lane<16;++lane)
                        if(bits(scorer->o_mask,16*port+lane,1))
                            native_scores.at(word*16+lane-102880)=scorer->o_data[port*16+lane];
                }
          },
          [this](bool released){su.participant.falling(released);scan.participant.falling(released);},
          [this](){return bank.fault()||su.participant.fault()||scan.participant.fault();}});
        runtime.participants.push_back(writer->participant());
        runtime.participants.push_back(backend->participant());
        auto self=shared_from_this();
        runtime.publication_ready=[self](auto id){return id==ID&&!self->bank.fault()&&!self->writer->fault();};
        runtime.publication_drained=[self](auto id){return id==ID&&self->finished;};
        attached=true;
    }
    void initialize() {
        require(attached&&!loading&&runtime.identity&&*runtime.identity==ID,"index input publication before cold admission");
        loading=true;bank.publication().begin(ID,inputs.front().producer);
    }
    void start(){require(inputs_visible()&&!started,"index GO before actual boundary-input visibility");started=true;}
    void advance() {
        if(loading&&input<inputs.size()) {
            const auto& i=inputs[input];
            if(!held) {
                count=std::min<size_t>(16,i.data.size()-offset);
                out={};out.vm_valid=1;out.vm_identity=ID;out.vm_address=i.base+offset;
                for(unsigned lane=0;lane<count;++lane) {
                    out.vm_data[lane]=i.data[offset+lane];
                    auto command=dsrom_s81_reserve_native_scalar_tag(runtime,ID,i.producer,out.vm_address+lane,out.vm_data[lane]);
                    bank.publication().native_scalar(i.producer,command,true);
                }
                held=true;offered=false;
            }
            if(!offered){offered=bank.io().offer(out,count);return;}
            if(!bank.io().visible(out,count))return;
            offset+=count;held=offered=false;
            if(offset==i.data.size()) {
                require(bank.publication().complete(ID,i.producer),"boundary operand has unmatched native ACK");
                ++input;offset=0;
                if(input<inputs.size())bank.publication().begin(ID,inputs[input].producer);
            }
        }
        if(scan_accepted&&scan.idle()&&bank.publication().complete(ID,scan_operation.index)&&
           writer->source_idle()&&backend->current_committed(262143)&&backend->drained()) {
            finished=true;if(last<0)last=runtime.cycle();
        }
    }
    void write(const std::string& directory)const {
        require(finished&&key_first>=0&&key_visible>=key_first&&scan_first>=key_visible&&last>=scan_first,
                "native I36/I44 has no completed source interval");
        std::ofstream f(directory+"/native_L20_index.tsv",std::ios::out|std::ios::app);
        require(bool(f),"index output unavailable");
        f<<"scope\trank\tposition\tkey_accept\tkey_visible\tscan_accept\tterminal\trequested_bytes\tdelivered_bytes\n"
         <<"I36.I44.native-SIM_ONLY-boundary-inputs\t3\t1048575\t"<<key_first<<'\t'<<key_visible<<'\t'
         <<scan_first<<'\t'<<last<<'\t'<<index->accepted_request_bytes()<<'\t'<<index->accepted_response_bytes()<<'\n';
        require(bool(f),"index output write failed");
        const std::string file=directory+"/native_L20_I44.u32";
        require(!std::ifstream(file).good(),"preserve existing native score dump");
        std::ofstream raw(file,std::ios::out|std::ios::binary);
        require(bool(raw),"native score output unavailable");
        for(uint32_t value:native_scores) {
            const char bytes[]={char(value),char(value>>8),char(value>>16),char(value>>24)};
            raw.write(bytes,4);
        }
        require(bool(raw),"native score output write failed");
    }
};
}

DsromS81MinimumSourcePlan dsrom_s81_bind_minimum_source(
    DsromS81MinimumRuntime& runtime,std::shared_ptr<Vnative_vm> vm) {
    const char* native_end=std::getenv("DSROM_S81_NATIVE_HEAD_END");
    if(native_end&&std::string(native_end)=="1")
        throw std::runtime_error("native HEAD-END requires the typed actual-core source entry");
    const char* native_index=std::getenv("DSROM_S81_NATIVE_L20_INDEX");
    if(native_index&&std::string(native_index)=="1") {
        auto source=std::make_shared<SourceL20Index>(runtime,std::move(vm));
        DsromS81MinimumSourcePlan plan;
        plan.identity=ID;plan.token=16754;plan.position=1048575;
        plan.attach_seeded=[source](){source->attach();};
        plan.initialize_seeded=[source](){source->initialize();};
        plan.seeded_inputs_visible=[source](){source->advance();return source->inputs_visible();};
        plan.begin_prefix=[source](){source->start();};
        plan.advance=[source](){source->advance();};
        plan.complete=[source](){return source->finished;};
        plan.write_measurements=[source](const auto& directory){source->write(directory);};
        return plan;
    }
    const char* l20=std::getenv("DSROM_S81_NATIVE_L20_I0");
    if(l20&&std::string(l20)=="1") {
        auto source=std::make_shared<SourceL20I0>(runtime,std::move(vm));
        DsromS81MinimumSourcePlan plan;
        plan.identity=ID;plan.token=16754;plan.position=1048575;
        plan.attach_seeded=[source](){source->attach();};
        plan.initialize_seeded=[source](){source->bank.initialize();};
        plan.seeded_inputs_visible=[source](){return source->bank.inputs_visible();};
        plan.begin_prefix=[source](){source->start();};
        plan.advance=[source](){source->advance();};
        plan.complete=[source](){return source->finished;};
        plan.write_measurements=[source](const auto& directory){source->write(directory);};
        return plan;
    }
    auto source=std::make_shared<Source>(runtime,std::move(vm));
    DsromS81MinimumSourcePlan plan;
    plan.identity=ID;plan.embedding_library="/tmp/dsrom-s81-embedding-8f65ab021/libdsrom_s81_embedding.so";
    plan.embedding_socket="/tmp/dsrom-s81-embedding-cbe13bd57.sock";
    plan.embedding_sink=source->target->sink();
    plan.attach=[source](auto& embedding){source->attach(embedding);};
    plan.begin_prefix=[source](){source->begin();};
    plan.advance=[source](){source->advance();};
    plan.complete=[source](){return source->complete();};
    return plan;
}

#ifdef DSROM_S81_HEAD_WINNER_BINDING_HEADER
DsromS81MinimumSourcePlan dsrom_s81_bind_minimum_source(
    DsromS81MinimumRuntime& runtime,std::shared_ptr<Vnative_vm> vm,
    std::shared_ptr<VDsromS81CoreEnd> actual_core) {
    const char* selected=std::getenv("DSROM_S81_NATIVE_HEAD_END");
    if(!selected||std::string(selected)!="1")
        throw std::runtime_error("typed native HEAD-END factory requires explicit selection");
    auto source=std::make_shared<SourceHeadEnd>(runtime,std::move(vm),std::move(actual_core));
    DsromS81MinimumSourcePlan plan;plan.identity=ID;plan.token=16754;plan.position=1048575;
    plan.attach_seeded=[source](){source->attach();};
    plan.initialize_seeded=[source](){source->initialize();};
    plan.seeded_inputs_visible=[source](){return source->inputs_visible();};
    plan.begin_prefix=[source](){source->start();};
    plan.advance=[source](){source->advance();};
    plan.complete=[source](){return source->complete();};
    plan.write_measurements=[source](const auto&){
        Source::require(source->consumed&&source->publications_drained(),"HEAD-END measurements before actual consumer");};
    return plan;
}
#endif

#ifdef DSROM_S81_L20_KV_ENCLOSING
// Borrow the already constructed native TP4 factory. It owns the descriptor,
// generation, history and actual transport bindings; this function supplies
// only the existing caller's literal engine selection and shared-edge clocks.
void dsrom_s81_join_minimum_l20_kv_source(
    std::shared_ptr<dsrom_s81_minimum::L20KvFactory> factory,
    const std::array<DsromS81MinimumRuntime*,4>& ranks,
    std::array<DsromS81PrefixNativeEngine,4>& su,
    std::array<DsromS81PrefixNativeEngine,4>& me) {
    using Engine=DsromS81PrefixNativeEngine;
    auto valid=[](const Engine& e){return !e.participant.name.empty()&&
        e.participant.prepare&&e.participant.rising&&e.participant.falling&&
        e.participant.fault&&e.ready&&e.idle&&e.inputs_ready&&e.drive;};
    if(!factory)throw std::runtime_error("native L20 KV factory absent");
    for(unsigned i=0;i<4;++i) {
        if(!ranks[i]||ranks[i]->identity||ranks[i]->rank!=int(i)||ranks[i]->stage!=37||
           !valid(su[i])||!valid(me[i])||
           me[i].participant.name.find("l20-source-selected-ME-rank")==0)
            throw std::runtime_error("L20 KV enclosing join requires all four cold actual engines");
        if(i&&ranks[i]->context!=ranks[0]->context)
            throw std::runtime_error("L20 KV enclosing ranks must share one context");
    }
    // One existing ME slot dispatches literal ATT operations; the retained
    // scorer/weight-ME engine remains the other branch, with its own leases.
    struct Dispatch {
        Engine previous,attention;
        std::vector<DsromS81MinimumParticipant> auxiliaries;
        std::shared_ptr<dsrom_s81_minimum::L20KvFactory> owner;
        std::optional<DsromS81PrefixOperation> held;
        bool selected=false;
        static bool is_attention(const DsromS81PrefixOperation& op) {
            const char* sha=op.index==2526?
                "00bb7b6a8b1a67526169d39c1f5b0954d2dbc600f330a42af48d1c0d7c46bc65":
                op.index==2534?
                "6124df21d8de509ccbb8e0f114d2ed9776a4316dd810e92c35c0a07acfb9083a":nullptr;
            if(!sha)return false;
            if(op.unit!=1||!op.template_sha256||std::string(op.template_sha256)!=sha)
                throw std::runtime_error("L20 QK/PV literal identity changed");
            return true;
        }
        Engine& active(){return selected?attention:previous;}
        bool inputs(const DsromS81PrefixOperation& op) {
            if(op.unit!=1)throw std::runtime_error("L20 ME dispatch received another ISA unit");
            const bool next=is_attention(op);
            if(!held||held->index!=op.index) {
                if(held) {
                    if(!active().idle())return false;
                    active().drive(*held,false);
                }
                selected=next;held=op;
            }else if(held->instruction!=op.instruction||held->unit!=op.unit)
                throw std::runtime_error("L20 held ME literal changed");
            return active().inputs_ready(op);
        }
        void drive(const DsromS81PrefixOperation& op,bool go) {
            if(go&&(!held||held->index!=op.index||held->instruction!=op.instruction))
                throw std::runtime_error("L20 ME GO without actual held operand admission");
            // Generic prefix withdraws GO with its next op before inputs_ready.
            // Preserve the old literal during that withdrawal, not new operands.
            if(held)active().drive(*held,go);
            else if(go)throw std::runtime_error("L20 ME missing source operation");
        }
    };
    auto participants=factory->participants();
    const unsigned shared=participants.size()==21?1:0;
    if(participants.size()!=20+shared || (shared&&participants[0].name!="SIM_ONLY-existing-CKV-TP4-11-142-II2"))
        throw std::runtime_error("L20 native KV participant census changed");
    for(unsigned i=0;i<4;++i)for(unsigned j=0;j<5;++j) {
        const auto& p=participants[shared+5*i+j];
        if(p.name.empty()||!p.prepare||!p.rising||!p.falling||!p.fault)
            throw std::runtime_error("L20 native KV participant incomplete");
        for(const auto& old:ranks[i]->participants)if(old.name==p.name)
            throw std::runtime_error("L20 KV participant already enrolled");
    }
    std::array<Engine,4> next_su,next_me;
    for(unsigned i=0;i<4;++i) {
        next_su[i]=factory->bind_su(i,su[i]);
        auto d=std::make_shared<Dispatch>();d->previous=me[i];
        d->attention=factory->attention(i);d->owner=factory;
        if(!valid(d->attention))throw std::runtime_error("actual packed640 attention engine missing");
        if(i==0&&shared)d->auxiliaries.push_back(std::move(participants[0]));
        for(unsigned j=0;j<5;++j)d->auxiliaries.push_back(std::move(participants[shared+5*i+j]));
        // Nest, rather than separately enroll, the five existing participants
        // so provider OLD snapshots precede endpoint cut prepare on every edge.
        // The caller enrolls this returned ME slot once with its other engines.
        next_me[i]={{"l20-source-selected-ME-rank"+std::to_string(i),
            [d](const auto& result){
                d->previous.participant.prepare(result);
                for(auto& p:d->auxiliaries)
                    if(p.name=="SIM_ONLY-existing-CKV-TP4-11-142-II2")p.prepare(result);
                d->attention.participant.prepare(result);
                for(auto& p:d->auxiliaries)
                    if(p.name!="SIM_ONLY-existing-CKV-TP4-11-142-II2")p.prepare(result);
            },
            [d](bool released){
                d->previous.participant.rising(released);d->attention.participant.rising(released);
                for(auto& p:d->auxiliaries)p.rising(released);
            },
            [d](bool released){
                d->previous.participant.falling(released);d->attention.participant.falling(released);
                for(auto& p:d->auxiliaries)p.falling(released);
            },
            [d](){
                if(d->previous.participant.fault()||d->attention.participant.fault())return true;
                for(auto& p:d->auxiliaries)if(p.fault())return true;
                return false;
            }},
            [d](){return d->held&&d->active().ready();},
            [d](){return d->active().idle();},
            [d](const auto& op){return d->inputs(op);},
            [d](const auto& op,bool go){d->drive(op,go);}};
    }
    su=std::move(next_su);me=std::move(next_me);

}
std::shared_ptr<dsrom_s81_minimum::L20KvFactory> dsrom_s81_join_minimum_l20_kv_source(
    std::array<dsrom_s81_minimum::L20KvRankBinding,4> bindings,
    std::function<void(const std::array<dsrom_s81_minimum::L20NativeCkv,4>&)> transport,
    std::array<DsromS81PrefixNativeEngine,4>& su,
    std::array<DsromS81PrefixNativeEngine,4>& me) {
    std::array<DsromS81MinimumRuntime*,4> runtimes{};
    for(unsigned i=0;i<4;++i)runtimes[i]=bindings[i].runtime;
    // Missing lifecycle/transport may be selected only by Noether's explicit
    // SIM_ONLY source opt-in inside the existing factory. Native IO/ACKs and
    // source-published selected IDs are mandatory in either selection.
    auto factory=std::make_shared<dsrom_s81_minimum::L20KvFactory>(
        std::move(bindings),std::move(transport),true);
    dsrom_s81_join_minimum_l20_kv_source(factory,runtimes,su,me);
    return factory; // caller uses the actual factory drain for source terminal
}

#endif
