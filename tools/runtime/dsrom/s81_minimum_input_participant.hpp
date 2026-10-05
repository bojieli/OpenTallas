#pragma once
#include "s81_minimum_runtime.hpp"
#include "Vcut.h"
#include "Vcut___024root.h"
#include "verilated.h"
#include <memory>
#include <stdexcept>

namespace dsrom_s81_minimum {
// Reuses the retained 6d1f532 dsrom_source_cut archive: native actquant and
// broadcast registers, RT_CUT, PHW10/VAW16/VRD64/KMAX6144. No pair array is
// instantiated here. The archived wrapper exposes public VM/control ROMs,
// NOT a VM DPI export. ReadWord must route real published native XN storage;
// optional pending reads advance only on the enclosing shared runtime.tick.
class NativeInputParticipant {
public:
    using ReadWord=std::function<std::optional<uint32_t>(uint64_t,uint32_t)>;
    using PublishedSpan=std::function<bool(uint64_t,uint32_t,size_t)>;
    static constexpr uint32_t XBASE=46464,K=5120;
    // Literal selected L0.I7 input_control.json, not a derived cut address.
    static constexpr uint32_t SOURCE_OUTPUT_BASE=419776,SOURCE_OPS=320;
    // An explicit input-only local alias is not a physical output home. The
    // private constructor prevents the old implicit uint16_t narrowing API.
    class InputOnlyOutputAlias {
        friend class NativeInputParticipant;
        uint64_t identity;
        uint16_t phase;
        uint32_t source_base,source_ops;
        uint16_t cut_base;
        InputOnlyOutputAlias(uint64_t id,uint16_t ph,uint32_t source,uint32_t ops,uint16_t alias)
            :identity(id),phase(ph),source_base(source),source_ops(ops),cut_base(alias){}
    };
    static InputOnlyOutputAlias declare_input_only_alias(uint64_t identity,uint16_t phase,
                 uint32_t actual_output_base,uint32_t actual_ops,uint32_t declared_cut_alias) {
        if(identity>=(uint64_t(1)<<47) || phase!=0 || actual_ops!=SOURCE_OPS ||
           actual_output_base!=SOURCE_OUTPUT_BASE ||
           actual_output_base>=(1u<<19) || actual_ops>(1u<<19)-actual_output_base ||
           declared_cut_alias>=(1u<<16) || actual_ops>(1u<<16)-declared_cut_alias ||
           (declared_cut_alias<XBASE+K && XBASE<declared_cut_alias+actual_ops))
            throw std::runtime_error("input-only alias/source VM19 span or cut VM16 span invalid");
        return InputOnlyOutputAlias(identity,phase,actual_output_base,actual_ops,
                                    static_cast<uint16_t>(declared_cut_alias));
    }
private:
    DsromS81MinimumRuntime& runtime;
    Vcut& cut;
    ReadWord read_word;
    PublishedSpan published_span;
    uint64_t identity=0;
    uint32_t loaded=0;
    uint32_t source_output_base=0,source_ops=0,source_rows=0;
    uint16_t local_output_alias=0;
    bool cold_seen=false,armed=false,issued=false,saw_pair_go=false;
    uint64_t cfg_edges=0,xs_edges=0,vm_read_edges=0;

    DsromS81PairDrive drive() const {
        DsromS81PairDrive p{};
        p.cfg_go=cut.fb_cfg_go;p.cfg_ph=cut.fb_cfg_ph;p.cfg_np=cut.fb_cfg_np;
        p.go=cut.fb_go;p.go_bf=cut.fb_go_bf;
        p.xs_v=cut.fb_xs_v;p.xs_p=cut.fb_xs_p;p.xs_b=cut.fb_xs_b;p.xs_sv=cut.fb_xs_sv;
        p.xs_e0=cut.fb_xs_e0;p.xs_e1=cut.fb_xs_e1;p.xs_pos=cut.fb_xs_pos;
        for(unsigned i=0;i<8;i++){p.xs_q0[i]=cut.fb_xs_q0[i];p.xs_q1[i]=cut.fb_xs_q1[i];}
        p.xb_pos=cut.fb_xb_pos;p.xb_v=cut.fb_xb_v;p.xb_b=cut.fb_xb_b;
        p.xb_sv=cut.fb_xb_sv;p.xb_u=cut.fb_xb_u;
        for(unsigned i=0;i<32;i++)p.xb_d[i]=cut.fb_xb_d[i];
        return p;
    }
    void prepare(const DsromS81PairResult&) {
        cut.go=0;
        if(armed) {
            if(!runtime.identity || *runtime.identity!=identity)
                throw std::runtime_error("native input source context changed");
            // Copy only exact raw bits returned by the actual native prefix
            // read participant. No exponent calculation or FP conversion.
            if(!issued && loaded<K && published_span(identity,XBASE,K)) {
                auto value=read_word(identity,XBASE+loaded);
                if(value) {
                    cut.rootp->dsrom_source_cut__DOT__dut__DOT__vm[XBASE+loaded]=*value;
                    loaded++;
                }
            }
            if(!issued && loaded==K && published_span(identity,XBASE,K) && cut.ready)
                cut.go=1;
        }
        // Copy the OLD native broadcast ports before ANY rising eval. Cicero
        // checks actual pair GO admission after all prepare callbacks.
        runtime.drive(drive());
    }
    void rising(bool released) {
        const bool accepted=bool(cut.go)&&bool(cut.ready)&&released;
        if(released) {
            cfg_edges+=cut.fb_cfg_go;xs_edges+=cut.fb_xs_v;vm_read_edges+=cut.obs_VM_re;
            if(cut.fb_go) {
                if(!armed || !issued || cut.fb_go_bf)
                    throw std::runtime_error("selected FP8 source broadcast GO mismatch");
                saw_pair_go=true;
            }
        }
        cut.clk=1;cut.rst_n=released;cut.eval();
        if(!released)cold_seen=true;
        if(accepted)issued=true;
    }
    void falling(bool released) {cut.clk=0;cut.rst_n=released;cut.eval();}
public:
    NativeInputParticipant(DsromS81MinimumRuntime& r,Vcut& native_cut,
                           ReadWord actual_xn_read,PublishedSpan actual_xn_published)
        :runtime(r),cut(native_cut),read_word(std::move(actual_xn_read)),
         published_span(std::move(actual_xn_published)) {
        if(!runtime.context || cut.contextp()!=runtime.context || !runtime.drive ||
           runtime.stage!=0 || runtime.rank!=0 || runtime.pair!=0 || !runtime.bf16 ||
           !read_word || !published_span)
            throw std::runtime_error("actual selected L0.I7/Vpb input participant binding required");
        cut.go=0;cut.clk=0;cut.rst_n=0;
        // fr_* remain Arch's real retained-root inputs. Never populate a
        // missing result, clear a live fault, or force ready/idle here.
    }

