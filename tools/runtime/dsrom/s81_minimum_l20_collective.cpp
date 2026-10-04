#include "s81_minimum_l20_collective.hpp"
#include "VDsromL20Collective.h"
#include "verilated.h"
#include <deque>
#include <memory>

namespace {
struct Collective {
    DsromS81MinimumRuntime& runtime;
    uint64_t identity;
    std::array<DsromS81MinimumSourceIo,4> io;
    std::function<void(unsigned,unsigned)> accepted;
    std::function<void(unsigned,unsigned,const S81EmbeddingOutput&)> captured;
    VDsromL20Collective leaf;
    struct Pending {S81EmbeddingOutput output;bool offered=false;};
    std::array<std::deque<Pending>,4> pending;
    std::array<std::array<uint32_t,5120>,4> operands{};
    std::array<unsigned,4> fetched{},seen{};
    unsigned pc=0,src=0,dst=0,n=0,extent=0,mode=0;
    const DsromS81L20CollectiveLiteral* held=nullptr;
    bool requested=false;
    bool reset_seen=false,armed=false,admitted=false,stopped=false,finished=false;
    static void require(bool v,const char* why){if(!v)throw std::runtime_error(why);}
    Collective(DsromS81MinimumRuntime&r,uint64_t id,const std::array<DsromS81MinimumSourceIo,4>& source,
           std::function<void(unsigned,unsigned)> a,
           std::function<void(unsigned,unsigned,const S81EmbeddingOutput&)> c)
        :runtime(r),identity(id),io(source),accepted(std::move(a)),captured(std::move(c)),
         leaf(r.context,"minimum_native_l20_collective") {
        require(r.context&&r.cycle&&identity<(1ull<<47)&&accepted&&captured,
                "native gather requires same context and publication callbacks");
        for(const auto& rank:io)require(rank.read_word&&rank.span_lease&&rank.offer&&rank.visible,
                                      "native gather needs actual four rank VM services");
        leaf.clk=0;leaf.rst_n=0;leaf.go=0;leaf.mode=0;leaf.rnd=0;leaf.src=0;leaf.dst=0;leaf.n=0;leaf.tag=0;leaf.vm_ready=0;
        for(unsigned i=0;i<64;i++)leaf.vm_rq[i]=0;
    }
    static const DsromS81L20CollectiveLiteral& literal(const DsromS81PrefixOperation& op) {
        for(const auto& item:dsrom_s81_l20_collective_literals())if(item.operation.index==op.index) {
            require(op.unit==6 && op.instruction==item.operation.instruction && op.template_sha256 &&
                    std::string(op.template_sha256)==item.operation.template_sha256,
                    "L20 collective literal payload changed");
            return item;
        }
        throw std::runtime_error("L20 collective excludes TOPK and other nodes");
    }
    bool inputs_ready(const DsromS81PrefixOperation& op) {
        const auto& item=literal(op);
        require(!stopped,"native collective quarantined");
        if(admitted && armed)return false;
        if(!armed) {
            require(reset_seen&&!leaf.busy&&empty(),"collective prefetch before reset/drain");
            held=&item;pc=op.index;src=item.src;dst=item.dst;n=item.n;mode=item.mode;
            extent=mode?4*n:n;
            fetched.fill(0);seen.fill(0);finished=false;admitted=false;armed=true;requested=false;
            leaf.src=src>>4;leaf.dst=dst>>4;leaf.n=n>>4;
            leaf.mode=mode;leaf.rnd=item.rnd;leaf.tag=item.seq;
        }
        require(held==&item,"collective literal changed during held prefetch");
        for(unsigned rank=0;rank<4;rank++)
            if(fetched[rank]!=n || !io[rank].span_lease(identity,src,n))return false;
        return true;
    }
    void drive(const DsromS81PrefixOperation& op,bool go) {
        // Existing sequencer clears every engine with the current OTHER unit's
        // instruction. Deassertion must neither decode nor erase held debt.
        if(!go){requested=false;leaf.go=0;return;}
        const auto& item=literal(op);
        require(held==&item && armed && !admitted,"collective drive without held literal");
        if(go)require(inputs_ready(op),"collective GO without four positive source leases");
        requested=go;leaf.go=go;
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
                leaf.go=requested&&ready&&!leaf.busy&&empty();
            }
            if(armed&&admitted&&!leaf.busy&&empty()) {
                for(auto count:seen)require(count==extent,"native gather drain lacks exact allrank outputs");
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
                    require(admitted&&(!mode || (pending[rank].empty()&&((leaf.vm_ready>>rank)&1u))),
                            "native output lacks finite batch reservation");
                    S81EmbeddingOutput out{};out.vm_identity=identity;out.vm_valid=1;
                    out.vm_address=field(leaf.vm_waddr,(rank*4+bank)*15,15)*16;
                    require(out.vm_address>=dst&&out.vm_address+16<=dst+extent,
                            "native gather write outside literal destination");
                    for(unsigned i=0;i<16;i++)out.vm_data[i]=leaf.vm_wdata[(rank*4+bank)*16+i];
                    writes[rank].push_back(out);
                }
            }
            if(leaf.go) {
                require(armed&&!admitted&&!leaf.busy,"native GO acceptance mismatch");
                for(unsigned rank=0;rank<4;rank++)accepted(rank,pc);
                admitted=true;requested=false;
            }
            leaf.clk=1;leaf.eval();
            for(unsigned i=0;i<64;i++)leaf.vm_rq[i]=rq[i]; // synchronous read Q after edge
            require(!leaf.fault,"native collective/DMA fault");
            for(unsigned rank=0;rank<4;rank++)for(const auto& out:writes[rank]) {
                require(pending[rank].size()<(mode?4:n/16)&&seen[rank]+16<=extent,"native reserved output seat overflow");
                captured(rank,pc,out);pending[rank].push_back({out,false});seen[rank]+=16;
            }
        }catch(...){stopped=true;throw;}
    }
    void falling(bool released){leaf.rst_n=released;leaf.clk=0;leaf.eval();}
};
}
DsromS81PrefixNativeEngine dsrom_s81_bind_native_l20_collective(
    DsromS81MinimumRuntime&r,uint64_t identity,const std::array<DsromS81MinimumSourceIo,4>&io,
    std::function<void(unsigned,unsigned)>accepted,
    std::function<void(unsigned,unsigned,const S81EmbeddingOutput&)>captured,bool opt_in) {
    if(!opt_in)throw std::runtime_error("L20 native collective defaults OFF");
    auto p=std::make_shared<Collective>(r,identity,io,std::move(accepted),std::move(captured));
    return {{"native-L20-nonTOPK-TP4",[p](const auto& result){p->prepare(result);},
             [p](bool reset){p->rising(reset);},[p](bool reset){p->falling(reset);},
             [p](){return p->stopped||bool(p->leaf.fault);}},
            [p](){return p->reset_seen&&!p->stopped&&!p->leaf.busy&&(!p->armed||!p->admitted);},
            [p](){return !p->armed&&p->empty()&&!p->leaf.busy&&!p->stopped;},
            [p](const auto& op){return p->inputs_ready(op);},
            [p](const auto& op,bool go){p->drive(op,go);}};
}

