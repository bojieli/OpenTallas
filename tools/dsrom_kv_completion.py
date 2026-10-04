"""Source-only actual KV completion join for Arch's reduced DS ROM system.

Reuse C8 backend receipt metadata, journal and pending-owner mux. Original
engine/source files and arithmetic remain unchanged. No host callbacks grant
visibility. Full-system execution stays with Archimedes.
"""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
PIN='1bfb4b6e855b723c06f8885ee1de4de950158c5a'
NATIVE='f6df84e14c2bc5908bdbf85b2bd95cd56b1f5520'

def original(path,pin=PIN):
    return subprocess.check_output(['git','show',pin+':'+path],cwd=ROOT,text=True)

def replace_once(s,old,new):
    if s.count(old)!=1:raise ValueError('source anchor missing/ambiguous: '+old[:100])
    return s.replace(old,new,1)

def add_ports(s,ports):
    k=s.index(');',s.index('module '))
    return s[:k]+',\n'+ports+'\n'+s[k:]

def prefetch_source():
    s=original('rtl/chip/ot_chip_v41x_kv_prefetch.sv',NATIVE)
    s=replace_once(s,'module ot_chip_v41x_kv_prefetch','module ot_dsrom_kv_prefetch_completion')
    s=add_ports(s,'output wire write_quiet,write_quarantine')
    return replace_once(s,'endmodule','''reg reset_quarantine=0;
 always @(posedge clk) if(!rst_n && (!wq_empty || (|we) || (|xwe))) reset_quarantine<=1;
 assign write_quarantine=reset_quarantine;
 assign write_quiet=wq_empty && !(|we) && !(|xwe) && !(|(m_v & m_we)) && !fault && !reset_quarantine;
endmodule''')

def mux_source():
    s=original('rtl/dsrom_sys/c8/ot_chip_v41x_kv_reqmux_c8.sv')
    s=replace_once(s,'module ot_chip_v41x_kv_reqmux_c8', 'module ot_dsrom_kv_reqmux_completion')
    s=add_ports(s,'output wire write_quiet,write_quarantine')
    s=replace_once(s,'    genvar s;', """    wire[3:0] pending_bits;reg reset_quarantine=0;
    always @(posedge clk) if(!rst_n && (|pending_bits)) reset_quarantine<=1;
    assign write_quarantine=reset_quarantine;
    assign write_quiet=rst_n && !(|pending_bits) && !(|(w_v&w_we)) && !(|(c_v&c_we)) && !reset_quarantine;
    genvar s;""")
    s=replace_once(s,'reg pending=0,owner_c=0;', 'reg pending=0,owner_c=0;\n        assign pending_bits[s]=pending;')
    return s

def credit_source():
    s=original('rtl/dsrom_sys/ot_chip_v41x_ckv_die_service_cr.sv')
    s=replace_once(s,'module ot_chip_v41x_ckv_die_service_cr #(', 'module ot_dsrom_ckv_credit_completion #(parameter integer KV_COMPLETION=0,')
    s=add_ports(s,'input wire [46:0] position_identity,\noutput wire own_pending, own_visible,\noutput wire [46:0] own_visible_identity,\noutput wire [POS_W-1:0] own_visible_gid')
    s=replace_once(s,'reg wr_act;', 'reg wr_act;\n    reg wr_pending,merge_complete;reg[46:0] write_identity;\n    assign own_pending=wr_act||wr_pending;\n    assign own_visible=KV_COMPLETION && wr_act && wr_pending && c_wr_done[wr_stack] && wr_k==8 && !fault;\n    assign own_visible_identity=write_identity;assign own_visible_gid=nw_gid;')
    s=replace_once(s,"wire w_this = wr_act && wr_stack == 2'(st);", "wire w_this = wr_act && (!KV_COMPLETION || !wr_pending) && wr_stack == 2'(st);")
    s=replace_once(s,'assign job_done = m_done;', 'assign job_done = KV_COMPLETION ? (merge_complete && !own_pending && !fault) : m_done;')
    s=replace_once(s,'wr_act <= 0; wr_k <= 0;', 'wr_act <= 0; wr_k <= 0;wr_pending<=0;merge_complete<=0;write_identity<=0;')
    s=replace_once(s,'// start: table complete and own row encoded', 'if (KV_COMPLETION && m_done) merge_complete<=1;\n            if (KV_COMPLETION && sel_v && !rd_act) merge_complete<=0;\n            // start: table complete and own row encoded')
    s=replace_once(s,'if (new_owned) begin wr_act <= 1; wr_k <= 0; end', 'if (new_owned) begin wr_act <= 1; wr_k <= 0;write_identity<=position_identity; end')
    old="""if (wr_act && c_rdy[wr_stack]) begin
                if (wr_k == 4'd8) wr_act <= 0; else wr_k <= wr_k + 1'b1;
            end"""
    new="""if (!KV_COMPLETION) begin
                if (wr_act && c_rdy[wr_stack]) begin
                    if (wr_k == 4'd8) wr_act <= 0; else wr_k <= wr_k + 1'b1;
                end
            end else begin
                if (wr_act && !wr_pending && c_rdy[wr_stack]) wr_pending<=1;
                if (|c_wr_done && (!wr_act || !wr_pending || c_wr_done!=(4'b1<<wr_stack))) begin
                    fault<=1;fault_code[5]<=1;
                end
                if (wr_act && wr_pending && c_wr_done[wr_stack]) begin
                    wr_pending<=0;
                    if(wr_k==8)wr_act<=0;else wr_k<=wr_k+1'b1;
                end
            end"""
    s=replace_once(s,old,new)
    # Keep AG_CREDIT receive FIFOs, generations, replay and arithmetic intact.
    return s

