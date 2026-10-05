#include "s81_minimum_runtime.hpp"
#include "s81_minimum_pair_source.hpp"
#include "dsrom_s81_rom_client.hpp"
#include "Vpq.h"
#include "Vpb.h"
#include "svdpi.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <filesystem>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <unordered_map>

namespace {
struct PairMem {
    int stage,rank,pair;std::vector<uint64_t> cfg;
    DsromS81MinimumRuntime* runtime=nullptr;
    std::function<bool()> source_selected;
    std::function<std::array<uint32_t,9>(unsigned,unsigned)> source_rom;
    std::function<uint64_t(unsigned)> source_cfg;
};
PairMem* registering=nullptr;
std::unordered_map<const void*,std::pair<PairMem*,int>> rom_scopes;
std::unordered_map<const void*,PairMem*> cfg_scopes;

std::vector<uint64_t> cfg_words(const std::string& path) {
    std::ifstream file(path);
    if(!file)throw std::runtime_error("actual pair configuration source required");
    std::vector<uint64_t> words;std::string line;
    while(std::getline(file,line)) {
        if(line.empty())continue;
        size_t consumed=0;auto word=std::stoull(line,&consumed,16);
        if(line.find_first_not_of(" \r\t",consumed)!=std::string::npos || word>>48)
            throw std::runtime_error("source configuration is not a native 48-bit word");
        words.push_back(word);
    }
    if(words.empty() || words.size()>25u*1024 || words.size()%25)
        throw std::runtime_error("native CW25/PHW10 configuration extent");
    return words;
}
void owner_bounds(int stage,int rank,int pair) {
    if(stage<0||stage>=81||rank<0||rank>=4||pair<0||pair>=2417)
        throw std::runtime_error("native S81 stage/rank/pair owner bounds");
}
struct PairBase {
    virtual ~PairBase()=default;
    virtual void drive(const DsromS81PairDrive&)=0;
    virtual DsromS81PairResult result()=0;
    virtual void eval(bool clk,bool rst)=0;
};
template<class Model> struct NativePair:PairBase {
    Model model;
    explicit NativePair(VerilatedContext* ctx):model(ctx,"selected_pair") {}
    void drive(const DsromS81PairDrive& p) override {
        if(p.cfg_go>1||p.go>1||p.go_bf>1||p.xs_v>1||p.xb_v>1||p.cfg_ph>=1024||p.cfg_np>=8||p.xs_e0>=1024||p.xs_e1>=1024 ||
           p.xs_b>=8||p.xs_sv>=4||p.xs_pos>=8||p.xb_pos>=8||p.xb_b>=8||p.xb_sv>=16)
            throw std::runtime_error("native pair broadcast port bounds");
        model.cfg_go=p.cfg_go;model.cfg_ph=p.cfg_ph;model.cfg_np=p.cfg_np;
        model.go=p.go;model.go_bf=p.go_bf;model.xs_v=p.xs_v;
        model.xs_p=p.xs_p;model.xs_b=p.xs_b;model.xs_sv=p.xs_sv;
        model.xs_e0=p.xs_e0;model.xs_e1=p.xs_e1;model.xs_pos=p.xs_pos;
        model.xb_pos=p.xb_pos;model.xb_v=p.xb_v;model.xb_b=p.xb_b;
        model.xb_sv=p.xb_sv;model.xb_u=p.xb_u;
        for(int i=0;i<8;i++){model.xs_q0[i]=p.xs_q0[i];model.xs_q1[i]=p.xs_q1[i];}
        for(int i=0;i<32;i++)model.xb_d[i]=p.xb_d[i];
    }
    DsromS81PairResult result() override {
        return {model.pv,model.perr,model.ppos,model.pseg,model.pnseg,model.prow,
                model.pval,bool(model.busy),bool(model.quiet),bool(model.fault)};
    }
    void eval(bool clk,bool rst) override {model.clk=clk;model.rst_n=rst;model.eval();}
};
}

