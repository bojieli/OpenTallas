#pragma once
#include "s81_minimum_prefix_io.hpp"
#include <deque>
#include <map>
#include <memory>

// Actual native XU port provider, not a software Sinkhorn evaluator.
// Arch's selected source is g_xu_a/ot_hdc_v41_xu: AW30 NW21 K512 IKW12
// SK_STEP7, with the actual source's HDC_SINKHORN_SEQ definition retained.
// Reuse that exact model; do not substitute default AW24/NW16 or g_xu_x.
// The unified model already prices sinkhorn_select_engram and serial Sinkhorn
// (tools/uarch_model.py). No engine, arithmetic, clock or geometry is changed.
// The caller retains/registers this participant ONCE on its shared host clock.
template<class NativeLeaf> class DsromS81MinimumXu {
    DsromS81MinimumRuntime& runtime;
    uint64_t identity;
    dsrom_s81_minimum::PrefixPublication& publication;
    DsromS81MinimumSourceIo io;
    std::shared_ptr<NativeLeaf> leaf;
    std::optional<DsromS81PrefixOperation> operation;
    std::vector<uint32_t> input;
    size_t fetched=0;
    uint32_t source=0,destination=0,count=0;
    unsigned opcode=0;
    bool accepted=false,stopped=false,offered=false;
    std::deque<S81EmbeddingOutput> output;
    static void require(bool ok,const char* why) {
        if(!ok)throw std::runtime_error(why);
    }
    static uint32_t field(const DsromS81PrefixOperation& op,unsigned off,unsigned n) {
        uint32_t result=0;
        for(unsigned j=0;j<n;++j)
            result|=((op.instruction[(off+j)/32]>>((off+j)%32))&1u)<<j;
        return result;
    }
    bool same_operation(const DsromS81PrefixOperation& op)const {
        return operation && operation->index==op.index &&
               operation->unit==op.unit && operation->instruction==op.instruction;
    }
    void decode(const DsromS81PrefixOperation& op) {
        // Fixed offsets from hdc_isa_v41.FULL_LAYOUT, not reduced-profile ISA.
        leaf->i_op=field(op,1455,2);
        leaf->i_src=field(op,1457,30); leaf->i_dst=field(op,1487,30);
        leaf->i_n=field(op,1517,21); leaf->i_k=field(op,1544,12);
        leaf->i_layer=field(op,1562,1);
    }
    uint32_t read(uint32_t address)const {
        require(io.span_lease(identity,source,count),"XU source version revoked during native execution");
        if(address>=source && uint64_t(address)-source<input.size())
            return input[address-source];
        throw std::runtime_error("XU native read outside actual leased operands");
    }
    void capture(uint32_t address,uint32_t bits) {
        require(operation&&accepted,"XU output before actual GO acceptance");
        require(uint64_t(address)<(1u<<19),"XU output address19 alias");
        const uint64_t limit=opcode==1?16:leaf->i_k;
        require(address>=destination && uint64_t(address)-destination<limit,
                "XU native writer outside literal result range");
        S81EmbeddingOutput result{};
        result.vm_valid=true;result.vm_identity=identity;
        result.vm_address=address;result.vm_data[0]=bits;
        // Same existing source tag reservation and publication callbacks. The
        // parent must enroll PC29 etc in these existing literal extent tables;
        // this provider does not bypass their current prefix-only rejection.
        auto command=dsrom_s81_reserve_native_scalar_tag(
            runtime,identity,operation->index,address,bits);
        require(command.source.identity==identity && command.source.element_address==address &&
                command.word.address==(address>>4) &&
                command.word.mask==(uint16_t(1)<<(address&15)) &&
                command.word.data[address&15]==bits,"XU source reservation changed native output");
        publication.native_scalar(operation->index,command,true);
        output.push_back(result);
    }
public:
    DsromS81MinimumXu(DsromS81MinimumRuntime& r,uint64_t id,
        dsrom_s81_minimum::PrefixPublication& pub,const DsromS81MinimumSourceIo& source_io,
        std::shared_ptr<NativeLeaf> native)
    :runtime(r),identity(id),publication(pub),io(source_io),leaf(std::move(native)) {
        require(leaf&&r.context&&r.cycle&&id<(1ull<<47)&&io.read_word&&io.span_lease&&
                io.offer&&io.visible,"XU requires actual selected native model and same-VM SourceIo");
        leaf->clk=0;leaf->rst_n=0;leaf->go=0;
        leaf->rst_v=0;leaf->rst_slot=0;leaf->prime_v=0;leaf->prime_first=0;leaf->prime_cid=0;
        leaf->token=0;leaf->first=0;leaf->i_hslot=0;
        leaf->vr_q=0;leaf->cr_q=0;
        for(unsigned j=0;j<32;++j)leaf->xr_q[j]=0;
        for(unsigned j=0;j<9;++j)leaf->er_q[j]=0;
    }
    bool inputs_ready(const DsromS81PrefixOperation& op) {
        try {
            require(!fault(),"XU native participant quarantined");
            if(accepted)return false;
            if(!same_operation(op)) {
                require(!operation || operation->index!=op.index,
                        "XU held literal changed without retirement");
                require(leaf->idle && output.empty(),"XU prefetch overlaps native debt");
                require(op.unit==4 && field(op,0,3)==4,"XU literal unit mismatch");
                require(field(op,1538,6)==0 && field(op,1556,6)==0,
                        "XU requires actual source-resolved dynamic count/k before binding");
                opcode=field(op,1455,2);
                require(opcode==1,"only actual literal Sinkhorn enrolled; SEL/EHASH/EGATHER need their source providers");
                source=field(op,1457,30);destination=field(op,1487,30);
                count=opcode==1?16:field(op,1517,21);
                require(count>0 && uint64_t(source)+count<=(1u<<19),"XU input extent/address19");
                require(opcode!=1 || field(op,1517,21)==16,"native Sinkhorn literal requires sixteen operands");
                require(uint64_t(destination)+(opcode==1?16:field(op,1544,12))<=(1u<<19),
                        "XU output extent/address19");
                if(!io.span_lease(identity,source,count))return false;
                operation=op;decode(op);input.assign(count,0);fetched=0;
            }
            require(io.span_lease(identity,source,count),"XU source lease lost during prefetch");
            // One existing actual scalar read request per host edge/poll. The
            // caller invokes this once per edge; no private eval or tick loop.
            if(fetched<input.size()) {
                auto bits=io.read_word(identity,source+fetched);
                if(!bits)return false;
                input[fetched++]=*bits;
            }
            return fetched==input.size();
        }catch(...){stopped=true;throw;}
    }
    void drive(const DsromS81PrefixOperation& op,bool go) {
        try {
            leaf->go=go;
            if(!go)return;
            require(!fault() && same_operation(op) && !accepted && fetched==input.size() &&
                    runtime.identity && *runtime.identity==identity &&
                    io.span_lease(identity,source,count),"XU GO before actual operand readiness");
            decode(op);
        }catch(...){stopped=true;throw;}
    }
    void prepare(const DsromS81PairResult&) {
        try {
            require(!fault(),"XU native/publication fault");
            if(!output.empty()) {
                if(!offered)offered=io.offer(output.front(),1);
                if(offered && io.visible(output.front(),1)) {output.pop_front();offered=false;}
            }
            if(accepted && leaf->idle && output.empty())accepted=false;
        }catch(...){stopped=true;throw;}
    }
    void rising(bool released) {
        try {
            require(released || (!accepted && output.empty()),"XU reset would erase admitted native debt");
            const bool accept=released&&leaf->go&&leaf->ready;
            auto scalar=leaf->vr_q;
            std::array<uint32_t,32> wide{};
            for(unsigned j=0;j<32;++j)wide[j]=leaf->xr_q[j];
            if(released) {
                if(leaf->vr_re)scalar=read(leaf->vr_addr);
                if(leaf->xr_re)for(unsigned j=0;j<16;++j)wide[j]=read(leaf->xr_addr+j);
                require(!leaf->cr_re && !leaf->er_re,"unbound XU ROM request cannot return zero");
            }
            if(accept) {require(operation && fetched==input.size(),"unprepared actual XU accept");accepted=true;}
            leaf->rst_n=released;leaf->clk=1;leaf->eval(); // Native reads see OLD Q.
            leaf->vr_q=scalar;
            for(unsigned j=0;j<32;++j)leaf->xr_q[j]=wide[j];
            // Registered memory Q becomes visible only after the native edge.
            if(released) {
                require(!leaf->fault,"actual XU arithmetic/control fault");
                if(leaf->vw_we)capture(leaf->vw_addr,leaf->vw_data);
                if(leaf->w_we)for(unsigned j=0;j<32;++j)
                    if((leaf->w_mask>>j)&1)capture(leaf->w_addr+j,leaf->w_data[j]);
            }
        }catch(...){stopped=true;throw;}
    }
    void falling(bool released) {leaf->rst_n=released;leaf->clk=0;leaf->eval();}
    bool fault()const {return stopped||leaf->fault||publication.fault();}
    bool ready()const {return leaf->ready&&!accepted&&!fault();}
    bool idle()const {return leaf->idle&&!accepted&&output.empty()&&!fault();}
};

