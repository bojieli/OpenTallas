#pragma once
#include "s81_minimum_prefix_io.hpp"
#include <deque>
#include <map>
#include <memory>
#include <set>
#include <type_traits>

// Port provider for the selected unit1 MC_A path, NOT the legacy weight ME
// or the ROM/head path. NativeLeaf is unchanged ot_hdc_v41x_att_adapt from
// rtl/w17_runtime/hdc/v41x: W16/G4/IL8/AW30/NW21/MP1/H16/D512/TD32/
// NL4/TROWS640/NHMAX16/PACKED_KV1. The selected core's X_ATT1 requires REAL
// chronological stored-format KV rows; this wrapper never re-encodes host KV.
// real_kv uses the EXISTING PrefixNativeEngine/participant interface. Its
// callbacks own actual KV ports on this SAME leaf and runtime. Missing hooks
// are rejected, and no zero/ready/clean substitute is supplied. With an ATT
// cut, its real attention participant must be enrolled on the shared host too.
// Final measurement enrollment is DS position 1048575: 128 WINDOW rows plus
// 512 native selected-history rows. A full extent is necessary, not proof of
// provenance: real_kv must still own those actual rows and their native order.
// No build is requested here: native KV callback/source enrollment is pending.
template<class NativeLeaf> class DsromS81MinimumMeAttention {
    DsromS81MinimumRuntime& runtime;
    uint64_t identity;
    dsrom_s81_minimum::PrefixPublication& publication;
    DsromS81MinimumSourceIo io;
    std::shared_ptr<NativeLeaf> leaf;
    DsromS81PrefixNativeEngine kv;
    std::function<uint32_t(unsigned)> dynamic;
    std::optional<DsromS81PrefixOperation> operation;
    std::map<uint32_t,uint32_t> operands;
    std::vector<uint32_t> addresses;
    size_t fetched=0;
    bool accepted=false,offered=false,stopped=false;
    std::deque<S81EmbeddingOutput> output;
    static void require(bool ok,const char* why) {
        if(!ok)throw std::runtime_error(why);
    }
    static uint32_t field(const DsromS81PrefixOperation& op,unsigned off,unsigned n) {
        uint32_t value=0;
        for(unsigned j=0;j<n;++j)value|=((op.instruction[(off+j)/32]>>((off+j)%32))&1u)<<j;
        return value;
    }
    template<class Packed> static uint32_t bits(const Packed& p,unsigned off,unsigned n) {
        uint32_t value=0;
        for(unsigned j=0;j<n;++j) {
            if constexpr (std::is_integral<Packed>::value)value|=((uint64_t(p)>>(off+j))&1u)<<j;
            else value|=((p[(off+j)/32]>>((off+j)%32))&1u)<<j;
        }
        return value;
    }
    uint32_t resolved(const DsromS81PrefixOperation& op,unsigned off,unsigned width,unsigned d)const {
        const unsigned selector=field(op,d,6);
        require(!selector || bool(dynamic),"ME requires actual source DYN callback for literal selector");
        const uint64_t value=uint64_t(field(op,off,width))+(selector?dynamic(selector):0);
        require(value<(1ull<<width),"ME resolved source field exceeds actual port width");
        return uint32_t(value);
    }
    void decode(const DsromS81PrefixOperation& op) {
        leaf->i_nout=resolved(op,11,21,276);leaf->i_tiles=resolved(op,32,21,282);
        leaf->i_k=resolved(op,53,21,288);leaf->i_wbase=resolved(op,75,30,258);
        leaf->i_xbase=resolved(op,195,30,264);leaf->i_obase=resolved(op,226,30,270);
        leaf->i_ts=field(op,105,30);leaf->i_ks=field(op,135,30);leaf->i_js=field(op,165,30);
        leaf->i_xks=field(op,294,30);leaf->i_xjs=field(op,324,30);leaf->i_xcs=field(op,420,30);
        leaf->i_hg=field(op,450,2);leaf->i_ogs=field(op,452,30);leaf->i_round=field(op,225,1);
        leaf->i_ots=field(op,357,30);leaf->i_ojs=field(op,387,30);leaf->i_mmode=field(op,417,1);
        leaf->i_oen=field(op,256,1);leaf->i_m=field(op,1723,3);
    }
    void check_dynamic(const DsromS81PrefixOperation& op)const {
        require(leaf->i_nout==resolved(op,11,21,276)&&leaf->i_tiles==resolved(op,32,21,282)&&
                leaf->i_k==resolved(op,53,21,288)&&leaf->i_wbase==resolved(op,75,30,258)&&
                leaf->i_xbase==resolved(op,195,30,264)&&leaf->i_obase==resolved(op,226,30,270),
                "ME source DYN values changed after captured operand association");
    }
    void capture(uint32_t address,uint32_t payload) {
        require(operation&&accepted&&address<(1u<<19),"ME output lacks admitted source/address19");
        S81EmbeddingOutput result{};result.vm_valid=true;result.vm_identity=identity;
        result.vm_address=address;result.vm_data[0]=payload;
        auto command=dsrom_s81_reserve_native_scalar_tag(runtime,identity,operation->index,address,payload);
        require(command.source.identity==identity&&command.source.element_address==address&&
                command.word.address==(address>>4)&&command.word.mask==(uint16_t(1)<<(address&15))&&
                command.word.data[address&15]==payload,"ME source tag changed native payload");
        publication.native_scalar(operation->index,command,true);output.push_back(result);
    }
public:
    DsromS81MinimumMeAttention(DsromS81MinimumRuntime& r,uint64_t id,
        dsrom_s81_minimum::PrefixPublication& pub,const DsromS81MinimumSourceIo& source,
        std::shared_ptr<NativeLeaf> native,DsromS81PrefixNativeEngine real_kv,
        std::function<uint32_t(unsigned)> source_dynamic)
    :runtime(r),identity(id),publication(pub),io(source),leaf(std::move(native)),
     kv(std::move(real_kv)),dynamic(std::move(source_dynamic)) {
        require(leaf&&r.context&&r.cycle&&id<(1ull<<47)&&io.read_word&&io.span_lease&&io.offer&&io.visible,
                "ME requires selected actual native model and same-VM SourceIo");
        require(!kv.participant.name.empty()&&kv.participant.prepare&&kv.participant.rising&&
                kv.participant.falling&&kv.participant.fault&&kv.ready&&kv.idle&&kv.inputs_ready&&kv.drive,
                "ME real packed-KV provider absent; cannot return zeros or force readiness");
        leaf->clk=0;leaf->rst_n=0;leaf->go=0;
        for(unsigned j=0;j<4;++j)leaf->x_q[j]=0;
        // All KV valid/mask/data/fault and ATT-cut ports are owned by the real
        // provider. Do not clear, tie or synthesize those signals here.
    }
    bool inputs_ready(const DsromS81PrefixOperation& op) {
        try {
            require(!fault(),"ME native/real KV/publication fault");
            if(accepted)return false;
            if(!operation || operation->index!=op.index) {
                require(leaf->idle&&output.empty(),"ME prefetch overlaps outstanding native publication");
                require(op.unit==1&&field(op,0,3)==1&&field(op,74,1)==1&&
                        !field(op,257,1)&&!field(op,1795,1)&&!field(op,418,2),
                        "this provider is QK/PV only; weight/head/indexer require their actual engines");
                decode(op);
                require(leaf->i_m<=1&&leaf->i_round&&leaf->i_mmode&&leaf->i_js==0&&
                        leaf->i_hg<=1,"ME selected attention geometry/rounding contract");
                const unsigned nk=leaf->i_ks>1?leaf->i_k:512;
                require(nk>0&&nk<=640&&leaf->i_nout>0&&
                        (leaf->i_ks>1?leaf->i_nout==512:leaf->i_k==512),
                        "ME attention shape is not actual D512 QK or chronological PV");
                require(leaf->i_ks>=1&&
                        (leaf->i_ks>1?leaf->i_k:leaf->i_nout)==640,
                        "DS target-context ME requires WINDOW128 plus selected512; reduced-context debug is excluded");
                std::set<uint32_t> unique;
                for(unsigned h=0;h<(8u<<leaf->i_hg);++h)for(unsigned k=0;k<nk;++k) {
                    const uint64_t a=uint64_t(leaf->i_xbase)+(h/8)*uint64_t(leaf->i_xcs)+
                        k*uint64_t(leaf->i_xks)+(h%8)*uint64_t(leaf->i_xjs);
                    require(a<(1u<<19),"ME operand address19 alias");unique.insert(uint32_t(a));
                }
                operation=op;addresses.assign(unique.begin(),unique.end());operands.clear();fetched=0;
            }
            require(operation->unit==op.unit&&operation->instruction==op.instruction,"ME held literal changed");
            check_dynamic(op);
            if(fetched<addresses.size()) {
                auto a=addresses[fetched];if(!io.span_lease(identity,a,1))return false;
                auto payload=io.read_word(identity,a);if(!payload)return false;
                require(io.span_lease(identity,a,1),"ME operand lease revoked at captured response");
                operands.emplace(a,*payload);++fetched;
            }
            if(fetched<addresses.size())return false;
            for(auto a:addresses)require(io.span_lease(identity,a,1),"ME source operand version lost before GO");
            // The real WINDOW may already own staged rows and therefore be
            // non-idle. Its positive ready/inputs_ready authorizes this exact
            // held consumer; terminal idle is required only for retirement.
            return kv.inputs_ready(op)&&kv.ready();
        }catch(...){stopped=true;throw;}
    }
    void drive(const DsromS81PrefixOperation& op,bool go) {
        try {
            if(go)require(!fault()&&!accepted&&operation&&operation->index==op.index&&
                          operation->instruction==op.instruction&&fetched==addresses.size()&&
                          runtime.identity&&*runtime.identity==identity&&leaf->ready&&kv.ready(),
                          "ME GO lacks actual source and real KV admission");
            if(go) {
                check_dynamic(op);
                for(auto a:addresses)require(io.span_lease(identity,a,1),"ME operand version lost on GO edge");
            }
            leaf->go=go;kv.drive(op,go);
        }catch(...){stopped=true;throw;}
    }
    void prepare(const DsromS81PairResult& result) {
        try {
            require(!fault(),"ME quarantined");kv.participant.prepare(result);
            if(!output.empty()) {
                if(!offered)offered=io.offer(output.front(),1);
                if(offered&&io.visible(output.front(),1)){output.pop_front();offered=false;}
            }
            if(accepted&&leaf->idle&&kv.idle()&&output.empty())accepted=false;
        }catch(...){stopped=true;throw;}
    }
    void rising(bool released) {
        try {
            require(released || (!accepted&&output.empty()),"ME reset would erase accepted native debt");
            std::array<uint32_t,4> q{};
            for(unsigned g=0;g<4;++g) {
                q[g]=leaf->x_q[g];
                if(released&&((leaf->x_re>>g)&1)) {
                    const auto a=bits(leaf->x_addr,g*30,30);auto found=operands.find(a);
                    require(found!=operands.end()&&io.span_lease(identity,a,1),"ME native x read lacks actual leased operand");
                    q[g]=found->second;
                }
            }
            if(released&&leaf->go&&leaf->ready)accepted=true;
            require(!released||!leaf->kv_re,"PACKED_KV1 unexpectedly requested unbound raw KV");
            // Both participants prepared OLD bus values before ANY evaluation.
            // Their actual rising callbacks sample the same pre-edge handshake.
            leaf->rst_n=released;leaf->clk=1;leaf->eval();
            kv.participant.rising(released);
            for(unsigned g=0;g<4;++g)leaf->x_q[g]=q[g];
            if(released) {
                require(!leaf->fault&&!kv.participant.fault(),"actual ME/KV terminal fault");
                for(unsigned g=0;g<4;++g)if((leaf->o_we>>g)&1) {
                    const uint64_t base=uint64_t(bits(leaf->o_addr,g*30,30))*16;
                    for(unsigned j=0;j<16;++j)if(bits(leaf->o_mask,g*16+j,1)) {
                        require(base+j<(1u<<19),"ME native masked writer address19 alias");
                        capture(uint32_t(base+j),leaf->o_data[g*16+j]);
                    }
                }
            }
        }catch(...){stopped=true;throw;}
    }
    void falling(bool released) {leaf->rst_n=released;leaf->clk=0;leaf->eval();kv.participant.falling(released);}
    bool fault()const {return stopped||leaf->fault||kv.participant.fault()||publication.fault();}
    bool ready()const {return leaf->ready&&kv.ready()&&!accepted&&!fault();}
    bool idle()const {return leaf->idle&&kv.idle()&&output.empty()&&!accepted&&!fault();}
};

