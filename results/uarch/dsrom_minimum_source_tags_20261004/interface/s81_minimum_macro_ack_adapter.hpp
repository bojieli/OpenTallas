#pragma once
#include <optional>
#include <utility>
#include "s81_minimum_pair_stage.hpp"

namespace dsrom_s81_minimum {
// Port join for ot_v41_vm_bank4_macro_pipe_masked_visible_r2, AW15/TAG227,
// MASKED_VISIBLE=1. This is a simulator adapter, not a hardware queue model.
// Command suppliers must be native capture/root participants, not pair partials
// relabelled as complete rows. Only the common runtime owns clock/reset edges.
struct MacroWrite { VmWord word; CaptureOwner source; };

template<class Model> class MacroAckAdapter {
public:
    using Commands=std::array<std::optional<MacroWrite>,4>;
    using Supply=std::function<Commands(const DsromS81PairResult&)>;
    using Accepted=std::function<void(unsigned,const MacroWrite&)>;
    using Visible=std::function<void(unsigned,const MacroWrite&,const VmReceipt&)>;
private:
    Model& model;
    NativeVmReceipts receipts;
    Supply supply;
    Accepted on_accept;
    Visible on_visible;
    Commands driven{};
    // Source attribution for the native ledger, NOT additional write seats.
    struct Origin {MacroWrite command;uint64_t edge;};
    std::array<std::deque<Origin>,4> origins{};
    uint64_t edge=0;
    bool stopped=false;
    unsigned callback_debt=0;
    static void require(bool condition,const char* message) {
        if(!condition)throw std::runtime_error(message);
    }
    template<class Wide> static void bit(Wide& w,unsigned pos,bool value) {
        const uint32_t mask=uint32_t(1)<<(pos%32);
        w[pos/32]=(w[pos/32]&~mask)|(value?mask:0);
    }
    template<class Wide> static bool bit(const Wide& w,unsigned pos) {
        return (w[pos/32]>>(pos%32))&1;
    }
    template<class Wide> static void pack_owner(Wide& out,unsigned bank,
                                                const std::array<uint32_t,8>& in) {
        for(unsigned i=0;i<227;i++)bit(out,bank*227+i,(in[i/32]>>(i%32))&1);
    }
    VmReceipt ack(unsigned b) const {
        VmReceipt r;
        r.address=(uint64_t(model.wr_ack_word_addr)>>(15*b))&32767;
        r.mask=(uint64_t(model.wr_ack_lane_mask)>>(16*b))&65535;
        for(unsigned i=0;i<227;i++)
            if(bit(model.wr_ack_owner,b*227+i))r.owner[i/32]|=uint32_t(1)<<(i%32);
        return r;
    }
    void check_provider() const {
        require(!model.wr_fault&&!model.rw_collision_fault&&!model.rd_fault,
                "native bank4 provider fault");
    }
    static void validate(unsigned b,const MacroWrite& c) {
        const auto& w=c.word;const auto& s=c.source;
        require(w.address<32768&&(w.address&3)==b&&w.mask&&!(w.owner[7]&~7u),
                "invalid native bank4 command");
        require(s.identity<(1ull<<47)&&s.phase<1024&&s.root<128&&s.position<8&&
                s.element_address<(1u<<19)&&(s.element_address>>4)==w.address&&
                (w.mask&(uint16_t(1)<<(s.element_address&15))),
                "captured source element absent from native write mask");
        // Minimum observer publishes one captured element, not unobserved lanes.
        require(__builtin_popcount(w.mask)==1,"minimum publication needs one captured lane");
    }
    void prepare(const DsromS81PairResult& result) {
        try {
            require(!stopped,"native macro adapter quarantined");
            driven=supply(result);
            model.wr_v=0;model.wr_word_addr=0;model.wr_lane_mask=0;
            for(unsigned i=0;i<64;i++)model.wr_word_data[i]=0;
            for(unsigned i=0;i<29;i++)model.wr_owner[i]=0;
            // This participant owns the selected VM instance. Read service is a
            // separate native participant/instance; no invented read eligibility.
            model.rd_v=0;model.rd_base_word=0;
            for(unsigned i=0;i<8;i++)model.rd_owner[i]=0;
            for(unsigned b=0;b<4;b++)if(driven[b]) {
                validate(b,*driven[b]);
                require(receipts.can_observe_accept(b),"native ACK response reservation exhausted");
                const auto& w=driven[b]->word;
                model.wr_v|=1u<<b;
                model.wr_word_addr|=uint64_t(w.address)<<(15*b);
                model.wr_lane_mask|=uint64_t(w.mask)<<(16*b);
                for(unsigned i=0;i<16;i++)model.wr_word_data[b*16+i]=w.data[i];
                pack_owner(model.wr_owner,b,w.owner);
            }
        }catch(...) {stopped=true;throw;}
    }
    void rising(bool released) {
        try {
            model.clk=0;model.rst_n=released;model.eval();
            if(!released) {
                if(outstanding()) {receipts.warm_reset();stopped=true;}
                model.clk=1;model.eval();return;
            }
            require(!stopped,"native macro adapter quarantined");
            edge++;
            check_provider();
            const unsigned accepted=model.wr_accept_v;
            require(!(accepted&~unsigned(model.wr_v)),"unsolicited native write acceptance");
            // Record all banks before evaluating the edge: a callback exception
            // must not erase a command already accepted by another bank.
            for(unsigned b=0;b<4;b++)if(accepted&(1u<<b)) {
                require(bool(driven[b]),"acceptance lacks retained source command");
                receipts.accepted(b,driven[b]->word,driven[b]->source,1,true);
                origins[b].push_back({*driven[b],edge});
            }
            model.clk=1;model.eval();
            check_provider();
            // ACK is E+3 with OLD owner/address/mask. Current command pins are
            // deliberately never used to derive this completion's identity.
            for(unsigned b=0;b<4;b++)if(model.wr_ack_v&(1u<<b)) {
                const auto r=ack(b);
                require(!origins[b].empty(),"ACK lacks captured source attribution");
                require(edge-origins[b].front().edge==3,"ACK not native E+3 old tuple");
                receipts.visible(b,r,true); // exact accepted-head tuple match
                callback_debt++;
                on_visible(b,origins[b].front().command,r);
                callback_debt--;origins[b].pop_front();
            }
            for(unsigned b=0;b<4;b++)if(accepted&(1u<<b))on_accept(b,*driven[b]);
        }catch(...) {stopped=true;throw;}
    }
public:
    MacroAckAdapter(Model& m,Supply s,Accepted a,Visible v):model(m),
        supply(std::move(s)),on_accept(std::move(a)),on_visible(std::move(v)) {
        require(bool(supply)&&bool(on_accept)&&bool(on_visible),"actual native participant callbacks required");
    }
    MacroAckAdapter(const MacroAckAdapter&)=delete;
    MacroAckAdapter& operator=(const MacroAckAdapter&)=delete;
    uint64_t outstanding() const {return receipts.outstanding()+callback_debt;}
    // Only this selected participant's obligations, never whole-field/all-copy
    // authority. Caller must compose its actual capture/root/reverse debt.
    bool drained() const {return !fault()&&!outstanding();}
    bool fault() const {return stopped||receipts.quarantine()||model.wr_fault||
        model.rd_fault||model.rw_collision_fault;}
    DsromS81MinimumParticipant participant() {
        return {"native-bank4-matched-macro-ACK",
            [this](const DsromS81PairResult& r){prepare(r);},
            [this](bool reset){rising(reset);},
            [this](bool reset){model.clk=0;model.rst_n=reset;model.eval();},
            [this](){return fault();}};
    }
};
} // namespace dsrom_s81_minimum