template<class NativeLeaf> DsromS81PrefixNativeEngine dsrom_s81_bind_minimum_xu(
    DsromS81MinimumRuntime& runtime,uint64_t identity,
    dsrom_s81_minimum::PrefixPublication& publication,const DsromS81MinimumSourceIo& io,
    const DsromS81MinimumSourceTags& tags,std::shared_ptr<NativeLeaf> native) {
    if(!tags.scalar_accept || !tags.read_accept)
        throw std::runtime_error("XU same-bank actual source accept callbacks required");
    auto p=std::make_shared<DsromS81MinimumXu<NativeLeaf>>(
        runtime,identity,publication,io,std::move(native));
    return {{"native-XU-source-SINK",[p](const auto& r){p->prepare(r);},
        [p](bool released){p->rising(released);},[p](bool released){p->falling(released);},
        [p](){return p->fault();}},[p](){return p->ready();},[p](){return p->idle();},
        [p](const auto& op){return p->inputs_ready(op);},
        [p](const auto& op,bool go){p->drive(op,go);}};
}

// Concrete selected primitive instantiation in s81_minimum_xu.cpp. Link the
// unchanged ot_hdc_v41_xu full-shape archive with generated prefix VDsromXu.
DsromS81PrefixNativeEngine dsrom_s81_bind_minimum_xu(
    DsromS81MinimumRuntime&,uint64_t,dsrom_s81_minimum::PrefixPublication&,
    const DsromS81MinimumSourceIo&,const DsromS81MinimumSourceTags&);