void dsrom_s81_minimum::bind_native_pair_source(
    DsromS81MinimumRuntime& runtime,std::function<bool()> selected,
    std::function<std::array<uint32_t,9>(unsigned,unsigned)> rom,
    std::function<uint64_t(unsigned)> cfg) {
    if(!selected||!rom||!cfg||!runtime.cycle||runtime.cycle()!=0||runtime.identity)
        throw std::runtime_error("native pair source must bind before shared cold/context admission");
    PairMem* memory=nullptr;
    for(const auto& scope:cfg_scopes)if(scope.second->runtime==&runtime) {
        if(memory&&memory!=scope.second)
            throw std::runtime_error("ambiguous native pair source owner");
        memory=scope.second;
    }
    if(!memory||memory->source_selected)
        throw std::runtime_error("missing or already bound native pair source owner");
    memory->source_selected=std::move(selected);
    memory->source_rom=std::move(rom);memory->source_cfg=std::move(cfg);
}

extern "C" void v41rt_rom_register(const char* instance) {
    if(!registering)throw std::runtime_error("native ROM registration outside pair construction");
    int bank=instance&&*instance&&instance[strlen(instance)-1]=='b';
    rom_scopes[svGetScope()]={registering,bank};
}
extern "C" void v41rt_cfg_register() {
    if(!registering)throw std::runtime_error("native CFG registration outside pair construction");
    cfg_scopes[svGetScope()]=registering;
}
extern "C" void v41rt_rom_read(int address,svBitVecVal* q) {
    const auto& binding=rom_scopes.at(svGetScope());const auto& owner=*binding.first;
    if(address<0)throw std::runtime_error("negative native ROM source address");
    const auto word=owner.source_selected&&owner.source_selected()
        ?owner.source_rom(binding.second,unsigned(address))
        :dsrom_s81::read(owner.stage,owner.rank,owner.pair,binding.second,address);
    if(word[8]>>18)throw std::runtime_error("native ROM source exceeds raw274 word");
    for(int i=0;i<9;i++)q[i]=word[i];
}
extern "C" long long v41rt_cfg_read(int address) {
    const auto& owner=*cfg_scopes.at(svGetScope());
    if(address<0)throw std::runtime_error("negative native CFG source address");
    if(owner.source_selected&&owner.source_selected()) {
        auto word=owner.source_cfg(unsigned(address));
        if(word>>48)throw std::runtime_error("native selected CFG exceeds word48");
        return static_cast<long long>(word);
    }
    const auto& cfg=owner.cfg;
    if(address<0||size_t(address)>=cfg.size())throw std::runtime_error("unowned native CFG phase/address");
    return static_cast<long long>(cfg[address]);
}

