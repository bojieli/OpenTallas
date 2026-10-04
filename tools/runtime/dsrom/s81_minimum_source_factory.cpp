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
#include <cstdlib>
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
// The opt-in path uses the existing seeded entry, bank and publication owner.
struct SourceL20I0 : std::enable_shared_from_this<SourceL20I0> {
    DsromS81MinimumRuntime& runtime;
    DsromS81MinimumL20Bank bank;
    DsromS81PrefixNativeEngine su;
    DsromS81PrefixOperation operation=DsromS81PrefixOperation{2470,2,"0a8042d53254c972480a5c7c05cf676d0c5e3cbea44e456aa5537b16ce93e622",{0x2u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x800004u,0x0u,0x280u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x4050140u,0xa02u,0x0u,0x0u,0x0u,0x0u,0x8d40000u,0x3c79ca1u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}};
    bool attached=false,started=false,accepted=false,go=false,finished=false;
    long first=-1,last=-1;
    std::optional<uint32_t> output;
    SourceL20I0(DsromS81MinimumRuntime& r,std::shared_ptr<Vnative_vm> vm)
      :runtime(r),bank(r,ID,std::move(vm),dsrom_s81_bind_minimum_source_tags(r,ID)) {
        bank.publication().enroll_literal(operation.index,{{40992,1}});
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
            if(started&&!accepted)go=bank.inputs_visible()&&su.inputs_ready(operation)&&su.ready();
            su.drive(operation,go);su.participant.prepare(result);
          },
          [this](bool released) {
            if(!released)require(!started&&!accepted,"reset erases accepted L20 I0 work");
            else if(go) {
                require(!accepted&&su.ready(),"L20 I0 lost actual native acceptance");
                bank.publication().begin(ID,operation.index);accepted=true;first=runtime.cycle();
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
        // Read back ONLY the published native result through the same held
        // bank request path. This is the operand for the following operation.
        output=bank.io().read_word(ID,40992);
        if(output){finished=true;last=runtime.cycle();}
    }
    void write(const std::string& directory) {
        require(finished&&output&&first>=0&&last>=first,"L20 I0 has no terminal native operand");
        std::ofstream file(directory+"/native_L20_I0.tsv",std::ios::out|std::ios::app);
        require(bool(file),"L20 I0 measurement output unavailable");
        file<<"scope\tposition\trank\tproducer\taccepted_cycle\tvisible_read_cycle\taddress\traw32\n"
            <<"L20.I0.native-component\t1048575\t"<<runtime.rank<<'\t'<<operation.index
            <<'\t'<<first<<'\t'<<last<<"\t40992\t"<<*output<<'\n';
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
        backend->preload_ring("/tmp/opentallas-L20-RING-priorhistory-20261004-r1/r3");
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
