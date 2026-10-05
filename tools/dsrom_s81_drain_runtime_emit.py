"""Generate an actual native scheduler with retained all-copy drain authority.

Consumes Cicero's emitter; originals and live model archives are untouched.
This is C++ runtime source generation only, with no RTL/model build or clock.
"""
from pathlib import Path
import argparse
from dsrom_s81_scheduler_emit import emit as emit_scheduler
import hdc_isa_v41 as ISA

ROOT=Path(__file__).resolve().parents[1]


def program_book():
    """Extract metadata from the actual native program using the official ABI.

    No tensor evaluation, allocation or map validation; deferred dynamic output
    extents refuse until an actual producer supplies their resolved ownership.
    """
    names=('unit','wait','pred','dslot','mx_m','mx_ops','qe_mode','qe_nout','qe_obase',
           'qe_d_obase','me_wsrc','me_nout','me_obase','me_d_obase','me_d_nout')
    accessors='\n'.join(f'    static uint64_t {name}(const std::string& w) {{return bits(w,{ISA.FULL_LAYOUT[name][0]},{ISA.FULL_LAYOUT[name][1]});}}'
                         for name in names)
    return r'''#pragma once
#include <fstream>
#include <string>
#include <vector>
#include "s81_native_drain.hpp"
class DsromS81NativeProgramBook {
    std::string root;
    std::array<std::vector<std::string>,4> programs;
    std::vector<std::string> read(int rank) const {
        std::ifstream stream(root+"/r"+std::to_string(rank)+"/prog.hex");
        if(!stream)throw std::runtime_error("actual native program missing");
        std::vector<std::string> words;std::string w;
        while(stream>>w) {
            if(w.size()!=512 || w.find_first_not_of("0123456789abcdefABCDEF")!=std::string::npos)
                throw std::runtime_error("actual FULL_SHAPE program format");
            words.push_back(w);
        }
        return words;
    }
    static uint64_t bits(const std::string& w,int offset,int width) {
        uint64_t v=0;
        for(int i=0;i<width;i++) {
            char c=w.at(w.size()-1-(offset+i)/4);
            unsigned nibble=(c<='9') ? c-'0' : (c<='F' ? c-'A'+10 : c-'a'+10);
            v|=uint64_t((nibble>>((offset+i)%4))&1)<<i;
        }
        return v;
    }
ACCESSORS
public:
    explicit DsromS81NativeProgramBook(std::string directory):root(std::move(directory)) {
        for(int r=0;r<4;r++)programs[r]=read(r);
    }
    void bind(DsromS81NativeDrain& board,const DsromC8SourceOffer& offer,const std::string& node) const {
        if(node.empty())throw std::runtime_error("literal SourceExecution node missing");
        int r=offer.die_id%4;
        if(programs[r]!=read(r))throw std::runtime_error("native program changed since model initialization");
        const auto& p=programs[r];
        if(size_t(offer.entry)+1>=p.size())throw std::runtime_error("native source entry unbound");
        const auto& w=p[offer.entry];const auto& end=p[offer.entry+1];
        if(unit(end)!=0 || wait(end)!=31 || pred(end)!=0)
            throw std::runtime_error("selected fragment lacks native END/wait31 debt closure");
        uint64_t position=offer.position+dslot(w),pr=pred(w);
        bool execute=(pr==0 || (pr==1 && (position&1)) || (pr==2 && position!=0));
        if(pr>2)throw std::runtime_error("native source predicate unsupported");
        bool field=execute && ((unit(w)==3 && qe_mode(w)==0) || (unit(w)==1 && me_wsrc(w)==0));
        std::vector<DsromS81NativeDrain::Span> spans;
        if(field) {
            bool me=unit(w)==1;
            if((me && (me_d_obase(w) || me_d_nout(w))) || (!me && qe_d_obase(w)))
                throw std::runtime_error("dynamic output extent requires actual resolved source lease");
            uint64_t rows=me ? me_nout(w) : qe_nout(w);
            uint64_t base=(me ? me_obase(w)*16 : qe_obase(w));
            uint64_t stride=mx_ops(w)*(me ? 16 : 1);
            uint64_t positions=std::max<uint64_t>(1,mx_m(w));
            field=rows!=0;
            if(field)for(uint64_t j=0;j<positions;j++) {
                uint64_t address=base+j*stride;
                if(address+rows>(1u<<19))throw std::runtime_error("literal source output exceeds native VM19");
                spans.push_back({uint32_t(address),uint32_t(rows)});
            }
        }
        // Non-field entries require matched native retirement and all-copy
        // receipts, but do not fabricate field GO or ownership of their VM.
        // Their VM carry lease stays unavailable until that writer is enrolled.
        board.declare(offer,field,std::move(spans));
    }
};
'''.replace('ACCESSORS',accessors)


def one(source, old, new):
    if source.count(old)!=1:
        raise ValueError('native drain source anchor not unique: '+old[:90])
    return source.replace(old,new,1)