template<class NativeLeaf> DsromS81PrefixNativeEngine dsrom_s81_bind_minimum_me_attention(
    DsromS81MinimumRuntime& runtime,uint64_t identity,
    dsrom_s81_minimum::PrefixPublication& publication,const DsromS81MinimumSourceIo& io,
    const DsromS81MinimumSourceTags& tags,std::shared_ptr<NativeLeaf> native,
    DsromS81PrefixNativeEngine real_kv,std::function<uint32_t(unsigned)> source_dynamic) {
    if(!tags.scalar_accept||!tags.read_accept)throw std::runtime_error("ME actual source accept callbacks absent");
    auto p=std::make_shared<DsromS81MinimumMeAttention<NativeLeaf>>(
        runtime,identity,publication,io,std::move(native),std::move(real_kv),std::move(source_dynamic));
    return {{"native-ME-attention-QK-PV",[p](const auto& r){p->prepare(r);},
        [p](bool released){p->rising(released);},[p](bool released){p->falling(released);},
        [p](){return p->fault();}},[p](){return p->ready();},[p](){return p->idle();},
        [p](const auto& op){return p->inputs_ready(op);},[p](const auto& op,bool go){p->drive(op,go);}};
}

// Concrete selected-model entrypoints. The factory borrows the created leaf
// to join actual packed KV and, if selected, ATT-cut buses before binding it.
// Both joins remain actual participants on the canonical shared edge.
class VDsromAttention;
std::shared_ptr<VDsromAttention> dsrom_s81_create_minimum_me_attention(
    DsromS81MinimumRuntime& runtime);
DsromS81PrefixNativeEngine dsrom_s81_bind_minimum_me_attention(
    DsromS81MinimumRuntime& runtime,uint64_t identity,
    dsrom_s81_minimum::PrefixPublication& publication,
    const DsromS81MinimumSourceIo& io,const DsromS81MinimumSourceTags& tags,
    std::shared_ptr<VDsromAttention> native,DsromS81PrefixNativeEngine real_kv,
    std::function<uint32_t(unsigned)> source_dynamic);
