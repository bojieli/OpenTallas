#include "s81_minimum_embedding.hpp"
#include "s81_embedding_checkpoint_client.hpp"
#include <algorithm>
#include <dlfcn.h>
#include <stdexcept>

namespace {
template<class Function> Function symbol(void* library, const char* name) {
    dlerror();
    auto pointer=dlsym(library,name);
    if(const char* error=dlerror())throw std::runtime_error(error);
    if(!pointer)throw std::runtime_error("missing native embedding ABI symbol");
    return reinterpret_cast<Function>(pointer);
}
bool same_write(const S81EmbeddingOutput& a,const S81EmbeddingOutput& b) {
    return a.vm_identity==b.vm_identity && a.vm_address==b.vm_address &&
           std::equal(std::begin(a.vm_data),std::end(a.vm_data),std::begin(b.vm_data));
}
}

struct DsromS81MinimumEmbedding::State {
    DsromS81MinimumRuntime& runtime;
    DsromS81EmbeddingCheckpointClient checkpoint;
    DsromS81EmbeddingSink sink;
    void* library=nullptr;
    void* reader=nullptr;
    decltype(&s81_embedding_destroy) destroy=nullptr;
    decltype(&s81_embedding_eval) evaluate=nullptr;
    decltype(&s81_embedding_edge) edge=nullptr;
    decltype(&s81_embedding_vm_word) probe=nullptr;
    S81EmbeddingInput input{};
    S81EmbeddingOutput output{},held{};
    uint32_t base;
    unsigned response_wait=0;
    bool reset=false,requested=false,started=false,pending=false;
    bool offered=false,request_take=false,response_take=false,write_take=false;
    bool done=false,stopped=false;

    State(DsromS81MinimumRuntime& runtime_,const std::string& path,
          const std::string& socket,uint32_t token,uint32_t position,
          uint64_t identity,uint32_t base_,DsromS81EmbeddingSink sink_)
    :runtime(runtime_),checkpoint(socket,token,position),sink(std::move(sink_)),base(base_) {
        if(!sink.offer||!sink.visible||!sink.fault||token>=129280||position>=(1u<<20)||
           identity>=(1ull<<47)||base>32768-20480||runtime.stage<0||runtime.stage>=81||
           runtime.rank<0||runtime.rank>=4||!runtime.context)
            throw std::runtime_error("minimum embedding requires real cold source and target ACK adapter");
        // The native reader addresses dedicated global embed.weight storage,
        // independent of the consumer's stage. Actual source authorization,
        // shared cold/context admission and matching VM ACKs remain required.
        // Existing embedding ABI was compiled with its own Verilator runtime.
        // Keep that runtime local rather than interposing the pair's symbols.
        library=dlopen(path.c_str(),RTLD_NOW|RTLD_LOCAL|RTLD_DEEPBIND);
        if(!library)throw std::runtime_error(dlerror());
        try {
            auto create=symbol<decltype(&s81_embedding_create)>(library,"s81_embedding_create");
            destroy=symbol<decltype(destroy)>(library,"s81_embedding_destroy");
            evaluate=symbol<decltype(evaluate)>(library,"s81_embedding_eval");
            edge=symbol<decltype(edge)>(library,"s81_embedding_edge");
            probe=symbol<decltype(probe)>(library,"s81_embedding_vm_word");
            reader=create();
            if(!reader)throw std::runtime_error("native embedding instance unavailable");
        }catch(...){dlclose(library);library=nullptr;throw;}
        input.token=token;input.identity=identity;input.vm_base=base;
    }
    ~State(){if(reader)destroy(reader);if(library)dlclose(library);}