MUX="""
                    ot_dsrom_kv_reqmux_completion #(.HAW(28),.TAGW(16),.C8_PUBLICATION(1)) completion_mux(
                     .clk(clk),.rst_n(rst_n),.write_quiet(mux_write_quiet),.write_quarantine(mux_write_quarantine),.w_v(kq_v),.w_rdy(kq_rdy),.w_addr(kq_addr),.w_len(kq_len),.w_tag(kq_tag),
                     .w_we(kq_we),.w_wdata(kq_wdata),.w_wstrb(kq_wstrb),.w_wr_done(kq_done),
                     .w_sv(kq_sv),.w_srdy(kq_srdy),.w_stag(kq_stag),.w_sbeat(kq_sbeat),.w_sdata(kq_sdata),
                     .c_v(4'b0),.c_rdy(),.c_addr('0),.c_len('0),.c_tag('0),.c_we(4'b0),.c_wdata('0),.c_wstrb('0),
                     .c_wr_done(),.c_sv(),.c_srdy(4'b0),.c_stag(),.c_sbeat(),.c_sdata(),
                     .m_v(km_v),.m_rdy(km_rdy),.m_addr(km_addr),.m_len(km_len),.m_tag(km_tag),.m_we(km_we),
                     .m_wdata(km_wdata),.m_wstrb(km_wstrb),.m_wr_done(km_done),
                     .s_v(ks_v),.s_rdy(ks_rdy),.s_tag(ks_tag),.s_beat(ks_beat),.s_data(ks_data));
"""

