#include "s81_native_head_argmax.hpp"
#include "VDsromS81Aux2048.h"
#include "VDsromTop2048.h"
#include <algorithm>

struct DsromS81NativeHeadArgmax::Impl {
    static constexpr unsigned rows=32320,keep=64;
    DsromS81MinimumRuntime& runtime;
    const uint64_t identity;
    const uint32_t base;
    std::array<DsromS81MinimumSourceIo,4> io;
    std::array<std::unique_ptr<VDsromS81Aux2048>,4> selectors;
    VDsromTop2048 merge;
    std::array<std::array<uint32_t,rows>,4> logits{};
    std::array<std::array<uint32_t,keep>,4> ids{};
    std::array<unsigned,4> fetched{},outputs{};
    std::array<bool,4> select_go{},select_idle{};
    uint64_t sequence=0;
    unsigned loads=0;
    bool cold=false,armed=false,merge_go=false,merge_done=false,stopped=false,acked=false;
    std::optional<DsromS81HeadArgmaxResult> held;
    static void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
    bool fault()const {
        if(stopped||merge.fault)return true;
        for(const auto& s:selectors)if(s->fault)return true;
        return false;
    }
    void owner()const {
        require(runtime.identity&&*runtime.identity==identity,"head argmax actual source owner changed");
    }
    bool leases()const {
        for(const auto& source:io)if(!source.span_lease(identity,base,rows))return false;
        return true;
    }
    Impl(DsromS81MinimumRuntime& r,uint64_t id,const std::array<DsromS81MinimumSourceIo,4>& source,uint32_t b)
        :runtime(r),identity(id),base(b),io(source),merge(r.context,"head_global_native_TOP2048") {
        require(r.context&&id<(1ull<<47)&&uint64_t(base)+rows<=(1ull<<19),"head argmax shared context/owner/logits home");
        for(unsigned rank=0;rank<4;++rank){
            require(io[rank].read_word&&io[rank].span_lease,"head argmax requires four actual produced logits homes");
            selectors[rank]=std::make_unique<VDsromS81Aux2048>(r.context,("head_native_SELECT64_rank"+std::to_string(rank)).c_str());
            auto& s=*selectors[rank];s.clk=0;s.rst_n=0;s.go=0;s.i_op=0;s.i_bf16=0;
            s.i_src=base;s.i_dst=0;s.i_n=rows;s.i_k=keep;s.i_layer=0;s.token=0;
            s.first=0;s.i_hslot=0;s.rst_v=0;s.rst_slot=0;s.prime_v=0;s.prime_first=0;s.prime_cid=0;
            s.vr_q=0;s.cr_q=0;
            for(unsigned j=0;j<32;++j)s.xr_q[j]=0;
            for(unsigned j=0;j<64;++j)s.vsl_q[j]=0;
            for(unsigned j=0;j<9;++j)s.er_q[j]=0;
        }
        merge.clk=0;merge.rst_n=0;merge.go=0;merge.ld_valid=0;merge.ld_id=0;merge.ld_word=0;merge.ld_rank=0;
        merge.n=keep;merge.k=1;merge.stride=rows;
        for(unsigned j=0;j<64;++j)merge.ld_data[j]=0;
    }
    bool inputs_ready()const {
        return cold&&!armed&&!acked&&!fault()&&leases()&&
            std::all_of(fetched.begin(),fetched.end(),[](unsigned n){return n==rows;});
    }
    void start(uint64_t seq) {
        owner();require(inputs_ready(),"head native SELECT before complete actual logits/leases");
        sequence=seq;armed=true;
    }
    uint32_t read(unsigned rank,uint32_t address)const {
        require(address>=base&&uint64_t(address)<uint64_t(base)+rows,"native head SELECT read outside source logits");
        return logits[rank][address-base];
    }
    void prepare(const DsromS81PairResult&) {
        try {
            require(!fault(),"native head argmax quarantined");
            if(cold&&runtime.identity&&!armed&&!acked){
                owner();
                if(leases())for(unsigned rank=0;rank<4;++rank)if(fetched[rank]<rows){
                    auto value=io[rank].read_word(identity,base+fetched[rank]);
                    if(value){
                        // Contract check on bits, not host ordering/arithmetic.
                        require((*value&0x7f800000u)!=0x7f800000u,"actual head nonfinite logit quarantined");
                        logits[rank][fetched[rank]++]=*value;
                    }
                }
            }
            for(unsigned rank=0;rank<4;++rank){auto& s=*selectors[rank];
                s.go=armed&&!select_go[rank];
            }
            merge.go=0;merge.ld_valid=0;merge.n=keep;merge.k=1;merge.stride=rows;
            if(armed&&std::all_of(select_idle.begin(),select_idle.end(),[](bool v){return v;})){
                if(loads<8){
                    merge.ld_id=loads>=4;merge.ld_rank=0;merge.ld_word=loads%4;
                    for(unsigned rank=0;rank<4;++rank)for(unsigned j=0;j<16;++j){
                        const auto local=ids[rank][(loads%4)*16+j];
                        merge.ld_data[rank*16+j]=loads>=4?local:logits[rank][local];
                    }
                    merge.ld_valid=1;
                }else if(!merge_go)merge.go=1;
            }
        }catch(...){stopped=true;throw;}
    }
    void rising(bool released) {
        try {
            require(!fault(),"native head argmax quarantined");
            if(!released)require(!armed&&!held,"reset would erase accepted native head argmax debt");
            if(armed){owner();require(leases(),"head logit source lease revoked before result acceptance");}
            for(unsigned rank=0;rank<4;++rank){auto& s=*selectors[rank];
                const bool take=released&&s.go&&s.ready;
                auto next=s.vr_q;
                if(released){
                    if(s.vr_re){require(select_go[rank],"foreign head SELECT request");next=read(rank,s.vr_addr);}
                    require(!s.xr_re&&!s.vsl_re&&!s.cr_re&&!s.er_re,"head SELECT requested an unenrolled port");
                }
                s.rst_n=released;s.clk=1;s.eval();
                // Native reads sample OLD Q; captured source bits become Q after edge.
                s.vr_q=next;
                if(take){require(armed&&!select_go[rank],"duplicate head SELECT GO");select_go[rank]=true;}
                if(released){
                    require(!s.fault,"native head SELECT fault");
                    require(!s.w_we,"head SELECT unexpected vector result port");
                    if(s.vw_we){
                        require(select_go[rank]&&outputs[rank]<keep&&s.vw_addr==outputs[rank],"native SELECT candidate output extent/order");
                        const uint32_t local=s.vw_data;
                        require(local<rows&&(outputs[rank]==0||local>ids[rank][outputs[rank]-1]),"native SELECT candidate ID not unique ascending local source ID");
                        ids[rank][outputs[rank]++]=local;
                    }
                    if(select_go[rank]&&s.idle){require(outputs[rank]==keep,"head SELECT idle before64 native candidates");select_idle[rank]=true;}
                }
            }
            const bool load=released&&merge.ld_valid;
            const bool go=released&&merge.go;
            merge.rst_n=released;merge.clk=1;merge.eval();
            if(!released){cold=true;return;}
            if(load){require(armed&&loads<8&&!merge_go,"foreign native head merge load");++loads;}
            if(go){require(armed&&loads==8&&!merge_go,"head TOP GO before actual eight load strobes");merge_go=true;}
            require(!merge.fault,"native head TOP fault");
            if(merge.out_valid){
                require(merge_go&&!held&&!merge_done&&merge.out_nw==1&&merge.out_last,"native head TOP output count/terminal");
                const uint32_t global=merge.out_data[0];
                require(global<4*rows,"native head global ID out of vocabulary");
                for(unsigned j=1;j<16;++j)require(merge.out_data[j]==0,"native head TOP k1 padding not zero");
                const unsigned rank=global/rows,local=global%rows;
                require(std::find(ids[rank].begin(),ids[rank].end(),local)!=ids[rank].end(),"native global ID absent from accepted candidate set");
                held=DsromS81HeadArgmaxResult{identity,sequence,global,logits[rank][local]};
            }
            if(merge.done){require(merge_go&&held&&!merge_done,"early/duplicate native head merge done");merge_done=true;}
        }catch(...){stopped=true;throw;}
    }
    void falling(bool released){
        for(auto& s:selectors){s->rst_n=released;s->clk=0;s->eval();}
        merge.rst_n=released;merge.clk=0;merge.eval();
    }
    std::optional<DsromS81HeadArgmaxResult> result()const {
        require(!fault(),"faulted native head result cannot publish");
        if(!merge_done)return std::nullopt;
        owner();return held;
    }
    void acknowledge(const DsromS81HeadArgmaxResult& accepted){
        owner();require(!fault()&&merge_done&&held&&!acked&&
            accepted.identity==held->identity&&accepted.sequence==held->sequence&&
            accepted.global_id==held->global_id&&accepted.bits==held->bits,
            "head ReadResult ACK must match held actual native result");
        require(!merge.busy,"head result ACK before actual native merge idle");
        acked=true;armed=false;held.reset();
    }
};
DsromS81NativeHeadArgmax::DsromS81NativeHeadArgmax(DsromS81MinimumRuntime& runtime,uint64_t id,
    const std::array<DsromS81MinimumSourceIo,4>& io,uint32_t base)
    :state(std::make_shared<Impl>(runtime,id,io,base)){}
DsromS81MinimumParticipant DsromS81NativeHeadArgmax::participant(){auto p=state;
    return {"head_native_SELECT64_TOP1",[p](const auto&r){p->prepare(r);},
        [p](bool r){p->rising(r);},[p](bool r){p->falling(r);},[p](){return p->fault();}};}
bool DsromS81NativeHeadArgmax::inputs_ready()const{return state->inputs_ready();}
void DsromS81NativeHeadArgmax::start(uint64_t seq){state->start(seq);}
std::optional<DsromS81HeadArgmaxResult> DsromS81NativeHeadArgmax::result()const{return state->result();}
void DsromS81NativeHeadArgmax::acknowledge(const DsromS81HeadArgmaxResult& accepted){state->acknowledge(accepted);}
bool DsromS81NativeHeadArgmax::idle()const{return !state->fault()&&(!state->armed)&&(!state->merge_go||state->acked);}
bool DsromS81NativeHeadArgmax::fault()const{return state->fault();}