const std::array<DsromS81L20CollectiveLiteral,13>& dsrom_s81_l20_collective_literals() {
    static const std::array<DsromS81L20CollectiveLiteral,13> values{{
        {{9,6,"71936363a5862e0eee46beb9bc7b365611e47ef7dc983204e86e2351c03e1f16",{0x000000feu,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00667c04u,0x00032700u,0x00000140u,0x00000000u,0x00000000u,0x00000000u,0x00000000u}},419776,51648,320,1,0,0},
        {{10,6,"ffbfb9c687822720845951b78ad0718c4bcc9556032ac16eb33427e932a4b4c8",{0x000000feu,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00669004u,0x00034f00u,0x00000080u,0x80000000u,0x00000000u,0x00000000u,0x00000000u}},420096,54208,128,1,0,1},
        {{26,6,"f8417aa9a218f042977ac04f8f236b3fd067ef0583cb11fc0e819c7ad4cb8c69",{0x000000feu,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x006d0e04u,0x0005b080u,0x00000080u,0x00000000u,0x00000001u,0x00000000u,0x00000000u}},446688,93216,128,1,0,2},
        {{72,6,"a6e0b31f76812c358612794889096418e39596048be9dd06139fc66950d0ff12",{0x000000feu,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00669e00u,0x00052880u,0x00001400u,0x80000000u,0x00000082u,0x00000000u,0x00000000u}},420320,84512,5120,0,1,5},
        {{88,6,"8bc6752db8e6480d2a840b79135853dbadedfe6a76676ae6713a9b2498a9cb58",{0x000000feu,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00660804u,0x001b1f80u,0x00000240u,0x00000000u,0x00000003u,0x00000000u,0x00000000u}},417920,444384,576,1,0,6},
        {{91,6,"09f53c094cc62c1be5a63fc616415fdd294ff444829682ee93366283009deb0c",{0x000000feu,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00669804u,0x00165580u,0x00000060u,0x80000000u,0x00000003u,0x00000000u,0x00000000u}},420224,365920,96,1,0,7},
        {{102,6,"39afacc0344816abe200be042d979a83c2a27e5e72eb545c290fc6e99b6eb543",{0x000000feu,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x0061a004u,0x001a4780u,0x00000240u,0x00000000u,0x00000004u,0x00000000u,0x00000000u}},399872,430560,576,1,0,8},
        {{112,6,"eb1bcab2a4a1ef92b3959a9f879365a1a2db9b280eb5188c0dccc601e7c991c0",{0x000000feu,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00625c04u,0x001a6b80u,0x00000240u,0x80000000u,0x00000004u,0x00000000u,0x00000000u}},402880,432864,576,1,0,9},
        {{117,6,"db65fa4471bd9c4b1d93cdc3ce021fd498369bc3d2309707afc912afeb8c4ba8",{0x000000feu,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00631804u,0x001a8f80u,0x00000240u,0x00000000u,0x00000005u,0x00000000u,0x00000000u}},405888,435168,576,1,0,10},
        {{122,6,"6e28bd26428d2cf98350126a4986b18446c824217bc32749b6fd21cc7a72629d",{0x000000feu,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x0063d404u,0x001ab380u,0x00000240u,0x80000000u,0x00000005u,0x00000000u,0x00000000u}},408896,437472,576,1,0,11},
        {{127,6,"abe208004bc75e177305329029113e996237cd3aaab2e08ff637867991deff34",{0x000000feu,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00649004u,0x001ad780u,0x00000240u,0x00000000u,0x00000006u,0x00000000u,0x00000000u}},411904,439776,576,1,0,12},
        {{130,6,"84cafc3547546d9b8401db7d1bf381bb04162a9b755932912b34aa53adfa0758",{0x000000feu,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00654c04u,0x001afb80u,0x00000240u,0x80000000u,0x00000006u,0x00000000u,0x00000000u}},414912,442080,576,1,0,13},
        {{138,6,"fcc788dc2c26dd58ccac02bc8bac7846a2923487be91a313652592da095aa78b",{0x000000feu,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x0014a204u,0x0019f780u,0x00000500u,0x00000000u,0x00000007u,0x00000000u,0x00000000u}},84512,425440,1280,1,0,14}
    }};
    return values;
}