def system_source():
    s=original('rtl/test/dsrom_sys/tb_dsrom_system.sv')
    s=replace_once(s,'module tb_dsrom_system #(', 'module tb_dsrom_system #(parameter integer KV_COMPLETION=0,')
    s=replace_once(s,'wire          c_start, c_done;', '''wire          c_start, c_done;
            wire kv_completion_quiet;
            reg[15:0] kv_completion_epoch=0;reg[46:0] kv_completion_identity=0;
            always @(posedge clk) if(KV_COMPLETION && rst_n && core_start) begin
              if(!kv_completion_quiet)$fatal(1,"KV context replaced with accepted write debt");
              kv_completion_epoch<=kv_completion_epoch+1'b1;
              kv_completion_identity<={16'(kv_completion_epoch+1'b1),10'(cur_u),21'(core_pos)};
            end''')
    s=replace_once(s,"assign c_done = PRIME ? (done && sh_st == 3'd0) : done;", "assign c_done = (PRIME ? (done && sh_st == 3'd0) : done) && (!KV_COMPLETION || kv_completion_quiet);")
    anchor='wire bridge_busy;'
    s=replace_once(s,anchor,anchor+'\n                wire[3:0] completion_quiet,completion_fault,completion_quarantine,km_done;\n                wire prefetch_write_quiet,prefetch_write_quarantine,mux_write_quiet,mux_write_quarantine;\n                assign kv_completion_quiet=(&completion_quiet)&&!(|completion_fault)&&!(|completion_quarantine)&&!bridge_busy&&prefetch_write_quiet&&!prefetch_write_quarantine&&mux_write_quiet&&!mux_write_quarantine&&!(|(km_v&km_we))&&!(|(h_v&h_we));')
    # Only the selected shared-stack path has actual backend completion metadata.
    start=s.index('if (`HDC_KV_HBM) begin : g_kv_hbm',s.index('if (`HDC_X_IDX == 2)'))
    end=s.index('end else begin : g_no_kv_hbm',start)
    block=s[start:end]
    block=replace_once(block,'wire [4:0] fault_code;', '''wire[3:0] kq_v,kq_rdy,kq_we,kq_done,kq_sv,kq_srdy;
                    wire[111:0] kq_addr;wire[15:0] kq_len,kq_sbeat;
                    wire[63:0] kq_tag,kq_stag;wire[1023:0] kq_wdata,kq_sdata;wire[127:0] kq_wstrb;
                    wire [4:0] fault_code;''')
    block=replace_once(block,'ot_chip_v41x_kv_prefetch #(', 'ot_dsrom_kv_prefetch_completion #(')
    # Local old port names to pending-owner mux front side.
    for name in ['v','rdy','addr','len','tag','we','wdata','wstrb']:
        block=replace_once(block,f'.m_{name}(km_{name})',f'.m_{name}(kq_{name})')
    for name in ['v','rdy','tag','beat','data']:
        target={'tag':'stag','beat':'sbeat','data':'sdata','v':'sv','rdy':'srdy'}[name]
        block=replace_once(block,f'.s_{name}(ks_{name})',f'.s_{name}(kq_{target})')
    block=replace_once(block,'.st_hold_cycles(kv_holds_w[n*32 +: 32]));', '.st_hold_cycles(kv_holds_w[n*32 +: 32]),.write_quiet(prefetch_write_quiet),.write_quarantine(prefetch_write_quarantine));'+MUX)
    s=s[:start]+block+s[end:]
    s=replace_once(s,'.k_wr_done(),','.k_wr_done(km_done[s]),')
    assert s.count('ot_hdc_v41x_idx_hbm #(.NPC(32), .AW(28)')==2
    s=s.replace('ot_hdc_v41x_idx_hbm #(.NPC(32), .AW(28)', 'ot_hdc_v41x_idx_hbm_c8 #(.NPC(32), .AW(28)',1)
    s=replace_once(s,'.wr_done(sh_wr_done),','.wr_done(sh_wr_done),.wr_done_addr(completion_addr),.wr_done_tag(completion_tag),')
    anchor='wire [32*32-1:0] sh_wstrb;'
    journal='''
                        wire[895:0] completion_addr;wire[543:0] completion_tag;wire[63:0] completion_writer;
                        for(genvar jp=0;jp<32;jp=jp+1)assign completion_writer[jp*2+:2]=sh_tag[jp*17+16]?2'b01:2'b00;
                        ot_dsrom_c8_write_journal #(.NPC(32),.DEPTH(64),.AW(28),.IDW(47),.TAGW(17)) completion_journal(
                         .clk(clk),.rst_n(rst_n),.accepted_write(sh_v&sh_rdy&sh_we),.backend_wr_done(sh_wr_done),
                         .accepted_addr(sh_addr),.accepted_tag(sh_tag),.accepted_writer(completion_writer),.accepted_identity(kv_completion_identity),
                         .backend_done_addr(completion_addr),.backend_done_tag(completion_tag),
                         .visible_v(),.visible_identity(),.visible_addr(),.visible_writer(),
                         .quiet(completion_quiet[s]),.debt(),.quarantine(completion_quarantine[s]),.fault(completion_fault[s]));
                        always @(posedge clk) if(KV_COMPLETION && rst_n && (completion_fault[s]||completion_quarantine[s]))
                         $fatal(1,"KV backend completion identity fault pkg=%0d stack=%0d",n,s);
'''
    s=replace_once(s,anchor,anchor+journal)
    # This installer opts into the successor as a whole; enable=False returns
    # the original source list, byte-identical. Refuse other frontend geometries.
    at=s.index('module tb_dsrom_system')
    body=s.index(');',at)+2
    s=s[:body]+'''\n initial if(!KV_COMPLETION || !`HDC_KV_HBM || `HDC_X_IDX!=2)
  $fatal(1,"KV completion source requires explicit KV_COMPLETION=1, pooled index and shared KV stacks");\n'''+s[body:]
    return s

