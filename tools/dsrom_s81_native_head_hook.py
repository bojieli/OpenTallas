"""Emit one additive selected core/adapter hookup; originals stay untouched."""
from pathlib import Path
import argparse,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
CORE=ROOT/'rtl/dsrom_sys/s81_capture_parent/ot_hdc_core_v41x.sv'
ADAPT=ROOT/'rtl/dsrom_sys/s81_capture_parent/ot_v41_rom_adapt.sv'

def emit(out):
    out.mkdir(parents=True,exist_ok=False)
    a=ADAPT.read_text();c=CORE.read_text()
    a=a.replace('parameter integer S81_CAPTURE=0,','parameter integer S81_CAPTURE=0,\n    parameter integer OPT_NATIVE_HEAD=0,')
    a=a.replace('m_round && !m_amax && !m_mmode;',"!m_mmode && ((m_round && !m_amax) || (OPT_NATIVE_HEAD && m_amax && !m_round && m_k==NW'(5120) && m_split==0));")
    a=a.replace("if (!m_ok) fault <= 1'b1;\n                        st <= S_LOOK;","if (!m_ok) fault <= 1'b1;\n                        st <= (OPT_NATIVE_HEAD && !m_ok) ? S_IDLE : S_LOOK;")
    a=a.replace("s_ph <= hit_p; st <= S_GO;","s_ph <= hit_p; st <= (OPT_NATIVE_HEAD && (!hit || fault)) ? S_IDLE : S_GO;")
    c=c.replace('parameter integer S81_CAPTURE=0,','parameter integer S81_CAPTURE=0,\n    parameter integer OPT_NATIVE_HEAD=0,')
    c=c.replace('input wire capture_command_ready,','input wire capture_command_ready,') # header remains source-owned
    anchor='    input wire [ROM_R*19-1:0] capture_root_rows,'
    assert anchor in c
    ports='''    input wire head_up_valid, head_up_last,
    output wire head_up_ready,
    input wire [511:0] head_up_data,
    input wire [46:0] head_up_identity,
    output wire head_dn_valid, head_dn_last,
    input wire head_dn_ready,
    input wire head_final_valid,
    output wire head_final_ready,
    input wire [511:0] head_final_data,
    input wire [46:0] head_final_identity,
    output wire [511:0] head_dn_data,
    output wire [46:0] head_dn_identity,
'''
    c=c.replace(anchor,ports+anchor)
    c=c.replace('localparam integer EAM = (X_ME != 0) ? 1 : 0;','localparam integer EAM = ((X_ROM != 0 && OPT_NATIVE_HEAD) || X_ME != 0) ? 1 : 0;')
    c=c.replace('    wire rom_m_go = e_go[1];','''    wire rom_m_go = e_go[1];
    wire head_busy,head_seen,head_fault;
    wire [NW-1:0] head_idx;
    wire [31:0] head_val;
    wire head_any;
    generate if(X_ROM && OPT_NATIVE_HEAD) begin:g_native_head
        initial if(MP!=1 || NSLOT!=1 || !S81_CAPTURE) $fatal(1,"minimum native head requires selected MP1/NSLOT1 capture path");
        ot_dsrom_s81_head_amax #(.R(ROM_R),.AW(AW),.NW(NW),.RANK(RANK)) u_head (
            .clk(clk),.rst_n(rst_n),.start(rom_m_go && me_amax),
            .identity(capture_identity),.nout(me_nout),.obase(me_obase*AW'(W)),
            .write_valid(rom_we),.write_accept(capture_vm_accept),.write_address(rom_waddr),.write_bits(rom_wdata),
            .upstream_valid(head_up_valid),.upstream_ready(head_up_ready),.upstream_data(head_up_data),
            .upstream_last(head_up_last),.upstream_identity(head_up_identity),
            .downstream_valid(head_dn_valid),.downstream_ready(head_dn_ready),.downstream_data(head_dn_data),
            .downstream_last(head_dn_last),.downstream_identity(head_dn_identity),
            .final_valid(head_final_valid),.final_ready(head_final_ready),.final_data(head_final_data),.final_identity(head_final_identity),
            .busy(head_busy),.result_seen(head_seen),.am_idx(head_idx),.am_val(head_val),.am_any(head_any),.fault(head_fault));
    end else begin:g_no_native_head
        assign head_busy=0;assign head_seen=0;assign head_fault=0;assign head_idx=0;assign head_val=0;assign head_any=0;
        assign head_final_ready=0;assign head_up_ready=0;assign head_dn_valid=0;assign head_dn_last=0;assign head_dn_data=0;assign head_dn_identity=0;
    end endgenerate''')
    c=c.replace('assign e_ready[1] = rom_ready_w;', 'assign e_ready[1] = rom_ready_w && !head_busy;')
    c=c.replace('assign e_idle[1] = rom_idle_w; assign e_fault[1] = 1\'b0;',"assign e_idle[1] = rom_idle_w && !head_busy; assign e_fault[1] = head_fault;")
    c=c.replace('assign e_am_idx[1*MP*NW +: MP*NW] = 0;',"assign e_am_idx[1*MP*NW +: MP*NW] = OPT_NATIVE_HEAD ? head_idx : 0;",1)
    c=c.replace('assign e_am_val[1*MP*32 +: MP*32] = 0; assign e_am_any[1*MP +: MP] = 0;',"assign e_am_val[1*MP*32 +: MP*32] = OPT_NATIVE_HEAD ? head_val : 0; assign e_am_any[1*MP +: MP] = OPT_NATIVE_HEAD ? head_any : 0;",1)
    c=c.replace('.S81_CAPTURE(S81_CAPTURE),.AW(AW)', '.OPT_NATIVE_HEAD(OPT_NATIVE_HEAD),.S81_CAPTURE(S81_CAPTURE),.AW(AW)',1)
    (out/CORE.name).write_text(c);(out/ADAPT.name).write_text(a)
    (out/'source_diff_receipt.json').write_text(json.dumps({'original_source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [CORE,ADAPT]},'selected_source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.sv')},'opt_in_default':False,'ME_head_output_format':'existing s_fmt1 FP32 unchanged','no_new_dot':True},indent=2)+'\n')


def winner_binding_source():
    """Caller-only binding to actual head_final and the existing result reader.

    No core/leaf shim, clock, reader, source-PC allocation or completion output
    is created. Arch supplies the actual Top, accepted context and existing
    reader, and calls consumed() only from its real result-consumption path.
    """
    import re
    package=ROOT/'rtl/rom/collectives/ot_rom_coll_pkg.sv'
    raw=package.read_bytes();text=raw.decode()
    fields={}
    for name in ('H_KIND','H_ARG_VAL','H_ARG_ID','H_ARG_OK'):
        matches=re.findall(r'localparam\s+integer\s+'+name+r'\s*=\s*(\d+)\s*;',text)
        if len(matches)!=1:raise ValueError('actual collective package field changed: '+name)
        fields[name]=int(matches[0])
    kind=re.findall(r"localparam\s+\[(\d+):0\]\s+K_ARGMAX\s*=\s*(\d+)'d(\d+)\s*;",text)
    if len(kind)!=1 or int(kind[0][0])+1!=int(kind[0][1]):
        raise ValueError('actual collective ARGMAX width/value required')
    fields['KIND_WIDTH']=int(kind[0][1]);fields['K_ARGMAX']=int(kind[0][2])
    src=r'''#pragma once
#include "s81_native_head_argmax.hpp"
#include "s81_native_head_collective.hpp"
#include "s81_wavefront_native_result_read.hpp"
// Generated from rtl/rom/collectives/ot_rom_coll_pkg.sv SHA256 @PKG_SHA@.
// Host glue only. All flags/outputs below are REAL selected native ports.
// Bind ONCE to the authoritative END/ReadResult consumer; caller retains TP4
// destination routing. Do not register a second head_final driver/ACK owner.
inline DsromS81NativeHeadRecord dsrom_s81_native_head_winner_frame(
    const DsromS81HeadArgmaxResult& actual) {
    if(actual.identity>=(1ull<<47)||actual.global_id>=129280||
       ((actual.bits>>23)&255)==255)
        throw std::runtime_error("native held winner owner/ID/finite payload");
    DsromS81NativeHeadRecord frame;frame.identity=actual.identity;frame.last=true;
    auto put=[&](unsigned offset,unsigned width,uint32_t value) {
        if(width==0||width>32||offset+width>512||uint64_t(value)>=(1ull<<width))
            throw std::runtime_error("source ARGMAX frame field width");
        for(unsigned i=0;i<width;++i)
            frame.data[(offset+i)/32]|=((value>>i)&1u)<<((offset+i)%32);
    };
    put(@H_KIND@,@KIND_WIDTH@,@K_ARGMAX@);
    put(@H_ARG_VAL@,32,actual.bits);put(@H_ARG_ID@,32,actual.global_id);
    put(@H_ARG_OK@,1,1); // actual adapter.result() exists; never drives core am_any
    return frame;
}

template<class Top> class DsromS81NativeHeadWinnerBinding {
    Top& top;
    std::shared_ptr<DsromS81NativeHeadArgmax> producer;
    std::shared_ptr<DsromS81WaveNativeResultRead<Top>> reader;
    const DsromS81NativeResultTerminal terminal;
    const uint64_t sequence;
    bool enabled,driven=false,sampled=false,take=false,taken=false;
    bool read_seen=false,consumed_once=false,stopped=false;
    std::optional<DsromS81HeadArgmaxResult> held;
    DsromS81NativeHeadRecord frame;
    static void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
    static bool same(const DsromS81HeadArgmaxResult& a,const DsromS81HeadArgmaxResult& b){
        return a.identity==b.identity&&a.sequence==b.sequence&&
               a.global_id==b.global_id&&a.bits==b.bits;
    }
    void healthy()const {
        require(!stopped&&!producer->fault()&&!reader->fault()&&!top.fault,
                "native head winner binding quarantined; debt retained");
    }
    void match(const DsromS81WaveStageResult& result)const {
        require(held&&result.identity==held->identity&&
                result.request_sequence==held->sequence&&result.next_token==held->global_id&&
                result.next_value==held->bits,"real END/ReadResult differs from held winner");
    }
public:
    DsromS81NativeHeadWinnerBinding(Top& actual_top,
        std::shared_ptr<DsromS81NativeHeadArgmax> actual_producer,
        std::shared_ptr<DsromS81WaveNativeResultRead<Top>> existing_reader,
        DsromS81NativeResultTerminal actual_terminal,uint64_t accepted_sequence,bool enable=false)
        :top(actual_top),producer(std::move(actual_producer)),reader(std::move(existing_reader)),
         terminal(std::move(actual_terminal)),sequence(accepted_sequence),enabled(enable) {
        require(producer&&reader,"actual held native producer and EXISTING reader required");
        DsromC8SourceDispatch checked(terminal.offer);
        require(!terminal.source_node.empty()&&terminal.producer_pc<(1u<<14)&&
            terminal.end_pc<(1u<<14)&&terminal.offer.entry<=terminal.producer_pc&&
            terminal.producer_pc<terminal.end_pc,"caller must supply emitted producer/END PCs");
        if(enabled)require(top.native_head_selected&&top.native_result_selected,
                          "actual selected head/result destination absent");
    }
    // Arch: drive -> settle actual native Top -> sample -> ONE shared rising
    // and settle -> after_edge. Do NOT additionally sample/advance reader;
    // these methods reuse that SAME existing reader. No eval/tick/reset here.
    void drive_before_edge() {
        if(!enabled)return;
        try {
            healthy();require(!driven&&!sampled&&top.rst_n,"head frame edge reused/reset");
            if(!consumed_once) {
                auto actual=producer->result();
                if(actual) {
                    require(actual->identity==terminal.offer.identity&&actual->sequence==sequence,
                            "native winner differs from accepted full identity/sequence");
                    if(held)require(same(*held,*actual),"native producer changed held winner");
                    else {held=actual;frame=dsrom_s81_native_head_winner_frame(*actual);}
                } else require(!held,"native producer released winner before consumption");
            }
            if(held&&!taken)require(top.native_result_active&&
                uint64_t(top.native_result_identity)==terminal.offer.identity&&
                uint32_t(top.native_result_entry)==terminal.offer.entry,
                "actual head destination has wrong active source entry/identity");
            top.head_final_valid=held&&!taken&&!consumed_once;
            top.head_final_identity=held?frame.identity:0;
            for(unsigned i=0;i<16;++i)top.head_final_data[i]=held?frame.data[i]:0;
            // Never write head_final_ready, head_dn_ready, forwarded, core
            // am_any, producer_take, END/done or c8_retire. Their owners remain native.
            driven=true;
        }catch(...){stopped=true;throw;}
    }
    void sample_before_edge() {
        if(!enabled)return;
        try {
            healthy();require(driven&&!sampled&&top.rst_n,"head frame not driven/settled");
            const bool valid=held&&!taken&&!consumed_once;
            require(bool(top.head_final_valid)==valid,"head final offer overwritten");
            if(held) {
                require(uint64_t(top.head_final_identity)==frame.identity,"head final identity overwritten");
                for(unsigned i=0;i<16;++i)require(top.head_final_data[i]==frame.data[i],"head final data overwritten");
            }
            take=valid&&bool(top.head_final_ready); // REAL OLD ready, not post-edge ready
            reader->sample_before_edge();sampled=true;
        }catch(...){stopped=true;throw;}
    }
    void after_edge() {
        if(!enabled)return;
        try {
            healthy();require(driven&&sampled&&top.rst_n,"head final edge not sampled");
            reader->after_edge(); // actual producer/END/output plus matching C8 retirement
            if(take){require(held&&!taken,"duplicate native final acceptance");taken=true;}
            driven=false;sampled=false;take=false;
        }catch(...){stopped=true;throw;}
    }
    // Exact existing StagePoller::ReadResult signature. Returning a real result
    // is NOT its consumption and never ACKs/releases the native producer.
    std::optional<DsromS81WaveStageResult> read_result(const DsromC8SourceOffer& offer) {
        if(!enabled)return std::nullopt;
        try {
            healthy();require(!consumed_once,"ReadResult after consumption");
            auto result=(*reader)(offer);
            if(result){require(taken,"END output before actual head_final acceptance");match(*result);read_seen=true;}
            return result;
        }catch(...){stopped=true;throw;}
    }
    // Arch calls ONLY after its actual poller/consumer has consumed the returned
    // result under its KV/index/remote/allcopy fences. Never on final_ready or END alone.
    void consumed(const DsromS81WaveStageResult& actual_accepted) {
        if(!enabled)return;
        try {
            healthy();require(taken&&read_seen&&!consumed_once,
                              "native winner ACK before real END/ReadResult consumption");
            match(actual_accepted);producer->acknowledge(*held);consumed_once=true;
        }catch(...){stopped=true;throw;}
    }
    void warm_quarantine(){stopped=true;} // do not erase held frame/native debt
    bool fault()const{return stopped||(enabled&&(producer->fault()||reader->fault()||top.fault));}
};

template<class Top>
auto dsrom_s81_bind_native_head_winner(Top& actual_top,
    std::shared_ptr<DsromS81NativeHeadArgmax> producer,
    std::shared_ptr<DsromS81WaveNativeResultRead<Top>> existing_reader,
    DsromS81NativeResultTerminal terminal,uint64_t accepted_sequence,bool enable=false) {
    return std::make_shared<DsromS81NativeHeadWinnerBinding<Top>>(actual_top,
        std::move(producer),std::move(existing_reader),std::move(terminal),accepted_sequence,enable);
}

template<class Binding>
auto dsrom_s81_native_head_winner_read_result_callback(std::shared_ptr<Binding> binding)
    -> std::function<std::optional<DsromS81WaveStageResult>(const DsromC8SourceOffer&)> {
    if(!binding)throw std::runtime_error("actual native head winner binding required");
    return [binding](const DsromC8SourceOffer& offer){return binding->read_result(offer);};
}
'''
    src=src.replace('@PKG_SHA@',hashlib.sha256(raw).hexdigest())
    for name,value in fields.items():src=src.replace('@'+name+'@',str(value))
    return src


def emit_winner_binding(out):
    """Emit a caller helper only; do not regenerate/build the selected native RTL."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    dest=out/'s81_native_head_winner_binding.hpp';source=winner_binding_source()
    if dest.exists() and dest.read_text()!=source:raise FileExistsError(dest)
    if not dest.exists():dest.write_text(source)
    return dest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);emit(p.parse_args().out)