int main(int argc,char** argv) {
    if(argc<9) {
        fprintf(stderr,"usage: minimum_element pq|pb STAGE RANK PAIR CFG_HEX OUTPUT SOURCE_CALLER.so|- ROM_SOCKET [+OT_ROM_DIR=DIR]\n");
        return 2;
    }
    for(int i=9;i<argc;++i) {
        if(i!=9||std::string(argv[i]).rfind("+OT_ROM_DIR=",0)!=0||!argv[i][12]) {
            fprintf(stderr,"unsupported or empty actual native model plusarg\n");
            return 2;
        }
    }
    // Keep the source image loaded until every retained participant closure
    // has been destroyed. No unload before native model/observer destruction.
    // '-' selects the actual source factory/entry linked into this executable.
    // This keeps retained non-PIC native return archives in their host image.
    void* caller=dlopen(std::string(argv[7])=="-"?nullptr:argv[7],RTLD_NOW|RTLD_LOCAL);
    if(!caller){fprintf(stderr,"actual minimum source caller: %s\n",dlerror());return 2;}
    auto source_main=reinterpret_cast<int(*)(DsromS81MinimumRuntime&,const char*)>(
        dlsym(caller,"dsrom_s81_minimum_source_main"));
    if(!source_main){fprintf(stderr,"actual minimum source entry missing\n");return 2;}
    try {
        bool bf=std::string(argv[1])=="pb";
        if(!bf&&std::string(argv[1])!="pq")throw std::runtime_error("actual PQ/PB model kind required");
        PairMem memory{std::stoi(argv[2]),std::stoi(argv[3]),std::stoi(argv[4]),cfg_words(argv[5]),nullptr,{},{},{}};
        owner_bounds(memory.stage,memory.rank,memory.pair);
        if(setenv("DSROM_S81_ROM_SOCKET",argv[8],1))throw std::runtime_error("native ROM socket binding failed");
        VerilatedContext ctx;ctx.commandArgs(argc,argv);ctx.randReset(0);
        std::unique_ptr<PairBase> native;
        registering=&memory;
        if(bf)native.reset(new NativePair<Vpb>(&ctx));else native.reset(new NativePair<Vpq>(&ctx));
        native->drive({});native->eval(false,false);native->eval(true,false);native->eval(false,false);
        registering=nullptr;
        DsromS81MinimumRuntime runtime{};
        memory.runtime=&runtime;
        runtime.stage=memory.stage;runtime.rank=memory.rank;runtime.pair=memory.pair;
        runtime.bf16=bf;runtime.context=&ctx;
        long cycle=0;uint64_t accepted_go=0;bool started=false;
        DsromS81PairDrive driven{};
        runtime.drive=[&](const DsromS81PairDrive& p){driven=p;native->drive(p);};
        runtime.result=[&](){return native->result();};runtime.cycle=[&](){return cycle;};
        runtime.bind_context=[&](uint64_t identity){
            if(!started)throw std::runtime_error("shared cold start required before context admission");
            if(identity>=(uint64_t(1)<<47)||!runtime.publication_drained||!runtime.publication_ready)
                throw std::runtime_error("actual publication/context authority required");
            if(runtime.identity && !runtime.publication_drained(*runtime.identity))
                throw std::runtime_error("new context overlaps real publication debt");
            runtime.identity=identity;
        };
        runtime.reload=[&](int stage,int rank,int pair,const std::string& cfg){
            owner_bounds(stage,rank,pair);
            if(!native->result().quiet||driven.go||driven.cfg_go||!runtime.identity ||
               !runtime.publication_drained||!runtime.publication_drained(*runtime.identity))
                throw std::runtime_error("native ROM owner reload lacks actual old-context drain");
            auto words=cfg_words(cfg);
            memory.cfg=std::move(words);memory.stage=stage;memory.rank=rank;memory.pair=pair;
            runtime.stage=stage;runtime.rank=rank;runtime.pair=pair;
        };
        std::filesystem::create_directories(argv[6]);
        const auto path=std::filesystem::path(argv[6])/"native_pair_edges.tsv";
        std::unique_ptr<FILE,decltype(&fclose)> journal(fopen(path.c_str(),"wx"),fclose);
        if(!journal)throw std::runtime_error("preserve existing actual element results");
        fprintf(journal.get(),"cycle\tstage\trank\tpair\tvalid\terror\trows\tpositions\tsegments\tsegment_counts\tvalues\n");
        auto check_participants=[&](){
            if(runtime.participants.empty())throw std::runtime_error("actual native participants required");
            for(auto& p:runtime.participants)
                if(p.name.empty()||!p.prepare||!p.rising||!p.falling||!p.fault)
                    throw std::runtime_error("incomplete actual native participant");
        };
        runtime.cold_start=[&](){
            if(started||runtime.identity||accepted_go||cycle)
                throw std::runtime_error("cold reset cannot clear accepted native debt");
            check_participants();
            auto before=native->result();
            for(auto& p:runtime.participants)p.prepare(before);
            native->eval(true,false);
            for(auto& p:runtime.participants)p.rising(false);
            native->eval(false,false);
            for(auto& p:runtime.participants)p.falling(false);
            started=true;
        };
        runtime.tick=[&](){
            if(!started)throw std::runtime_error("shared native cold start required");
            if(runtime.participants.empty()||!runtime.publication_ready||!runtime.publication_drained)
                throw std::runtime_error("actual native input/publication participants required");
            auto before=native->result();
            if(before.fault)throw std::runtime_error("native element fault");
            for(auto& p:runtime.participants) {
                if(p.name.empty()||!p.prepare||!p.rising||!p.falling||!p.fault)
                    throw std::runtime_error("incomplete actual native participant");
                p.prepare(before);
            }
            // Input participants set the command for this edge in prepare().
            // Admit that command, rather than the preceding edge's held GO.
            if(driven.go) {
                if(!runtime.identity||before.busy||!runtime.publication_ready(*runtime.identity))
                    throw std::runtime_error("field GO lacks actual native publication admission");
                accepted_go++;
            }
            // All consumers sample pre-edge ports. No consumer sees the
            // element's newly evaluated rising-edge result on this edge.
            native->eval(true,true);
            for(auto& p:runtime.participants)p.rising(true);
            native->eval(false,true);
            for(auto& p:runtime.participants)p.falling(true);
            cycle++;
            auto after=native->result();
            if(after.fault)throw std::runtime_error("actual native element arithmetic fault");
            for(auto& p:runtime.participants)if(p.fault())throw std::runtime_error("actual native participant fault: "+p.name);
            if(after.valid) {
                fprintf(journal.get(),"%ld\t%d\t%d\t%d\t%u\t%u\t%u\t%u\t%u\t%u\t%016llx\n",
                    cycle,runtime.stage,runtime.rank,runtime.pair,after.valid,after.error,
                    after.rows,after.positions,after.segments,after.segment_counts,
                    (unsigned long long)after.values);
                if(fflush(journal.get())||ferror(journal.get()))throw std::runtime_error("native element result write failed");
            }
        };
        int rc=source_main(runtime,argv[6]);
        // The opted-in I0 path performs native SU work and no field GO. Its
        // source plan requires actual SU acceptance, output publication ACK
        // and readback before completion. Preserve every common drain check.
        const char* native_i0=std::getenv("DSROM_S81_NATIVE_L20_I0");
        const bool nonfield_i0=native_i0&&std::string(native_i0)=="1"&&runtime.stage==37;
        const char* native_index=std::getenv("DSROM_S81_NATIVE_L20_INDEX");
        const bool nonfield_index=native_index&&std::string(native_index)=="1"&&runtime.stage==37&&runtime.rank==3;
        // The actual-core END entry clocks its own enrolled native core on
        // this host's shared edges. It requires real END and publication
        // completion in source_main; no field-pair GO is implied by END.
        const char* native_end=std::getenv("DSROM_S81_NATIVE_HEAD_END");
        const bool nonfield_end=native_end&&std::string(native_end)=="1"&&
            runtime.stage==80&&runtime.rank==0&&runtime.pair==11&&runtime.bf16;
        // The selected four-rank ATT caller uses native KV/attention services,
        // not this host's field pair. Its own completion still owes all ACKs.
        const char* native_att=std::getenv("DSROM_S81_NATIVE_L20_ATT");
        const bool nonfield_att=native_att&&std::string(native_att)=="1"&&runtime.stage==37&&runtime.rank==0;
        // Full field actors own their selected pairs and checked GO/ACK counts.
        // The singleton host pair remains quiet; common publication drain applies.
        const char* native_field=std::getenv("DSROM_S81_NATIVE_L20_FIELD");
        const char* native_qfield=std::getenv("DSROM_S81_NATIVE_L20_QFIELD");
        const bool actor_field=((native_field&&std::string(native_field)=="1")||
                                (native_qfield&&std::string(native_qfield)=="1"))&&
                               runtime.stage==37&&runtime.rank>=0&&runtime.rank<4;
        if(rc==0&&((!accepted_go&&!nonfield_i0&&!nonfield_index&&!nonfield_end&&!nonfield_att&&!actor_field)||!runtime.identity||!runtime.publication_drained||
                   !runtime.publication_drained(*runtime.identity)||!native->result().quiet))
            throw std::runtime_error("source exit precedes actual native field/publication drain");
        printf("MINIMUM_SOURCE_EXIT rc=%d cycles=%ld field_go=%llu stage=%d rank=%d pair=%d\n",
            rc,cycle,(unsigned long long)accepted_go,runtime.stage,runtime.rank,runtime.pair);
        return rc;
    }catch(const std::exception& e){fprintf(stderr,"MINIMUM_NATIVE_ERROR %s\n",e.what());return 1;}
}