def install(sources,output,*,enable=False):
    sources=[Path(p) for p in sources]
    if not enable:return dict(sources=sources,top='tb_dsrom_system',parameters={},verilator_args=[])
    tb=[p for p in sources if p.name=='tb_dsrom_system.sv']
    if len(tb)!=1 or tb[0].read_text()!=original('rtl/test/dsrom_sys/tb_dsrom_system.sv'):
        raise ValueError('actual pinned Arch system testbench required')
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    selected=out/'tb_dsrom_system.sv';selected.write_text(system_source())
    prefetch=out/'ot_dsrom_kv_prefetch_completion.sv';prefetch.write_text(prefetch_source())
    mux=out/'ot_dsrom_kv_reqmux_completion.sv';mux.write_text(mux_source())
    # Existing backend arithmetic/queues plus metadata outputs, existing journal
    # and mux. No duplicate engine or fake source-memory readiness.
    deps=[ROOT/'rtl/dsrom_sys/c8'/n for n in ['ot_hdc_v41x_idx_hbm_c8.sv','ot_dsrom_c8_write_journal.sv']]
    result=[selected if p==tb[0] else p for p in sources]
    result=list(dict.fromkeys(result+[prefetch,mux]+deps))
    return dict(sources=result,top='tb_dsrom_system',parameters={'KV_COMPLETION':1},verilator_args=['-GKV_COMPLETION=1'])


def install_credit_service(sources,output,*,caller,position_identity,own_pending='c8_own_pending',own_visible='c8_own_visible_v',own_visible_identity='c8_own_visible_identity',own_visible_gid='c8_own_visible_gid',enable=False):
    """Select the credit CKV completion copy only in a real C8 ACK parent.

    Arch supplies its selected enclosing source and actual captured identity
    signal. This does not install a new stage/lifecycle/context engine.
    """
    sources=[Path(p) for p in sources];caller=Path(caller)
    if not enable:return dict(sources=sources,parameters={},verilator_args=[])
    s=caller.read_text()
    if caller not in sources:raise ValueError('selected actual caller absent from source inventory')
    if not position_identity.isidentifier():raise ValueError('actual captured identity signal name required')
    for binding in (position_identity,own_pending,own_visible,own_visible_identity,own_visible_gid):
        if not binding.isidentifier() or binding not in s:raise ValueError('actual enclosing identity/visibility/quiet binding absent: '+binding)
    for dependency in ('ot_dsrom_c8_write_journal','ot_chip_v41x_kv_rope_reqmux_c8','ot_chip_v41x_hbm3e_phy_c8'):
        if dependency not in s:raise ValueError('selected parent needs actual C8 ACK dependency '+dependency)
    s=replace_once(s,'ot_chip_v41x_ckv_die_service_cr #(', 'ot_dsrom_ckv_credit_completion #(.KV_COMPLETION(C8_PUBLICATION),')
    k=s.index('ot_dsrom_ckv_credit_completion #(')
    tail=s[k:]
    if '.position_identity(' not in tail.split(');',1)[0]:
        tail=replace_once(tail,'.sel_v(', f'.position_identity({position_identity}),.own_pending({own_pending}),.own_visible({own_visible}),.own_visible_identity({own_visible_identity}),.own_visible_gid({own_visible_gid}),\n .sel_v(')
    s=s[:k]+tail
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    selected=out/caller.name;selected.write_text(s)
    service=out/'ot_dsrom_ckv_credit_completion.sv';service.write_text(credit_source())
    result=[selected if p==caller else p for p in sources]+[service]
    # Include the original credit engine's real dependencies; reuse an owner's
    # already selected copy by filename rather than introducing a second module.
    for name in ('ot_chip_v41x_ckv_sel_ids.sv','ot_chip_v41x_ckv_sel_fetch.sv',
                 'ot_chip_v41x_ckv_stream_merge.sv','ot_chip_v41x_ckv_selected_dma.sv',
                 'ot_chip_v41x_ckv_fp4_decode.sv','ot_chip_v41x_ckv_row_encoder.sv'):
        if not any(p.name==name for p in result): result.append(ROOT/'rtl/chip'/name)
    return dict(sources=result,parameters={'C8_PUBLICATION':1},verilator_args=['-GC8_PUBLICATION=1'])

# Strip inherited trailing whitespace only in generated successor copies.
def _clean_generated(generator):
    def generate():
        return '\n'.join(line.rstrip() for line in generator().splitlines())+'\n'
    return generate

prefetch_source=_clean_generated(prefetch_source)
mux_source=_clean_generated(mux_source)
credit_source=_clean_generated(credit_source)
system_source=_clean_generated(system_source)