    void arm(uint64_t actual_identity,uint16_t phase,
             const std::array<uint64_t,2>& literal_phrom,
             const std::vector<uint64_t>& literal_stream,
             uint32_t actual_output_base,uint32_t actual_ops,
             const InputOnlyOutputAlias& declared_alias) {
        if(!cold_seen || armed || issued || !runtime.identity ||
           *runtime.identity!=actual_identity || actual_identity>=(uint64_t(1)<<47) || phase!=0)
            throw std::runtime_error("native input arm requires selected cold/context/phase");
        const uint64_t word=literal_phrom[0];
        const uint32_t k=(word>>1)&8191,beats=(word>>14)&65535,base=(word>>30)&65535;
        const uint32_t rows=(word>>46)&65535;
        if((word&1) || k!=K || !beats || beats!=literal_stream.size() ||
           base>=16384 || beats>16384-base || literal_phrom[1]>>16)
            throw std::runtime_error("literal source PHROM does not fit retained FP8 encoder");
        if(rows!=SOURCE_OPS || actual_ops!=SOURCE_OPS || actual_output_base!=SOURCE_OUTPUT_BASE ||
           actual_output_base>=(1u<<19) ||
           rows>(1u<<19)-actual_output_base || declared_alias.identity!=actual_identity ||
           declared_alias.phase!=phase || declared_alias.source_base!=actual_output_base ||
           declared_alias.source_ops!=actual_ops)
            throw std::runtime_error("declared input-only alias differs from actual source output route");
        for(auto stream:literal_stream)if(stream>>48)
            throw std::runtime_error("literal source STREAM exceeds native 48-bit word");
        identity=actual_identity;
        source_output_base=actual_output_base;source_ops=actual_ops;source_rows=rows;
        local_output_alias=declared_alias.cut_base;
        auto* root=cut.rootp;
        root->dsrom_source_cut__DOT__dut__DOT__u_sp__DOT__phrom[2*phase]=literal_phrom[0];
        root->dsrom_source_cut__DOT__dut__DOT__u_sp__DOT__phrom[2*phase+1]=literal_phrom[1];
        for(size_t i=0;i<literal_stream.size();i++)
            root->dsrom_source_cut__DOT__dut__DOT__u_sp__DOT__strom[base+i]=literal_stream[i];
        cut.i_ph=phase;cut.i_np=0;cut.i_xbase=XBASE;cut.i_xps=0;
        // Only the input encoder uses this local cut alias. The actual root
        // supplier must route by actual_output_address(), never cut.o_addr or
        // cut VM writes. Full literal PHROM rows/stream remain unchanged.
        cut.i_obase=local_output_alias;cut.i_ops=static_cast<uint16_t>(actual_ops);
        armed=true;
    }
    DsromS81MinimumParticipant participant() {
        return {"native_fp8_input",[this](const auto& p){prepare(p);},
            [this](bool r){rising(r);},[this](bool r){falling(r);},
            [this](){return bool(cut.fault);}};
    }
    // Arch may use this SAME cut to bind actual branch/root return inputs.
    // Sender never evaluates it outside the shared participant callbacks.
    Vcut& native_cut(){return cut;}
    bool inputs_loaded() const{return loaded==K;}
    bool input_finished() const {
        return issued && saw_pair_go && !cut.obs_ld_run && !cut.obs_sm_run && !cut.fault;
    }
    uint32_t actual_output_address(uint32_t row,uint32_t position) const {
        if(!armed || position!=0 || row>=source_rows)
            throw std::runtime_error("actual source output row/position outside selected route");
        return source_output_base+position*source_ops+row;
    }
    uint32_t actual_output_base() const {
        if(!armed)throw std::runtime_error("actual source output route not armed");
        return source_output_base;
    }
    uint32_t actual_output_ops() const {
        if(!armed)throw std::runtime_error("actual source output route not armed");
        return source_ops;
    }
    uint16_t input_only_cut_alias() const {
        if(!armed)throw std::runtime_error("input-only cut alias not declared/armed");
        return local_output_alias;
    }
    // Deliberately no phase_idle/publication callback: this input-only cut
    // cannot qualify actual source output visibility or a 320-row completion.
    bool input_only_cut_idle() const{return issued && bool(cut.idle);}
    static constexpr bool cut_output_publication_credit(){return false;}
    uint64_t native_cfg_edges() const{return cfg_edges;}
    uint64_t native_xs_edges() const{return xs_edges;}
    uint64_t native_vm_read_edges() const{return vm_read_edges;}
};
} // namespace dsrom_s81_minimum
