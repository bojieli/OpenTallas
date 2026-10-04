#!/usr/bin/env python3
"""Additive native L20 C8 publication sources. Original source pins unchanged."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN='f6df84e14c2bc5908bdbf85b2bd95cd56b1f5520'
OUT=ROOT/'rtl/dsrom_sys/c8'

def original(path):
 return subprocess.check_output(['git','show',PIN+':'+path],cwd=ROOT,text=True)

def extra_ports(s,text):
 i=s.index('\n);');return s[:i].rstrip()+',\n'+text+s[i:]

def generate():
 # Require source-sized prebuild reservation before generating engine copies.
 model=json.loads((ROOT/'results/uarch/dsrom_c8_publication_20261003/model.json').read_text())
 assert model['admission']['isolated_actual_backend_functional']
 receipts={}
 def emit(path,s):
  q=OUT/path;q.write_text(s);receipts[str(q.relative_to(ROOT))]=hashlib.sha256(q.read_bytes()).hexdigest()
 s=original('rtl/chip/ot_chip_v41x_kv_reqmux.sv').replace('module ot_chip_v41x_kv_reqmux #(','module ot_chip_v41x_kv_reqmux_c8 #(\n    parameter integer C8_PUBLICATION=0,')
 s=extra_ports(s,'    input wire clk,rst_n')
 s=s.replace('wire choose_w = w_v[s];','reg pending=0,owner_c=0;\n        wire hold_write=C8_PUBLICATION && pending;\n        wire choose_w = w_v[s];\n        always @(posedge clk) begin\n          if (!rst_n) begin pending<=0; owner_c<=0; end\n          else if (C8_PUBLICATION) begin\n            if (m_wr_done[s] && pending) pending<=0;\n            if (m_v[s] && m_rdy[s] && m_we[s]) begin pending<=1;owner_c<=!choose_w;end\n          end\n        end')
 s=s.replace('w_v[s] || c_v[s]','rst_n && !hold_write && (w_v[s] || c_v[s])')
 # Replace complete assignments; substring replacement also matches the
 # negated C predicate and formerly turned !choose_w into !rst_n.
 for client,predicate in [('w','choose_w'),('c','!choose_w')]:
  old=f'assign {client}_rdy[s] = {predicate} && m_rdy[s];'
  new=f'assign {client}_rdy[s] = rst_n && !hold_write && {predicate} && m_rdy[s];'
  assert s.count(old)==1
  s=s.replace(old,new)
 s=s.replace("choose_w ? w_we[s] : 1'b0","choose_w ? w_we[s] : (C8_PUBLICATION ? c_we[s] : 1'b0)")
 s=s.replace("choose_w ? w_wdata[s*256 +: 256] : '0","choose_w ? w_wdata[s*256 +: 256] : (C8_PUBLICATION ? c_wdata[s*256 +: 256] : '0)")
 s=s.replace("choose_w ? w_wstrb[s*32 +: 32] : '0","choose_w ? w_wstrb[s*32 +: 32] : (C8_PUBLICATION ? c_wstrb[s*32 +: 32] : '0)")
 s=s.replace('assign w_wr_done[s] = m_wr_done[s];','assign w_wr_done[s] = C8_PUBLICATION ? (rst_n && pending && !owner_c && m_wr_done[s]) : m_wr_done[s];')
 s=s.replace("assign c_wr_done[s] = 1'b0;","assign c_wr_done[s] = C8_PUBLICATION && rst_n && pending && owner_c && m_wr_done[s];")
 emit('ot_chip_v41x_kv_reqmux_c8.sv',s)
 s=original('rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv').replace('module ot_chip_v41x_kv_rope_reqmux #(','module ot_chip_v41x_kv_rope_reqmux_c8 #(\n    parameter integer C8_PUBLICATION=0,')
 s=s.replace('&& !c_we[s]','&& (!c_we[s] || C8_PUBLICATION)')
 s=s.replace('|| c_we[s]))','|| (c_we[s] && !C8_PUBLICATION)))')
 s=s.replace('ot_chip_v41x_kv_reqmux #(.HAW(HAW), .TAGW(TAGW-1))','ot_chip_v41x_kv_reqmux_c8 #(.C8_PUBLICATION(C8_PUBLICATION), .HAW(HAW), .TAGW(TAGW-1))')
 s=s.replace('.w_v(w_req_v),','.clk(clk),.rst_n(rst_n),.w_v(w_req_v),')
 emit('ot_chip_v41x_kv_rope_reqmux_c8.sv',s)
 s=original('rtl/chip/ot_chip_v41x_ckv_die_service.sv').replace('module ot_chip_v41x_ckv_die_service #(','module ot_chip_v41x_ckv_die_service_c8 #(\n    parameter integer C8_PUBLICATION=0,')
 s=extra_ports(s,'    input wire [46:0] position_identity,\n    output reg own_visible_v,\n    output reg [46:0] own_visible_identity,\n    output reg [POS_W-1:0] own_visible_gid,\n    output wire own_pending,\n    output wire reuse_ready')
 s=s.replace('reg wr_act;','reg wr_act;\n    reg wr_pending;reg [46:0] own_identity;\n    assign own_pending=wr_act || wr_pending;')
 s=s.replace("wr_act && wr_stack == 2'(st)","wr_act && wr_stack == 2'(st) && (!C8_PUBLICATION || !wr_pending)")
 s=s.replace('step <= 0; go <= 0;', 'wr_pending<=0;own_visible_v<=0;own_visible_identity<=0;own_visible_gid<=0;own_identity<=0;\n            step <= 0; go <= 0;',1)
 s=s.replace('cyc <= cyc + 1;','cyc <= cyc + 1;own_visible_v<=0;',1)
 s=s.replace("nw_gid <= POS_W'(nw_addr >> 9);","nw_gid <= POS_W'(nw_addr >> 9);own_identity<=position_identity;")
 old="""if (wr_act && c_rdy[wr_stack]) begin
                if (wr_k == 4'd8) wr_act <= 0; else wr_k <= wr_k + 1'b1;
            end"""
 new="""if (!C8_PUBLICATION) begin
                if (wr_act && c_rdy[wr_stack]) begin
                    if (wr_k == 4'd8) wr_act<=0; else wr_k<=wr_k+1'b1;
                end
            end else begin
                if (wr_act && !wr_pending && c_rdy[wr_stack]) wr_pending<=1;
                if (wr_act && wr_pending && c_wr_done[wr_stack]) begin
                    wr_pending<=0;
                    if (wr_k==4'd8) begin
                        wr_act<=0;own_visible_v<=1;own_visible_identity<=own_identity;own_visible_gid<=nw_gid;
                    end else wr_k<=wr_k+1'b1;
                end
            end"""
 assert old in s;s=s.replace(old,new)
 # Positive local reuse: fetch output and merger/ID reader must actually
 # finish before another context can replace the table or overwrite nw_gid.
 s=s.replace('assign own_pending=wr_act || wr_pending;',
             "assign own_pending=wr_act || wr_pending;\n    assign reuse_ready=rst_n && !fault && f_ready && !f_ov && !f_job && !rel_on && !rd_act && !rq_v && tail==0 && !own_pending && !enc_busy && !enc_go && !nw_have && nw_got==0 && !new_sel_pulse && !sel_v && !nw_we;")
 s=s.replace('wire rel_ok = step && m_jready && !rel_on;', 'wire rel_ok = step && m_jready && !rel_on && (!C8_PUBLICATION || (rows_ready && !own_pending));')
 # The original unconditional collector count assignment is later in the
 # same always block than selection clear. It otherwise overrides npresent=0
 # on every second selection. Keep legacy default byte-level behavior, and
 # make the selected publisher clear win without changing arithmetic.
 s=s.replace("npresent <= npresent + (KW+1)'(nwr);",
             "if (C8_PUBLICATION && sel_v && !rd_act) npresent <= 0;\n            else npresent <= npresent + (KW+1)'(nwr);")
 emit('ot_chip_v41x_ckv_die_service_c8.sv',s)
 # Native backend exposes metadata from the ACTUAL serviced queue entry.
 s=original('rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv').replace('module ot_hdc_v41x_idx_hbm #(', 'module ot_hdc_v41x_idx_hbm_c8 #(')
 s=extra_ports(s,'    output reg [NPC*AW-1:0] wr_done_addr,\n    output reg [NPC*TAGW-1:0] wr_done_tag')
 s=s.replace('cyc <= 0; rsp_v <= 0; wr_done <= 0;', 'cyc <= 0; rsp_v <= 0; wr_done <= 0;wr_done_addr<=0;wr_done_tag<=0;')
 s=s.replace("wr_done[p] <= 1'b1;", "wr_done[p] <= 1'b1;wr_done_addr[p*AW+:AW]<=q_addr[p][slot];wr_done_tag[p*TAGW+:TAGW]<=q_tag[p][slot];")
 emit('ot_hdc_v41x_idx_hbm_c8.sv',s)
 s=original('rtl/chip/ot_chip_v41x_hbm3e_phy.sv').replace('module ot_chip_v41x_hbm3e_phy #(', 'module ot_chip_v41x_hbm3e_phy_c8 #(')
 s=extra_ports(s,'    output wire [NPC*K_AW-1:0] k_wr_done_addr,\n    output wire [NPC*KTAGW-1:0] k_wr_done_tag')
 s=s.replace('ot_hdc_v41x_idx_hbm #(', 'ot_hdc_v41x_idx_hbm_c8 #(')
 s=s.replace('.wr_done(k_wr_done),', '.wr_done(k_wr_done),.wr_done_addr(k_wr_done_addr),.wr_done_tag(k_wr_done_tag),')
 emit('ot_chip_v41x_hbm3e_phy_c8.sv',s)
 # Actual owner-safe L20 parent: existing compute/arithmetic sources retained.
 s=original('rtl/chip/window_owner_safe/ot_chip_v41x_die_owner_safe.sv').replace('module ot_chip_v41x_die_owner_safe #(', 'module ot_chip_v41x_die_owner_safe_c8 #(\n    parameter integer C8_PUBLICATION=0,')
 s=extra_ports(s, '    input wire [46:0] c8_position_identity,\n    output wire c8_write_quiet,c8_write_quarantine,c8_write_fault,\n    output wire [127:0] c8_visible_v,\n    output wire [128*47-1:0] c8_visible_identity,\n    output wire [128*K_HAW-1:0] c8_visible_addr,\n    output wire [255:0] c8_visible_writer,\n    output wire c8_own_pending, c8_own_visible_v,\n    output wire [46:0] c8_own_visible_identity,\n    output wire [20:0] c8_own_visible_gid')
 s=s.replace('ot_chip_v41x_ckv_die_service #(', 'ot_chip_v41x_ckv_die_service_c8 #(.C8_PUBLICATION(C8_PUBLICATION),')
 s=s.replace('.sel_v(ckv_sel_v),', '.position_identity(c8_position_identity),.own_pending(c8_own_pending),.reuse_ready(c8_ckv_reuse_ready),.own_visible_v(c8_own_visible_v),.own_visible_identity(c8_own_visible_identity),.own_visible_gid(c8_own_visible_gid),\n                .sel_v(ckv_sel_v),')
 s=s.replace('end else begin : g_no_ckv', "end else begin : g_no_ckv\n            assign c8_ckv_reuse_ready=1;assign c8_own_pending=0;assign c8_own_visible_v=0;assign c8_own_visible_identity=0;assign c8_own_visible_gid=0;")
 s=s.replace('ot_chip_v41x_kv_rope_reqmux #(', 'ot_chip_v41x_kv_rope_reqmux_c8 #(.C8_PUBLICATION(C8_PUBLICATION),')
 s=s.replace('wire [127:0] kh_v,', 'wire c8_ckv_reuse_ready;\n    wire [3:0] c8_jquiet,c8_jquarantine,c8_jfault;\n    assign c8_write_quiet=(&c8_jquiet) && !kb_busy && !c8_own_pending && c8_ckv_reuse_ready && !win_service_busy && window_prime_ready && !win_blk_v && !(|(kh_v & kh_we)) && !(|(pm_v & pm_we));\n    assign c8_write_quarantine=|c8_jquarantine;assign c8_write_fault=|c8_jfault;\n    wire [127:0] kh_v,')
 anchor='wire [31:0] h_v, h_rdy, h_we, h_wr_done, r_v, r_rdy;'
 assert s.count(anchor)==1
 journal="""
        wire [63:0] c8_kind;wire [32*K_HAW-1:0] c8_done_addr;wire [32*17-1:0] c8_done_tag;
        for(genvar jp=0;jp<32;jp=jp+1) begin:g_c8_kind
            assign c8_kind[jp*2+:2]=h_tag[jp*17+16] ? {1'b1,h_tag[jp*17+14]} : 2'b00;
        end
        if(C8_PUBLICATION) begin:g_c8_journal
            ot_dsrom_c8_write_journal #(.NPC(32),.DEPTH(64),.AW(K_HAW),.IDW(47)) u_journal(
              .clk(clk),.rst_n(rn),.accepted_write(h_v & h_rdy & h_we),.backend_wr_done(h_wr_done),
              .accepted_addr(h_addr),.accepted_tag(h_tag),.backend_done_addr(c8_done_addr),.backend_done_tag(c8_done_tag),.accepted_writer(c8_kind),.accepted_identity(c8_position_identity),
              .visible_v(c8_visible_v[s*32+:32]),.visible_identity(c8_visible_identity[s*32*47+:32*47]),
              .visible_addr(c8_visible_addr[s*32*K_HAW+:32*K_HAW]),.visible_writer(c8_visible_writer[s*64+:64]),
              .quiet(c8_jquiet[s]),.debt(),.quarantine(c8_jquarantine[s]),.fault(c8_jfault[s]));
        end else begin:g_no_c8_journal
            assign c8_visible_v[s*32+:32]=0;assign c8_visible_identity[s*32*47+:32*47]=0;
            assign c8_visible_addr[s*32*K_HAW+:32*K_HAW]=0;assign c8_visible_writer[s*64+:64]=0;
            assign c8_jquiet[s]=1;assign c8_jquarantine[s]=0;assign c8_jfault[s]=0;
        end
"""
 s=s.replace(anchor,anchor+journal)
 s=s.replace('ot_chip_v41x_hbm3e_phy #(', 'ot_chip_v41x_hbm3e_phy_c8 #(')
 s=s.replace('.k_wr_done(h_wr_done),','.k_wr_done(h_wr_done),.k_wr_done_addr(c8_done_addr),.k_wr_done_tag(c8_done_tag),')
 emit('ot_chip_v41x_die_owner_safe_c8.sv',s)
 s=original('rtl/chip/window_owner_safe/ot_v41_rt_die_l20_owner_safe.sv').replace('module ot_v41_rt_die_l20_owner_safe #(', 'module ot_v41_rt_die_l20_c8 #(\n    parameter integer C8_PUBLICATION=0,\n    parameter integer C8_CONTEXT=0,')
 s=extra_ports(s,'    input wire [13:0] c8_entry,\n    input wire c8_context_restored,\n    output wire c8_offer_ready,c8_context_v,c8_retire_v,c8_stage_active,c8_stage_quarantine,\n    output wire [46:0] c8_context_identity,c8_retire_identity,\n    output wire [20:0] c8_context_token,\n    output wire [13:0] c8_context_entry,\n    input wire [46:0] c8_position_identity,\n    output wire c8_write_quiet,c8_write_quarantine,c8_write_fault,\n    output wire [127:0] c8_visible_v,\n    output wire [128*47-1:0] c8_visible_identity,\n    output wire [128*30-1:0] c8_visible_addr,\n    output wire [255:0] c8_visible_writer,\n    output wire c8_own_pending,c8_own_visible_v,\n    output wire [46:0] c8_own_visible_identity,\n    output wire [20:0] c8_own_visible_gid')
 s=s.replace('ot_chip_v41x_die_owner_safe #(', 'ot_chip_v41x_die_owner_safe_c8 #(.C8_PUBLICATION(C8_PUBLICATION),')
 s=s.replace('.host_mode(1\'b1),', '.c8_position_identity(c8_position_identity),.c8_write_quiet(c8_write_quiet),.c8_write_quarantine(c8_write_quarantine),.c8_write_fault(c8_write_fault),\n        .c8_visible_v(c8_visible_v),.c8_visible_identity(c8_visible_identity),.c8_visible_addr(c8_visible_addr),.c8_visible_writer(c8_visible_writer),\n        .c8_own_pending(c8_own_pending),.c8_own_visible_v(c8_own_visible_v),.c8_own_visible_identity(c8_own_visible_identity),.c8_own_visible_gid(c8_own_visible_gid),\n        .host_mode(1\'b1),')
 # Actual retained core entry / native write callbacks, not an external
 # assumed retirement tuple. The old start/token/pos/user path is unchanged
 # unless C8_CONTEXT is selected. The caller must hold offers until ready and
 # restore the real VM context before pulsing c8_context_restored.
 s=s.replace('.c8_position_identity(c8_position_identity)', '.c8_position_identity(C8_CONTEXT ? c8_engine_identity : c8_position_identity)')
 for port,legacy,new in [('host_start','start','c8_engine_start'),('host_token','token','c8_engine_token'),('host_pos','pos','c8_engine_pos'),('host_user','user','c8_engine_user')]:
  old=f'.{port}({legacy})';assert s.count(old)==1
  s=s.replace(old,f'.{port}(C8_CONTEXT ? {new} : {legacy})')
 assert s.count(".host_entry(14'd0)")==1
 s=s.replace(".host_entry(14'd0)",".host_entry(C8_PUBLICATION ? (C8_CONTEXT ? c8_engine_entry : c8_entry) : 14'd0)")
 context="""
    wire c8_engine_start;
    wire [20:0] c8_engine_token,c8_engine_pos;
    wire [9:0] c8_engine_user;
    wire [13:0] c8_engine_entry;
    wire [46:0] c8_engine_identity;
    generate if(C8_CONTEXT) begin:g_c8_context
        initial if(!C8_PUBLICATION) $fatal(1,"C8 context requires actual native publication callbacks");
        ot_dsrom_c8_stage_context u_context(
            .clk(clk),.rst_n(rst_n),.offer_v(start),.offer_ready(c8_offer_ready),
            .offer_token(token),.offer_pos(pos),.offer_user(user),
            .offer_epoch(c8_position_identity[46:31]),.offer_entry(c8_entry),
            .context_v(c8_context_v),.context_restored(c8_context_restored),
            .context_identity(c8_context_identity),.context_token(c8_context_token),.context_entry(c8_context_entry),
            .engine_start(c8_engine_start),.engine_token(c8_engine_token),.engine_pos(c8_engine_pos),
            .engine_user(c8_engine_user),.engine_entry(c8_engine_entry),.engine_identity(c8_engine_identity),
            .engine_done(done),.write_journal_quiet(c8_write_quiet),
            .write_quarantine(c8_write_quarantine),.write_fault(c8_write_fault),
            .retire_v(c8_retire_v),.retire_identity(c8_retire_identity),
            .active(c8_stage_active),.quarantine(c8_stage_quarantine));
    end else begin:g_no_c8_context
        assign c8_offer_ready=rst_n;assign c8_context_v=0;assign c8_retire_v=0;
        assign c8_stage_active=0;assign c8_stage_quarantine=0;
        assign c8_context_identity=0;assign c8_retire_identity=0;
        assign c8_context_token=0;assign c8_context_entry=0;
        assign c8_engine_start=0;assign c8_engine_token=0;assign c8_engine_pos=0;
        assign c8_engine_user=0;assign c8_engine_entry=0;assign c8_engine_identity=0;
    end endgenerate
"""
 assert s.count('endmodule')==1
 s=s.replace('endmodule',context+'\nendmodule')
 emit('ot_v41_rt_die_l20_c8.sv',s)
 return receipts
if __name__=='__main__':
 print(json.dumps(generate(),indent=2))
