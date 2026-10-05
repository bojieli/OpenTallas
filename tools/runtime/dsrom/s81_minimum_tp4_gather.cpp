#include "s81_minimum_tp4_gather.hpp"
#include "VDsromTp4Gather.h"
#include "verilated.h"
#include <deque>
#include <memory>

namespace {
struct Gather {
    DsromS81MinimumRuntime& runtime;
    uint64_t identity;
    std::array<DsromS81MinimumSourceIo,4> io;
    std::function<void(unsigned,unsigned)> accepted;
    std::function<void(unsigned,unsigned,const S81EmbeddingOutput&)> captured;
    VDsromTp4Gather leaf;
    struct Pending {S81EmbeddingOutput output;bool offered=false;};
    std::array<std::deque<Pending>,4> pending;
    std::array<std::array<uint32_t,320>,4> operands{};
    std::array<unsigned,4> fetched{},seen{};
    unsigned pc=0,src=0,dst=0,n=0;
    bool reset_seen=false,armed=false,admitted=false,stopped=false,finished=false;
    static void require(bool v,const char* why){if(!v)throw std::runtime_error(why);}
    Gather(DsromS81MinimumRuntime&r,uint64_t id,const std::array<DsromS81MinimumSourceIo,4>& source,
           std::function<void(unsigned,unsigned)> a,
           std::function<void(unsigned,unsigned,const S81EmbeddingOutput&)> c)
        :runtime(r),identity(id),io(source),accepted(std::move(a)),captured(std::move(c)),
         leaf(r.context,"minimum_native_tp4_gather") {
        require(r.context&&r.cycle&&identity<(1ull<<47)&&accepted&&captured,
                "native gather requires same context and publication callbacks");
        for(const auto& rank:io)require(rank.read_word&&rank.span_lease&&rank.offer&&rank.visible,
                                      "native gather needs actual four rank VM services");
        leaf.clk=0;leaf.rst_n=0;leaf.go=0;leaf.command=0;leaf.vm_ready=0;
        for(unsigned i=0;i<64;i++)leaf.vm_rq[i]=0;
    }
    void start(unsigned instruction) {
        require((instruction==9||instruction==10)&&!armed&&!stopped,
                "native gather start overlaps debt or unsupported PC");
        require(reset_seen&&!leaf.busy&&empty(),"gather start before reset/previous drain");
        require(instruction==9?pc==0:(pc==9&&finished),"literal I9 then I10 order");
        pc=instruction;src=pc==9?419776:420096;dst=pc==9?51648:54208;n=pc==9?320:128;
        fetched.fill(0);seen.fill(0);finished=false;admitted=false;armed=true;
        leaf.command=pc==10;
    }
    bool empty()const {for(const auto& q:pending)if(!q.empty())return false;return true;}
    void prepare(const DsromS81PairResult&) {
        try {
            require(!stopped&&!leaf.fault,"native gather quarantined; debt retained");
            leaf.go=0;leaf.vm_ready=0;
            for(unsigned rank=0;rank<4;rank++) {
                auto& q=pending[rank];
                if(!q.empty()) {
                    auto& item=q.front();
                    if(!item.offered)item.offered=io[rank].offer(item.output,16);
                    if(item.offered&&io[rank].visible(item.output,16))q.pop_front();
                }
                if(q.empty())leaf.vm_ready|=1u<<rank;
            }
            if(armed&&!admitted) {
                require(runtime.identity&&*runtime.identity==identity,"gather lost held runtime context");
                bool ready=true;
                for(unsigned rank=0;rank<4;rank++) {
                    if(fetched[rank]<n&&io[rank].span_lease(identity,src,n)) {
                        auto value=io[rank].read_word(identity,src+fetched[rank]);
                        if(value)operands[rank][fetched[rank]++]=*value;
                    }
                    ready=ready&&fetched[rank]==n&&io[rank].span_lease(identity,src,n);
                }
                leaf.go=ready&&!leaf.busy&&empty();
            }
            if(admitted&&!leaf.busy&&empty()) {
                for(auto count:seen)require(count==4*n,"native gather drain lacks exact allrank outputs");
                armed=false;finished=true;
            }
        }catch(...){stopped=true;throw;}
    }
    static uint32_t field(const VlWide<8>& data,unsigned offset,unsigned width) {
        uint32_t v=0;for(unsigned i=0;i<width;i++)v|=((data[(offset+i)/32]>>((offset+i)%32))&1u)<<i;return v;
    }
    void rising(bool released) {
        try {
            leaf.clk=0;leaf.rst_n=released;leaf.eval();
            if(!released) {
                require(!armed&&!admitted&&empty(),"reset cannot erase native gather/publication debt");
                reset_seen=true;leaf.clk=1;leaf.eval();return;
            }
            require(!stopped&&!leaf.fault,"native gather preedge fault");
            std::array<uint32_t,64> rq{};
            std::array<std::vector<S81EmbeddingOutput>,4> writes;
            for(unsigned rank=0;rank<4;rank++) {
                for(unsigned i=0;i<16;i++)rq[rank*16+i]=leaf.vm_rq[rank*16+i];
                if((leaf.vm_re>>rank)&1u) {
                    require(admitted,"DMA read before accepted GO");
                    unsigned word=(leaf.vm_raddr>>(rank*15))&32767u;
                    require(word>=(src>>4)&&word<(src>>4)+(n>>4)&&io[rank].span_lease(identity,src,n),
                            "DMA read outside actual held source lease");
                    for(unsigned i=0;i<16;i++)rq[rank*16+i]=operands[rank][(word-(src>>4))*16+i];
                }
                for(unsigned bank=0;bank<4;bank++)if((leaf.vm_we>>(rank*4+bank))&1u) {
                    require(admitted&&pending[rank].empty()&&((leaf.vm_ready>>rank)&1u),
                            "native output lacks finite batch reservation");
                    S81EmbeddingOutput out{};out.vm_identity=identity;out.vm_valid=1;
                    out.vm_address=field(leaf.vm_waddr,(rank*4+bank)*15,15)*16;
                    require(out.vm_address>=dst&&out.vm_address+16<=dst+4*n,
                            "native gather write outside literal destination");
                    for(unsigned i=0;i<16;i++)out.vm_data[i]=leaf.vm_wdata[(rank*4+bank)*16+i];
                    writes[rank].push_back(out);
                }
            }
            if(leaf.go) {
                require(armed&&!admitted&&!leaf.busy,"native GO acceptance mismatch");
                for(unsigned rank=0;rank<4;rank++)accepted(rank,pc);
                admitted=true;
            }
            leaf.clk=1;leaf.eval();
            for(unsigned i=0;i<64;i++)leaf.vm_rq[i]=rq[i]; // synchronous read Q after edge
            require(!leaf.fault,"native collective/DMA fault");
            for(unsigned rank=0;rank<4;rank++)for(const auto& out:writes[rank]) {
                require(pending[rank].size()<4&&seen[rank]+16<=4*n,"native four-word output seat overflow");
                captured(rank,pc,out);pending[rank].push_back({out,false});seen[rank]+=16;
            }
        }catch(...){stopped=true;throw;}
    }
    void falling(bool released){leaf.rst_n=released;leaf.clk=0;leaf.eval();}
};
}
DsromS81NativeGather dsrom_s81_bind_native_tp4_gather(
    DsromS81MinimumRuntime&r,uint64_t identity,const std::array<DsromS81MinimumSourceIo,4>&io,
    std::function<void(unsigned,unsigned)>accepted,
    std::function<void(unsigned,unsigned,const S81EmbeddingOutput&)>captured) {
    auto p=std::make_shared<Gather>(r,identity,io,std::move(accepted),std::move(captured));
    return {{"native-TP4-I9-I10-gather",[p](const auto& result){p->prepare(result);},
             [p](bool reset){p->rising(reset);},[p](bool reset){p->falling(reset);},
             [p](){return p->stopped||bool(p->leaf.fault);}},
            [p](unsigned pc){p->start(pc);},[p](){return p->finished&&!p->stopped;}};
}
