#pragma once
#include <algorithm>
#include <map>
#include <utility>
#include "s81_minimum_macro_ack_adapter.hpp"

namespace dsrom_s81_minimum {
struct NativeRootPorts {
    bool valid=false,error=false;
    uint16_t row=0,bf16=0;
    uint8_t position=0;
    uint32_t fp32=0;
};

// Literal binding read by the caller from its selected emitted PHROM/key/CFG.
// One canonical region/node only; these receipts never certify other roots.
struct ReturnPhaseBinding {
    int stage=-1,rank=-1,pair=-1;
    uint8_t root=0, positions_minus_one=0,format=0;
    uint16_t phase=0;
    uint64_t identity=0, phrom0=0, phrom1=0;
    uint32_t output_base=0, output_position_stride=0;
    std::string emitted_key, source_matrix_sha256, cfg_path;
    // Canonical region boundary and exact node a/b leaf indices from connectivity.
    uint16_t region_pair_begin=0,region_pair_end=0;
    uint32_t branch_a_leaf=0,branch_b_leaf=0;
    // Canonical plans prove this selected pair owns EVERY K segment of these
    // rows. Other rows/root quotas remain whole-phase obligations elsewhere.
    std::vector<uint16_t> component_rows;
};

inline uint32_t native_partial_tag(const Partial& p) {
    if(p.segment>=32||p.segments==0||p.segments>=32||p.position>=8)
        throw std::runtime_error("literal return package tag bounds");
    // rtl/v41rom/ot_v41_ret.sv: {position3,row16,lo5,k3,nseg5};
    // runtime leaf() supplies k=0. Normalization/siblings/sum are ONLY RTL.
    return (uint32_t(p.position)<<29)|(uint32_t(p.row)<<13)|
           (uint32_t(p.segment)<<8)|p.segments;
}
inline unsigned native_root_quota(uint64_t phrom0,unsigned np,unsigned root) {
    if(np>=8||root>=128)throw std::runtime_error("canonical capture root bounds");
    const unsigned rows=(phrom0>>46)&65535,rem=rows%256;
    return (2*(rows/256)+(rem>2*root)+(rem>2*root+1))*(np+1);
}

// Uses the archived RD64/RST1/BYPASS1 branch and D128/QD128 observer root.
// No new engine, numerical interpreter, backpressure on NOREADY, or ACK timer.
// All models use runtime.context; the runtime supplies every clock edge.
// The bounded simulation records retain ALL source-selected complete rows
// until matched native ACK; no phase rebind/reuse while any debt is present.
// Full PHROM quota remains separately visible, never certified by this cut.
template<class Branch,class Root> class NativeReturnParticipant {
public:
    using Commands=std::array<std::optional<MacroWrite>,4>;
    using EncodeOwner=std::function<std::array<uint32_t,8>(const ReturnPhaseBinding&,const CaptureOwner&)>;
private:
    DsromS81MinimumRuntime& runtime;
    Branch branch;
    Root root;
    ReturnPhaseBinding bound{};
    EncodeOwner encode_owner;
    struct Row {MacroWrite command;bool accepted=false,visible=false;};
    std::deque<Row> rows;
    std::map<uint32_t,size_t> row_index;
    unsigned quota=0,seen=0,taken=0,published=0;
    bool admitted=false,stopped=false;
    uint64_t root_sample_cycle=0;
    struct RootSample {
        bool r_v=false,r_e=false;
        uint16_t r_row=0,r_bf16=0;
        uint8_t r_pos=0;
        uint32_t r_fp32=0;
    } sample;
    static void require(bool b,const char* s){if(!b)throw std::runtime_error(s);}
    uint32_t record_key(const CaptureOwner& s)const{return (uint32_t(s.position)<<16)|s.row;}
    void validate_bound(const ReturnPhaseBinding& p)const {
        require(p.stage==runtime.stage&&p.rank==runtime.rank&&p.pair==runtime.pair,
                "source phase/CFG native pair owner mismatch");
        require(p.stage>=0&&p.stage<81&&p.rank>=0&&p.rank<4&&p.pair>=0&&p.pair<2417&&
                p.root<128&&p.positions_minus_one<8&&p.format<3&&p.phase<1024&&
                p.identity<(1ull<<47)&&p.output_base<(1u<<19)&&p.output_position_stride<(1u<<19),
                "source phase port bounds");
        require(!p.emitted_key.empty()&&p.source_matrix_sha256.size()==64&&!p.cfg_path.empty(),
                "actual emitted phase/key/matrix/CFG provenance required");
        require(p.region_pair_begin<=p.pair&&p.pair<p.region_pair_end&&p.region_pair_end<=2417&&
                p.branch_a_leaf==2*unsigned(p.pair)&&p.branch_b_leaf==2*unsigned(p.pair)+1,
                "canonical region or actual first-branch leaf mismatch");
        require(native_root_quota(p.phrom0,p.positions_minus_one,p.root)!=0,
                "source selected root has zero capture quota");
        require(!p.component_rows.empty(),"source pair has no complete K-owned component rows");
        std::map<unsigned,bool> owned;
        for(auto row:p.component_rows) {
            require(row<((p.phrom0>>46)&65535)&&((unsigned(row)/2)%128)==p.root&&
                    owned.emplace(row,true).second,"component row ownership/range/duplicate");
        }
    }
    void capture_output() {
        if(!sample.r_v)return;
        require(admitted,"root pulse before accepted source phase");
        require(!sample.r_e,"native completed root carries arithmetic error");
        const unsigned nrow=(bound.phrom0>>46)&65535;
        require(sample.r_row<nrow&&sample.r_pos<=bound.positions_minus_one&&
                ((unsigned(sample.r_row)/2)%128)==bound.root,
                "root row/position outside canonical phase ownership");
        require(std::find(bound.component_rows.begin(),bound.component_rows.end(),sample.r_row)
                    !=bound.component_rows.end(),"root output outside source-selected complete-row cut");
        require(seen<quota,"NOREADY root output exceeds reserved component quota");
        CaptureOwner s{bound.identity,bound.phase,uint16_t(sample.r_row),bound.root,
                       uint8_t(sample.r_pos),0};
        const uint64_t address=uint64_t(bound.output_base)+s.row+
                              uint64_t(s.position)*bound.output_position_stride;
        require(address<(1u<<19),"native capture address aperture");
        s.element_address=uint32_t(address);
        require(!row_index.count(record_key(s)),"duplicate native root row/position");
        MacroWrite w{};w.source=s;w.word.address=address>>4;
        w.word.mask=uint16_t(1)<<(address&15);
        const bool fp32=bound.format==1 || (bound.format==0 &&
            ((s.row<(bound.phrom1&65535))?((bound.phrom0>>62)&1):((bound.phrom0>>63)&1)));
        // Exact retained capture format: root already performs BF16 RNE.
        w.word.data[address&15]=fp32?uint32_t(sample.r_fp32):(uint32_t(sample.r_bf16)<<16);
        w.word.owner=encode_owner(bound,s); // actual caller's full tuple, no padding policy
        require(!(w.word.owner[7]&~7u),"native source TAG227 width");
        row_index.emplace(record_key(s),rows.size());rows.push_back({w});seen++;
    }
    void prepare(const DsromS81PairResult& result) {
        try {
            // Snapshot old root output and old branch output before ANY model
            // rising evaluation. Register this participant before bank supply.
            sample={bool(root.r_v),bool(root.r_e),uint16_t(root.r_row),
                    uint16_t(root.r_bf16),uint8_t(root.r_pos),uint32_t(root.r_fp32)};
            root.i_v=branch.o_v;root.i_t=branch.o_t;root.i_d=branch.o_d;root.i_e=branch.o_e;
            auto a=partial(result,0),b=partial(result,1);
            require(admitted||(!a.valid&&!b.valid),"pair outputs lack source phase admission");
            branch.a_v=a.valid;branch.a_e=a.error;branch.a_d=a.fp32_bits;
            branch.b_v=b.valid;branch.b_e=b.error;branch.b_d=b.fp32_bits;
            branch.a_t=a.valid?native_partial_tag(a):0;
            branch.b_t=b.valid?native_partial_tag(b):0;
            root_sample_cycle=runtime.cycle();
        }catch(...){stopped=true;throw;}
    }
    void rising(bool released) {
        if(!released&&admitted) {
            stopped=true;
            throw std::runtime_error("cold reset would clear admitted return phase; debt quarantined");
        }
        branch.rst_n=released;root.rst_n=released;
        branch.clk=1;root.clk=1;branch.eval();root.eval();
        // Literal capture register edge: bank supply already sampled before
        // this rising edge. Newly captured records become eligible NEXT edge.
        if(released)try{capture_output();}catch(...){stopped=true;throw;}
        if(branch.fault||root.fault)stopped=true;
    }
    void falling(bool released) {
        branch.rst_n=released;root.rst_n=released;
        branch.clk=0;root.clk=0;branch.eval();root.eval();
    }
    Row& matched(const MacroWrite& w) {
        require(admitted&&w.source.identity==bound.identity&&w.source.phase==bound.phase&&
                w.source.root==bound.root,"native publication source context mismatch");
        auto it=row_index.find(record_key(w.source));
        require(it!=row_index.end(),"receipt absent from actual root outputs");
        auto& r=rows[it->second];
        require(r.command.word.address==w.word.address&&r.command.word.mask==w.word.mask&&
                r.command.word.owner==w.word.owner&&r.command.word.data==w.word.data&&
                r.command.source.element_address==w.source.element_address,
                "receipt differs from retained native root payload");
        return r;
    }
public:
    NativeReturnParticipant(DsromS81MinimumRuntime& r,EncodeOwner encoder):runtime(r),
        branch(r.context,"minimum_retained_branch"),root(r.context,"minimum_retained_root"),
        encode_owner(std::move(encoder)) {
        require(bool(encode_owner),"actual source tuple encoder required");
        branch.clk=0;branch.rst_n=0;branch.a_v=0;branch.b_v=0;
        branch.a_t=0;branch.b_t=0;branch.a_d=0;branch.b_d=0;branch.a_e=0;branch.b_e=0;
        root.clk=0;root.rst_n=0;root.i_v=0;root.i_t=0;root.i_d=0;root.i_e=0;
        branch.eval();root.eval();
    }
    void admit(const ReturnPhaseBinding& p) {
        require(!stopped&&!admitted,"return context already held/quarantined");
        require(runtime.identity&&*runtime.identity==p.identity,"accepted native context required");
        validate_bound(p);bound=p;quota=unsigned(p.component_rows.size())*(p.positions_minus_one+1);
        admitted=true;
    }
    Commands supply(const DsromS81PairResult&)const {
        require(!stopped,"return publication quarantined");
        Commands out{};
        for(const auto& r:rows)if(!r.accepted) {
            const unsigned b=r.command.word.address&3;
            if(!out[b])out[b]=r.command;
        }
        return out;
    }
    void accepted(unsigned bank,const MacroWrite& w) {
        require(!stopped&&bank==(w.word.address&3),"native acceptance bank/quarantine");
        auto& r=matched(w);require(!r.accepted,"duplicate native root publication acceptance");
        r.accepted=true;taken++;
    }
    void visible(unsigned bank,const MacroWrite& w,const VmReceipt& receipt) {
        require(bank==(w.word.address&3),"native visible bank mismatch");
        auto& r=matched(w);require(r.accepted&&!r.visible,"native ACK before acceptance or duplicate");
        require(w.word.address==receipt.address&&w.word.mask==receipt.mask&&w.word.owner==receipt.owner,
                "native ACK old-context tuple mismatch");
        r.visible=true;published++;
    }
    void warm_quarantine(){stopped=true;} // immutable records and all counts retained
    bool fault()const{return stopped||branch.fault||root.fault;}
    bool local_drained()const {
        return admitted&&!fault()&&seen==quota&&taken==quota&&published==quota&&branch.quiet&&
               !branch.o_v&&!root.r_v&&!root.obs_qc&&!root.obs_held&&!root.obs_add&&!root.obs_sv;
    }
    NativeRootPorts root_output()const {
        // Read-only OLD port snapshot; no Vcut or return model eval.
        return {bool(root.r_v),bool(root.r_e),uint16_t(root.r_row),
                uint16_t(root.r_bf16),uint8_t(root.r_pos),uint32_t(root.r_fp32)};
    }
    unsigned root_region()const {require(admitted,"unbound native return root");return bound.root;}
    bool has_admitted_phase()const{return admitted;}
    unsigned expected()const{return quota;}
    unsigned whole_root_expected()const{return admitted?native_root_quota(bound.phrom0,bound.positions_minus_one,bound.root):0;}
    unsigned received()const{return seen;}
    unsigned committed()const{return published;}
    uint64_t last_sample_cycle()const{return root_sample_cycle;}
    // No autonomous clock or field-wide/all-copy completion callback.
    DsromS81MinimumParticipant participant() {
        return {"retained-RD64-branch-D128-root",
            [this](const DsromS81PairResult& p){prepare(p);},
            [this](bool reset){rising(reset);},[this](bool reset){falling(reset);},
            [this](){return fault();}};
    }
};
} // namespace dsrom_s81_minimum
