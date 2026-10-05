#pragma once
#include "s81_minimum_runtime.hpp"
#include <deque>
#include <set>
#include <stdexcept>

// Port glue for the existing idx_pool_adapt and xu_adapt(X_SEL=1) native
// models, AW30/NW21, four stacks x 32 PCs, SK512. No scorer, selector,
// backing memory, private clock or initialization payload is implemented here.
// Arch owns source decode/GO, actual operand/score-memory latency and HBM
// wiring. Noether consumes the SAME published selection VM span. A retained
// self-driving testbench or whole-die model is not a substitute for these ports.
namespace dsrom_s81_minimum {
template<class Index,class Select> class NativeIndexParticipant {
public:
    struct SelectionWrite { uint64_t identity; uint32_t address,id; };
    struct Counters {
        uint64_t request_bytes=0,response_bytes=0,active_cycles=0;
        uint64_t first_accept_cycle=0,last_accept_cycle=0;
        uint64_t native_keys=0,native_scores=0,visible_ids=0;
        bool saw_accept=false;
    };
    using Wiring=std::function<void()>;
    using Offer=std::function<bool(const SelectionWrite&)>;
    using Visible=std::function<bool(const SelectionWrite&)>;
    using Fence=std::function<bool()>;
private:
    DsromS81MinimumRuntime& runtime;
    Index& index; Select& select;
    Wiring wire; Offer offer; Visible visible; Fence actual_source_and_history;
    uint64_t identity=0; uint32_t base=0;
    bool armed=false,stopped=false,offered=false;
    std::vector<SelectionWrite> old_writes;
    bool old_index_go=false,old_select_go=false,index_accepted=false,select_accepted=false;
    uint64_t old_request=0,old_response=0;
    std::deque<SelectionWrite> pending;
    std::set<uint32_t> ids;
    Counters measured;
    long prepared=-1;
    static void require(bool ok,const char* why) {
        if(!ok)throw std::runtime_error(why);
    }
    template<class Wide> static uint32_t bits(const Wide& value,unsigned off,unsigned n) {
        uint32_t result=0;
        for(unsigned b=0;b<n;++b)result|=((value[(off+b)/32]>>((off+b)%32))&1u)<<b;
        return result;
    }
    void prepare() {
        require(!fault(),"native index participant fault; debt retained");
        require(prepared!=runtime.cycle(),"index participant prepared twice");
        prepared=runtime.cycle();
        if(!pending.empty()) {
            if(!offered)offered=offer(pending.front());
            if(offered&&visible(pending.front())) {
                pending.pop_front();offered=false;++measured.visible_ids;
            }
        }
        // Wiring may settle combinational ports, but never evaluates rising
        // edges, creates ACKs, supplies oracle scores or preloaded selection.
        index.clk=0;select.clk=0;wire();index.eval();select.eval();
        wire();index.eval();select.eval();
        old_request=old_response=0;
        old_index_go=armed&&index.go&&index.ready;
        old_select_go=armed&&select.go&&select.ready;
        old_writes.clear();
        if(!armed)return;
        require(runtime.identity&&*runtime.identity==identity&&actual_source_and_history(),
                "index source/history lease or current-row visibility lost");
        if(old_index_go)require(!index_accepted&&index.i_nout==262144,
                "index GO must scan its exact 262144-key rank once");
        if(old_select_go)require(!select_accepted&&select.i_bf16&&select.i_n==262144&&
                select.i_k==512&&select.i_op==0,
                "selector GO must select actual full-rank scores/top512");
        for(unsigned pc=0;pc<128;++pc) {
            if(bits(index.h_req_v,pc,1)&&bits(index.h_req_rdy,pc,1)) {
                auto len=bits(index.h_req_len,pc*4,4);
                require(len>0,"zero-length accepted index HBM request");
                old_request+=uint64_t(len)*32;
            }
            if(bits(index.h_rsp_v,pc,1)&&bits(index.h_rsp_rdy,pc,1))old_response+=32;
        }
        if(select.w_we) {
            require(select_accepted,"selection write before native SELECT acceptance");
            for(unsigned lane=0;lane<32;++lane)if((select.w_mask>>lane)&1u) {
                SelectionWrite w{identity,uint32_t(select.w_addr)+lane,
                                 uint32_t(select.w_data[lane])};
                require(w.address==base+ids.size()+old_writes.size()&&w.id<262144&&
                        ids.size()+old_writes.size()<512,
                        "native rank selection address/count/ID outside source span");
                old_writes.push_back(w);
            }
        }
    }
    void rising(bool released) {
        require(!fault(),"native index fault; retained publication debt");
        require(released||!armed,"reset cannot discard admitted index history/selection");
        require(prepared==runtime.cycle(),"index missing common pre-edge prepare");
        if(released&&armed) {
            index_accepted|=old_index_go;select_accepted|=old_select_go;
            if(old_request||old_response) {
                const auto c=uint64_t(runtime.cycle());
                if(!measured.saw_accept)measured.first_accept_cycle=c;
                measured.saw_accept=true;measured.last_accept_cycle=c;
            }
            measured.request_bytes+=old_request;measured.response_bytes+=old_response;
            if(old_index_go||old_select_go||!index.idle||!select.idle||!pending.empty())
                ++measured.active_cycles;
            for(const auto& w:old_writes) {
                require(ids.insert(w.id).second,"duplicate actual selected ID");
                pending.push_back(w);
            }
        }
        index.rst_n=released;select.rst_n=released;
        index.clk=1;select.clk=1;index.eval();select.eval();
        if(armed) {
            measured.native_keys=index.dbg_keys_streamed;
            measured.native_scores=index.dbg_keys_scored;
        }
    }
public:
    NativeIndexParticipant(DsromS81MinimumRuntime& r,Index& i,Select& s,
        Wiring wiring,Offer actual_vm_offer,Visible matched_vm_visible,Fence source_and_history)
    :runtime(r),index(i),select(s),wire(std::move(wiring)),offer(std::move(actual_vm_offer)),
     visible(std::move(matched_vm_visible)),actual_source_and_history(std::move(source_and_history)) {
        require(r.context&&r.cycle&&wire&&offer&&visible&&actual_source_and_history,
                "index requires native ports and actual publication/history authorities");
    }
    void arm(uint64_t id,uint32_t actual_selection_base) {
        require(!armed&&!fault()&&index.idle&&select.idle&&runtime.identity&&
                *runtime.identity==id&&id<(1ull<<47)&&
                uint64_t(actual_selection_base)+512<=(1u<<19)&&actual_source_and_history(),
                "index admission requires actual full source/history and idle native models");
        identity=id;base=actual_selection_base;armed=true;
    }
    bool rank_selection_visible()const {
        return armed&&!fault()&&index_accepted&&select_accepted&&index.idle&&select.idle&&
            measured.native_keys==262144&&measured.native_scores==262144&&
            measured.saw_accept&&measured.response_bytes>0&&ids.size()==512&&
            measured.visible_ids==512&&pending.empty()&&actual_source_and_history();
    }
    bool fault()const{return stopped||index.fault||select.fault;}
    const Counters& counters()const{return measured;}
    DsromS81MinimumParticipant participant() {
        return {"actual-L20-native-index-top512",
            [this](const DsromS81PairResult&){try{prepare();}catch(...){stopped=true;throw;}},
            [this](bool r){try{rising(r);}catch(...){stopped=true;throw;}},
            [this](bool r){index.rst_n=r;select.rst_n=r;index.clk=0;select.clk=0;
                         index.eval();select.eval();},[this]{return fault();}};
    }
};
}