    void prepare() {
        if(stopped)throw std::runtime_error("native embedding participant quarantined");
        if(sink.fault())throw std::runtime_error("native embedding target fault retains input debt");
        input.reset_n=reset;
        input.start=reset&&requested&&!started;
        input.req_ready=reset&&!pending;
        input.rsp_valid=reset&&pending&&response_wait==0;
        input.commit_ready=0;
        evaluate(reader,&input,&output);
        if(output.fault)throw std::runtime_error("native embedding source fault");
        request_take=output.req_valid&&input.req_ready;
        response_take=output.rsp_ready&&input.rsp_valid;
        write_take=false;
        if(output.vm_valid) {
            if(output.vm_identity!=input.identity || output.vm_address<base ||
               uint64_t(output.vm_address)+16>uint64_t(base)+20480)
                throw std::runtime_error("native embedding write owner/extent mismatch");
            if(offered&&!same_write(output,held))
                throw std::runtime_error("native embedding changed a stalled target payload");
            if(!offered) {
                held=output;
                offered=sink.offer(held);
            }
            // Only positive actual target publication releases COMMIT. The
            // reader's own mutable VM then accepts the same sixteen words.
            input.commit_ready=offered&&sink.visible(held);
            write_take=input.commit_ready;
            evaluate(reader,&input,&output);
        }else if(offered)throw std::runtime_error("native embedding withdrew unresolved target write");
        if(request_take) {
            if(pending||output.req_identity!=input.identity)
                throw std::runtime_error("foreign/overlapping native embedding request");
            auto words=checkpoint.read(output.req_identity,output.req_macro,output.req_row);
            std::copy(words.begin(),words.end(),input.rsp_data);
            input.rsp_identity=output.req_identity;
            input.rsp_macro=output.req_macro;input.rsp_row=output.req_row;
        }
    }
    void rising(bool released) {
        if(!released) {
            if(started||requested||pending||offered)
                throw std::runtime_error("embedding reset would erase accepted native debt");
            input.reset_n=0;input.start=0;input.req_ready=0;
            input.rsp_valid=0;input.commit_ready=0;
            edge(reader,&input,&output);reset=true;return;
        }
        if(!reset)throw std::runtime_error("native embedding shared cold start required");
        const auto old_count=output.committed_words;
        edge(reader,&input,&output);
        if(input.start)started=true;
        if(request_take){pending=true;response_wait=8;}
        if(response_take)pending=false;
        else if(pending&&response_wait)--response_wait;
        if(write_take)offered=false;
        if(output.committed_words!=old_count+(write_take?16u:0u))
            throw std::runtime_error("native embedding actual VM commit count mismatch");
        if(output.done) {
            if(pending||offered||output.busy||output.committed_words!=20480)
                throw std::runtime_error("native embedding completed with source/publication debt");
            done=true;
        }
    }
    void falling(bool released) {
        input.reset_n=released;
        // eval() sets clk=0. No private rising edge or simulation loop.
        evaluate(reader,&input,&output);
    }
};

DsromS81MinimumEmbedding::DsromS81MinimumEmbedding(
    DsromS81MinimumRuntime& runtime,const std::string& library,const std::string& socket,
    uint32_t token,uint32_t position,uint64_t identity,uint32_t base,DsromS81EmbeddingSink sink)
:state(std::make_shared<State>(runtime,library,socket,token,position,identity,base,std::move(sink))) {
    runtime.participants.push_back({"native_embedding",
        [s=state](const DsromS81PairResult&){
            try{s->prepare();}catch(...){s->stopped=true;throw;}
        },
        [s=state](bool released){
            try{s->rising(released);}catch(...){s->stopped=true;throw;}
        },
        [s=state](bool released){
            try{s->falling(released);}catch(...){s->stopped=true;throw;}
        },
        [s=state](){return s->stopped||bool(s->output.fault)||s->sink.fault();}});
}
void DsromS81MinimumEmbedding::start() {
    if(state->stopped||!state->reset||state->requested||!state->runtime.identity||
       *state->runtime.identity!=state->input.identity)
        throw std::runtime_error("embedding start lacks shared reset and matching source context");
    state->requested=true;
}
bool DsromS81MinimumEmbedding::complete() const{return state->done&&!state->stopped;}
uint32_t DsromS81MinimumEmbedding::committed_words() const{return state->output.committed_words;}
uint32_t DsromS81MinimumEmbedding::word(uint32_t address) const {
    if(!complete()||state->sink.fault()||!state->runtime.identity||
       *state->runtime.identity!=state->input.identity||address<state->base||
       uint64_t(address)>=uint64_t(state->base)+20480)
        throw std::runtime_error("native embedding read lacks completed target publication lease");
    return state->probe(state->reader,address);
}