def emit(owner, out, *, wavefront=False):
    owner,out=Path(owner),Path(out)
    path=emit_scheduler(owner,out,wavefront=wavefront)
    # Enroll only the retained 16-lane non-relay transport namespace. A different
    # physical packet layout needs its own source binding, never a guessed bit.
    top=(owner/'rtl/dsrom_sys/c8/ot_v41_rt_die_l20_c8.sv').read_text()
    for declaration in ('parameter integer CL_LANES = 16,','parameter integer CL_RELAY = 0,'):
        if declaration not in top:raise ValueError('selected native transport changed')
    helper='tools/runtime/dsrom/s81_native_drain.hpp'
    (out/'s81_native_drain.hpp').write_bytes((ROOT/helper).read_bytes())
    (out/'s81_native_program_book.hpp').write_text(program_book())
    api=out/'dsrom_s81_scheduler_api.hpp'
    s=api.read_text()
    s=one(s,'struct DieBase {','#include "s81_native_drain.hpp"\nstruct DieBase {')
    s=one(s,'    virtual bool c8_ready()=0;',
          '    virtual DsromS81DrainSample drain_sample()=0;\n    virtual bool c8_ready()=0;')
    s=one(s,'    std::function<bool()> links_empty;',
          '    std::function<bool()> links_empty;\n'
          '    std::function<bool(const DsromC8SourceOffer&)> remote_drained, all_copies_drained;\n'
          '    std::function<void(const DsromC8SourceOffer&,const std::string&)> bind_receipt;\n'
          '    std::function<bool(int,uint64_t,uint32_t,size_t)> source_span_lease;')
    api.write_text(s)
    s=path.read_text()
    s=one(s,'    void capture_warm_reset(bool request) override {',r'''
    DsromS81DrainSample drain_sample() override {
        DsromS81DrainSample e;
        e.offer_accept=d->start && d->c8_offer_ready;
        e.offered_identity=d->c8_position_identity;e.token=d->token;e.entry=d->c8_entry;
        e.field_identity=d->capture_identity;e.field_live=d->capture_live;
        e.field_drained=d->capture_drained;e.warm_reset=d->capture_reset_request;
        e.retire=d->c8_retire_v;e.retire_identity=d->c8_retire_identity;
        e.fault=fault() || d->capture_fault || d->c8_stage_quarantine ||
                d->c8_write_quarantine || d->c8_write_fault || d->ckv_fault_code;
        e.vm_visible=capture_visible(e.field_identity);
        for(int r=0;r<128;r++)e.vm_commits+=getb(d->capture_vm_accept,r,1);
        e.pop_ucie=d->ucie_ccr_out;e.pop_board=d->bl_ccr_out;
        e.return_ucie=d->ucie_ccr_in;e.return_board=d->bl_ccr_in;
        return e;
    }
    void capture_warm_reset(bool request) override {''')
    # The source retains the excluded historical singleton main as well as the
    # executable scheduler. Instrument ONLY the scheduler's actual clock loop.
    native,s=s.split('#include <dlfcn.h>',1)
    s='#include "s81_native_program_book.hpp"\n'+s
    s=one(s,'        DsromS81Runtime runtime{};',
          '        DsromS81NativeProgramBook program_book(root);\n'
          '        DsromS81Runtime runtime{};')
    s=one(s,'    auto link_step = [&]() {',
          '    const char* stage_env=getenv("DSROM_S81_STAGE");\n'
          '    if(!stage_env)throw std::runtime_error("native drain stage required");\n'
          '    DsromS81NativeDrain drain_board(std::stoi(stage_env));\n'
          '    auto link_step = [&]() {')
    s=one(s,'                dies[s]->ucie_tx(rec);',
          '                dies[s]->ucie_tx(rec);\n'
          '                if(dies[s]->ucie_tx_v())drain_board.link_sent(s,peer,(rec.at(16)&1));')
    s=one(s,'if (v || c) { dies[s]->bl_tx(rec);',
          'if (v || c) { dies[s]->bl_tx(rec); if(v)drain_board.link_sent(s,dst,(rec.at(16)&1));')
    s=one(s,'            dies[d]->set_links(uv, ur, ucr, bv, b0, b1, bcr);',
          '''            if(uv)drain_board.link_injected(d^1,d,(ur.at(16)&1));
            if(ucr)drain_board.reverse_arrived(d,d^1,ucr);
            for(int J=0;J<2;J++) {
                int peer=2*(1-d/2)+J;
                if((bv>>J)&1)drain_board.link_injected(peer,d,((J?b1:b0).at(16)&1));
                unsigned cr=(bcr>>(2*J))&3;
                if(cr)drain_board.reverse_arrived(d,peer,cr);
            }
            dies[d]->set_links(uv, ur, ucr, bv, b0, b1, bcr);''')
    s=one(s,'                q.push_back({t, {rk, gid, row}});',
          '                drain_board.ckv_sent(s2,d2);\n                q.push_back({t, {rk, gid, row}});')
    s=one(s,'                    dies[d2]->ckv_rx(slot, true,',
          '                    drain_board.ckv_injected(s2,d2);\n                    dies[d2]->ckv_rx(slot, true,')
    s=one(s,'    auto tick = [&]() {',
          '    auto tick = [&]() {\n'
          '        std::array<DsromS81DrainSample,4> samples;\n'
          '        for(int r=0;r<4;r++)samples[r]=dies[r]->drain_sample();\n'
          '        drain_board.before_edge(samples);')
    s=one(s,'        link_step();',
          '        for(int r=0;r<4;r++)samples[r]=dies[r]->drain_sample();\n'
          '        drain_board.after_edge(samples);\n        link_step();')
    s=one(s,'        runtime.cycle=[&](){return cyc;};',
          '        runtime.cycle=[&](){return cyc;};\n'
          '        runtime.remote_drained=[&](const DsromC8SourceOffer& offer){return drain_board.drained(offer);};\n'
          '        runtime.all_copies_drained=runtime.remote_drained;\n'
          '        runtime.bind_receipt=[&](const DsromC8SourceOffer& offer,const std::string& node){program_book.bind(drain_board,offer,node);};\n'
          '        runtime.source_span_lease=[&](int die,uint64_t identity,uint32_t address,size_t words){return drain_board.source_span_lease(die,identity,address,words);};')
    path.write_text(native+'#include <dlfcn.h>\n'+s)
    return path


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--owner',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--wavefront',action='store_true')
    a=p.parse_args();print(emit(a.owner,a.out,wavefront=a.wavefront))
