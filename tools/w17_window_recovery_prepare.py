"""Prepare added simulation copies and exact diffs. Never compile or edit RTL originals."""
import argparse
import difflib
import hashlib
import json
import re
import subprocess
from pathlib import Path

SOURCE = '4e38326d6f361bc85e660f48c59c355e2bb95274'
EPOCH9 = 'c09f3fe1500e17f14f2f75e88c03e49bb82995e4'
ORIGINS = {
 'window_prefetch_recovery.sv':(EPOCH9,'rtl/test/w17_window_epoch9_candidate/ot_chip_v41x_window_kv_prefetch.sv'),
 'kv_reqmux_recovery.sv':(SOURCE,'rtl/chip/ot_chip_v41x_kv_reqmux.sv'),
 'kv_rope_reqmux_recovery.sv':(SOURCE,'rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv'),
 'hbm_karb_recovery.sv':(SOURCE,'rtl/chip/ot_chip_v41x_hbm_karb.sv'),
 'idx_hbm_recovery.sv':(SOURCE,'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv'),
}


def read_origin(commit,path):
    return subprocess.check_output(['git','show',f'{commit}:{path}']).decode()


def edit(text,old,new):
    if text.count(old)!=1:
        raise ValueError('nonunique/missing source anchor: '+old[:90])
    return text.replace(old,new)


def split_module(text):
    a=text.index('module ');b=text.index(');',a)+2
    header=text[a:b]
    name=re.search(r'module\s+(\w+)',header).group(1)
    parameters=re.findall(r'parameter\s+(?:(?:integer|longint|bit|signed|wire|reg)\s+)*(\w+)\s*=',header)
    ports=re.findall(r'^\s*(?:input|output)\s+(?:wire|reg)\s*(?:\[[^\]]+\]\s*)?(\w+)\s*[,\n]',header,re.M)
    if not ports or len(ports)!=len(set(ports)):
        raise ValueError('unsupported port schema')
    return a,b,name,header,parameters,ports


def extended(text,controls):
    a,b,name,h,params,ports=split_module(text)
    h=edit(h,'\n) (',',\n    parameter bit OPT_RECOVERY = 0,\n    parameter integer SELECT_STACK = 2\n) (')
    h=h[:-2]+',\n'+controls+'\n);'
    return text[:a]+h+text[b:]

def controls(inputs,outputs):
    return ',\n'.join('    '+direction+' wire '+name
                       for direction,names in [('input',inputs),('output',outputs)]
                       for name in names.split())

SOURCE_PORTS=controls('rec_request rec_token rec_commit rec_down_empty rec_down_visible rec_down_token_ack',
                     'rec_freeze rec_owner_empty rec_restart_ready')
HOP_PORTS=controls('rec_freeze rec_token rec_commit rec_down_empty rec_down_visible rec_down_token_ack',
                  'rec_owner_empty rec_visible_empty rec_token_ack')
BACKEND_PORTS=controls('rec_freeze rec_token rec_commit',
                      'rec_owner_empty rec_visible_empty rec_token_ack')



def source_body(text):
    text=extended(text,SOURCE_PORTS)
    a=text.index('    localparam integer PITCH')
    text=text[:a]+'''    // PREPARED ONLY: no wire identity extension, physical PHY provider or build.
    reg rec_violation;
    assign rec_freeze = OPT_RECOVERY && (fault || rec_request);
    wire rec_reply_owned = state == FR_PIPE && reply_sector <= 16 &&
        reply_epoch_ok && refill_issued[reply_sector] &&
        !refill_received[reply_sector] && s_beat[WIN_STACK*4 +: 4] == 0;
    assign rec_owner_empty = OPT_RECOVERY && rec_freeze &&
        (state == IDLE || (state == FR_PIPE && refill_pending == 0)) &&
        !m_v[WIN_STACK] && !response && !done_write;
    assign rec_restart_ready = rec_owner_empty && rec_down_empty &&
        rec_down_visible && rec_down_token_ack == rec_token &&
        !rec_violation && !fault_code[2] && !blk_v && !prime_v &&
        !prefetch_v && !re && !packed_re;
    initial if (OPT_RECOVERY && (WIN_STACK != SELECT_STACK || SELECT_STACK != 2 ||
        REFILL_CREDITS != 8 || TAGW != 16 || BANKED_STAGE))
        $fatal(1,"recovery selected-aperture contract");
''' +text[a:]
    text=edit(text,'wire pipe_reply_ok = state == FR_PIPE && !fault && response &&\n        reply_sector <= 16 && reply_epoch_ok &&\n        refill_issued[reply_sector] && !refill_received[reply_sector] &&\n        s_beat[WIN_STACK*4 +: 4] == 0 && !response_poison;',
              'wire pipe_reply_ok = rec_reply_owned && response;')
    text=edit(text,'wire pipe_issue = state == FR_PIPE && !fault && refill_pending',
              'wire pipe_issue = state == FR_PIPE && !fault && !rec_freeze && refill_pending')
    for lhs in ['assign blk_ready =','assign prime_ready =','assign prefetch_ready =','assign kv_ok =','assign packed_valid =']:
        text=edit(text,lhs,lhs+' !rec_freeze &&')
    text=edit(text,'if ((state == WC || state == WS || state == FR) && !addr_bad)',
                   'if ((state == WC || state == WS || (state == FR && !rec_freeze)) && !addr_bad)')
    text=edit(text,'refill_epoch <= 0; refill_issued <= 0;',
                   'rec_violation <= 0;\n            refill_epoch <= 0; refill_issued <= 0;')
    for old,new in [('if (blk_v) begin','if (blk_v && blk_ready) begin'),
                    ('end else if (prime_v) begin','end else if (prime_v && prime_ready) begin'),
                    ('end else if (prefetch_v) begin','end else if (prefetch_v && prefetch_ready) begin')]:
        text=edit(text,old,new)
    text=edit(text,'WS_DONE: if (done_write) begin\n                    block_valid',
                   'WS_DONE: if (done_write && !rec_freeze) begin\n                    block_valid')
    # Faulted accepted WS must still finish, but never publish its row.
    text=edit(text,'FR_PIPE: if (!fault) begin', '''FR_PIPE: if (rec_freeze) begin
                    if (response) begin
                        if (!rec_reply_owned || refill_pending == 0) begin
                            rec_violation <= 1; fault <= 1; fault_code[2] <= 1;
                        end else begin
                            refill_received[reply_sector] <= 1;
                            refill_pending <= refill_pending - 1'b1;
                        end
                    end
                end else if (!fault) begin''')
    text=edit(text,'if (!BANKED_STAGE) begin\n                                    if (reply_sector < 16)',
        '''if (response_poison) begin fault <= 1; fault_code[4] <= 1; end
                                if (!response_poison && !BANKED_STAGE) begin
                                    if (reply_sector < 16)''')
    text=edit(text,'if (reply_sector == 16) begin','if (reply_sector == 16 && !response_poison) begin')
    text=edit(text,'            endcase\n        end\n    end\nendmodule', '''            endcase
            if (rec_freeze) begin
                // Clear publication after all legacy NBA assignments. Accepted
                // WC -> WS continuation still issues and drains without new blk.
                row_valid <= 0; stage_valid <= 0;
                if (state == WS_DONE && done_write) state <= IDLE;
                if (response && state != FR_PIPE) begin
                    rec_violation <= 1; fault <= 1; fault_code[2] <= 1;
                end
            end
            if (rec_commit) begin
                if (rec_restart_ready) begin
                    state <= IDLE; refill_epoch <= refill_epoch + 1'b1;
                    refill_issued <= 0; refill_received <= 0;
                    refill_next <= 0; refill_pending <= 0;
                    fault <= 0; fault_code <= 0;
                    row_active <= 0; row_valid <= 0; stage_valid <= 0;
                    rec_violation <= 0;
                end else $fatal(1,"uncertified recovery commit");
            end
        end
    end
endmodule''')
    return text


def hop_body(text,kind):
    text=extended(text,HOP_PORTS)
    if kind=='karb':
        condition="!(k_v && k_tag[TAGW-1 -: 2] == 0) && !k_wr_done && !(k_rsp_v && k_rsp_tag[TAGW-1 -: 2] == 0)"
        constraints='NPC != 32 || TAGW != 16 || AW != 30 || LENW != 4 || BEATW != 4 || DW != 256 || PIPE_OUT || PIPE_RSP'
    elif kind=='outer':
        condition='!w_v[SELECT_STACK] && !w_sv[SELECT_STACK] && !w_wr_done[SELECT_STACK]'
        constraints='TAGW != 16 || HAW != 30'
    else:
        condition='!w_v[SELECT_STACK] && !w_sv[SELECT_STACK] && !w_wr_done[SELECT_STACK]'
        # Inner mux in actual nested path uses TAGW15.
        constraints='TAGW != 15 || HAW != 30'
    idx=text.index(');',text.index('module '))+2
    text=text[:idx]+f'''
    // Direct mux/arbiter: control only, no new request/response holding state.
    assign rec_owner_empty = rec_freeze && rec_down_empty && {condition};
    assign rec_visible_empty = rec_down_visible;
    assign rec_token_ack = (rec_owner_empty && rec_visible_empty &&
        rec_down_token_ack == rec_token) ? rec_token : !rec_token;
    initial if (SELECT_STACK != 2 || {constraints})
        $fatal(1,"recovery direct-path aperture");
''' +text[idx:]
    return text


def backend_body(text):
    text=extended(text,BACKEND_PORTS)
    idx=text.index('    // backing store')
    text=text[:idx]+'''    // Simulation-provider watermark only: no healthy publication timer.
    reg [3:0] rec_reads [0:NPC-1];
    reg [1:0] rec_writes [0:NPC-1];
    longint rec_visible_at;
    reg rec_visible_valid, rec_ack_pending;
    function automatic rec_mine(input [TAGW-1:0] t);
        rec_mine = t[TAGW-1 -: 3] == 3'b100;
    endfunction
    function automatic rec_zero();
        integer z;
        begin
            rec_zero = 1;
            for (z=0; z<NPC; z=z+1)
                if (rec_reads[z] != 0 || rec_writes[z] != 0 ||
                    (rsp_v[z] && rec_mine(rsp_tag[z*TAGW +: TAGW])) ||
                    (req_v[z] && rec_mine(req_tag[z*TAGW +: TAGW])))
                    rec_zero = 0;
        end
    endfunction
    assign rec_owner_empty = rec_freeze && !rec_ack_pending && rec_zero();
    assign rec_visible_empty = !rec_visible_valid;
    assign rec_token_ack = (rec_owner_empty && rec_visible_empty) ? rec_token : !rec_token;
    initial if (SELECT_STACK != 2 || NPC != 32 || TAGW != 17 || LENW != 4 ||
        BEATW != 4 || AW != 30 || DW != 256 || QD != 64 || RQD != 32 ||
        RW != 16 || MAXSKIP != 16 || REFPB != 3 || MEM_WORDS != 264320 ||
        CWL_PS != 6250 || BURST_PS != 1024 || MEM_MODE != 0 || CLK_PS != 1000)
        $fatal(1,"recovery finite simulation provider geometry");
''' +text[idx:]
    text=edit(text,'cyc <= 0; rsp_v <= 0; wr_done <= 0;',
        'rec_visible_at = 0; rec_visible_valid = 0; rec_ack_pending = 0;\n            cyc <= 0; rsp_v <= 0; wr_done <= 0;')
    text=edit(text,'q_rp[p] = 0; q_n[p] = 0;',
        'rec_reads[p]=0; rec_writes[p]=0;\n                q_rp[p] = 0; q_n[p] = 0;')
    text=edit(text,'now = cyc * CLK_PS;', 'now = cyc * CLK_PS;\n            rec_ack_pending = 0;')
    text=edit(text,'if (rsp_v[p] && rsp_rdy[p]) begin', '''if (rsp_v[p] && rsp_rdy[p]) begin
                    if (rec_mine(rsp_tag[p*TAGW +: TAGW])) begin
                        if (rec_reads[p] == 0) $fatal(1,"owner return underflow");
                        rec_reads[p] = rec_reads[p] - 1'b1;
                    end''')
    text=edit(text,'if (req_v[j] && req_rdy[j]) begin', '''if (req_v[j] && req_rdy[j]) begin
                    if (rec_mine(req_tag[j*TAGW +: TAGW])) begin
                        if (req_addr[j*AW +: AW] >= MEM_WORDS)
                            $fatal(1,"owner address allocation alias");
                        if (req_len[j*LENW +: LENW] != 1)
                            $fatal(1,"owner request must be one sector");
                        if (req_we[j]) begin
                            if (rec_writes[j] != 0) $fatal(1,"owner write overflow");
                            rec_writes[j] = rec_writes[j] + 1'b1;
                        end else begin
                            if (rec_reads[j] == 8) $fatal(1,"owner read overflow");
                            rec_reads[j] = rec_reads[j] + 1'b1;
                        end
                    end''')
    text=edit(text,'if (q_we[p][slot]) begin', '''if (q_we[p][slot]) begin
                                if (rec_mine(q_tag[p][slot])) begin
                                    if (rec_writes[p] == 0) $fatal(1,"owner issue underflow");
                                    rec_writes[p] = rec_writes[p] - 1'b1;
                                    rec_ack_pending = 1;
                                    if (h_tcol[p] + CWL_PS + BURST_PS > rec_visible_at)
                                        rec_visible_at = h_tcol[p] + CWL_PS + BURST_PS;
                                    rec_visible_valid = 1;
                                end''')
    text=edit(text,'// registered outputs for the next cycle', '''// Owner-only invariant: registers remain finite; q/r aliases
            // are checked by the independent bench oracle, not extra ledgers.
            begin : rec_population
                integer z, x, qr, qw, rr, nr, nw;
                nr=0; nw=0;
                for(z=0;z<NPC;z=z+1) begin
                    qr=0; qw=0; rr=0;
                    for(x=0;x<q_n[z];x=x+1)
                        if(rec_mine(q_tag[z][(q_rp[z]+x)%QD])) begin
                            if(q_we[z][(q_rp[z]+x)%QD]) qw=qw+1; else qr=qr+1;
                        end
                    for(x=0;x<r_n[z];x=x+1)
                        if(rec_mine(r_tag[z][(r_rp[z]+x)%RQD])) rr=rr+1;
                    if(rec_reads[z] != qr+rr || rec_writes[z] != qw)
                        $fatal(1,"owner ledger versus ring provenance");
                    nr=nr+rec_reads[z]; nw=nw+rec_writes[z];
                end
                if(nr>8 || nw>1 || now<0) $fatal(1,"owner population/time bound");
            end
            if (rec_visible_valid && now >= rec_visible_at) rec_visible_valid = 0;
            if (rec_commit && !(rec_owner_empty && rec_visible_empty))
                $fatal(1,"backend commit before visibility/owner drain");
            // registered outputs for the next cycle''')
    return text


def prepare(out):
    if out.exists():
        raise ValueError('refuse existing preparation directory')
    bases={f:read_origin(*origin) for f,origin in ORIGINS.items()}
    names={f:split_module(t)[2] for f,t in bases.items()}
    rename={name:name+'_recovery_legacy' for name in names.values()}
    records={};out.mkdir(parents=True)
    for f,base in bases.items():
        name=names[f]
        enabled=(source_body(base) if f.startswith('window') else
                 backend_body(base) if f.startswith('idx') else
                 hop_body(base,'karb' if f.startswith('hbm') else 'outer' if 'rope' in f else 'inner'))
        # Rename all copied dependencies; direct nested mux remains the exact
        # legacy inner mux. Its emptiness has no distinct storage. Control
        # observability is at outer WINDOW boundary (same combinational path).
        legacy=base;active=enabled
        for old,new in rename.items():
            legacy=re.sub(r'\b'+old+r'\b',new,legacy)
            active=re.sub(r'\b'+old+r'\b',new,active)
        active=edit(active,'module '+rename[name], 'module '+name+'_recovery_enabled')
        # Wrapper selection provides literal original implementation at default.
        a,b,_,h,params,ports=split_module(enabled)
        wrapper=enabled[:a]+h.replace('module '+name,'module '+name+'_recovery',1)
        extra_ports=([('rec_freeze',0),('rec_owner_empty',0),('rec_restart_ready',0)] if f.startswith('window') else
                     [('rec_owner_empty',0),('rec_visible_empty',0),('rec_token_ack',0)])
        baseline_params=[p for p in params if p not in ('OPT_RECOVERY','SELECT_STACK')]
        baseline_ports=split_module(base)[5]
        def instance(mod,ps,vs):
            return mod+' #(\n'+',\n'.join('    .'+p+'('+p+')' for p in ps)+'\n) u_impl (\n'+',\n'.join('    .'+p+'('+p+')' for p in vs)+'\n);\n'
        wrapper+='\ngenerate if (!OPT_RECOVERY) begin : g_legacy\n'+instance(rename[name],baseline_params,baseline_ports)
        wrapper+=''.join('assign '+p+" = 1'b0;\n" for p,_ in extra_ports)
        wrapper+='end else begin : g_recovery\n'+instance(name+'_recovery_enabled',params,ports)+'end endgenerate\nendmodule\n'
        generated=wrapper+'\n'+legacy+'\n'+active
        (out/f).write_text(generated)
        diff=''.join(difflib.unified_diff(base.splitlines(True),enabled.splitlines(True),fromfile=ORIGINS[f][1],tofile=f+'_enabled'))
        (out/(f+'.diff')).write_text(diff)
        restored=legacy
        for old,new in rename.items():restored=re.sub(r'\b'+new+r'\b',old,restored)
        assert restored==base
        records[f]={'origin_commit':ORIGINS[f][0],'origin_path':ORIGINS[f][1],
                    'origin_sha256':hashlib.sha256(base.encode()).hexdigest(),
                    'copy_sha256':hashlib.sha256(generated.encode()).hexdigest(),
                    'enabled_diff_sha256':hashlib.sha256(diff.encode()).hexdigest(),
                    'default_branch_inverse_rename_byte_identical':True,
                    'module_names':[name+'_recovery',name+'_recovery_legacy',name+'_recovery_enabled']}
    return records




def prepared_bench(out):
    """Finite bench, uncompiled. Identities/counters here are observer-only."""
    modules={f:split_module(read_origin(*v)) for f,v in ORIGINS.items()}
    declarations=[];instances=[];assignments=[]
    aliases={'window_prefetch_recovery.sv':'src','kv_rope_reqmux_recovery.sv':'mux',
             'hbm_karb_recovery.sv':'arb','idx_hbm_recovery.sv':'back'}
    settings={
      'src':{'POS_W':21,'SEC_W':30,'HAW':30,'TAGW':16,'USER_W':10,'BANKED_STAGE':0,'WIN_STACK':2,'REFILL_CREDITS':8,'WINDOW_SLOTS':128,'MAX_CONTEXT':1048576},
      'mux':{'HAW':30,'TAGW':16},
      'arb':{'NPC':32,'AW':30,'TAGW':16,'LENW':4,'BEATW':4,'DW':256,'PIPE_OUT':0,'PIPE_RSP':0},
      'back':{'NPC':32,'AW':30,'TAGW':17,'LENW':4,'BEATW':4,'DW':256,'QD':64,'RQD':32,'RW':16,'MAXSKIP':16,'REFPB':3,'CLK_PS':1000,'MEM_MODE':0,'MEM_WORDS':264320},
    }
    controls={
      'src':{'rec_request':'recover','rec_token':'token','rec_commit':'commit','rec_down_empty':'mux_empty','rec_down_visible':'mux_visible','rec_down_token_ack':'mux_ack','rec_freeze':'freeze','rec_owner_empty':'source_empty','rec_restart_ready':'restart_ready'},
      'mux':{'rec_freeze':'freeze','rec_token':'token','rec_commit':'commit','rec_down_empty':'arb_empty','rec_down_visible':'arb_visible','rec_down_token_ack':'arb_ack','rec_owner_empty':'mux_empty','rec_visible_empty':'mux_visible','rec_token_ack':'mux_ack'},
      'arb':{'rec_freeze':'freeze','rec_token':'token','rec_commit':'commit','rec_down_empty':'back_empty','rec_down_visible':'back_visible','rec_down_token_ack':'back_ack','rec_owner_empty':'arb_empty','rec_visible_empty':'arb_visible','rec_token_ack':'arb_ack'},
      'back':{'rec_freeze':'freeze','rec_token':'token','rec_commit':'commit','rec_owner_empty':'back_empty','rec_visible_empty':'back_visible','rec_token_ack':'back_ack'},
    }
    for f,prefix in aliases.items():
        _,_,name,header,_,ports=modules[f];params=settings[prefix]
        directions={}
        for match in re.finditer(r'^\s*(input|output)\s+(?:wire|reg)\s*(\[[^\]]+\])?\s*(\w+)',header,re.M):
            direction,width,port=match.groups();directions[port]=direction
            width=width or ''
            for key,value in params.items():width=re.sub(r'\b'+key+r'\b',str(value),width)
            declarations.append(f'wire {width} {prefix}_{port};')
        connections={p:prefix+'_'+p for p in ports};connections.update(controls[prefix])
        for p in ports:
            if directions[p]!='input':continue
            rhs="'0"
            if p=='clk':rhs='clk'
            elif p=='rst_n':rhs='rst_n'
            elif prefix=='src':
                rhs={'prime_v':'prime','prefetch_v':'prefetch','blk_v':'block_offer','packed_re':'fault_pulse','region_base_sector':'30\'d262144','region_sector_count':'30\'d2176','blk_scale':'8\'d127'}.get(p,rhs)
                if p=='s_v':rhs='mux_w_sv'
                elif p=='s_tag':rhs='mux_w_stag'
                elif p=='s_beat':rhs='mux_w_sbeat'
                elif p=='s_data':rhs='mux_w_sdata'
                elif p=='m_rdy':rhs='mux_w_rdy'
                elif p=='m_wr_done':rhs='mux_w_wr_done'
            elif prefix=='mux':
                rhs={'w_v':'src_m_v','w_addr':'src_m_addr','w_len':'src_m_len','w_tag':'src_m_tag','w_we':'src_m_we','w_wdata':'src_m_wdata','w_wstrb':'src_m_wstrb','w_srdy':'src_s_rdy','m_rdy':"(4'(arb_k_rdy) << 2)",'m_wr_done':"(4'(arb_k_wr_done) << 2)",'s_v':"(4'(arb_k_rsp_v) << 2)",'s_tag':"(64'(arb_k_rsp_tag) << 32)",'s_beat':"(16'(arb_k_rsp_beat) << 8)",'s_data':"(1024'(arb_k_rsp_data) << 512)", 'c_v':"(4'(ckv_offer) << 2)",'c_addr':"(120'(30'd20) << 60)",'c_len':"(16'(4'd1) << 8)",'c_srdy':"4'hf",'p_srdy':"4'hf"}.get(p,rhs)
            elif prefix=='arb':
                rhs={'k_v':'mux_m_v[2]','k_addr':'mux_m_addr[60 +: 30]','k_len':'mux_m_len[8 +: 4]','k_tag':'mux_m_tag[32 +: 16]','k_we':'mux_m_we[2]','k_wdata':'mux_m_wdata[512 +: 256]','k_wstrb':'mux_m_wstrb[64 +: 32]','k_rsp_rdy':'mux_s_rdy[2]','h_rdy':'back_req_rdy','h_wr_done':'back_wr_done','r_v':'back_rsp_v & {32{!hold_return}}','r_tag':'back_rsp_tag','r_beat':'back_rsp_beat','r_data':'back_rsp_data','b_v':"(32'(b_offer) << 31)",'b_addr':"(960'(30'd124) << 930)",'b_len':"(128'(4'd1) << 124)",'b_we':"(32'(b_offer && b_is_write) << 31)",'b_wstrb':"(1024'(32'hffffffff) << 992)",'b_rsp_rdy':"32'hffffffff"}.get(p,rhs)
            elif prefix=='back':
                rhs={'req_v':'arb_h_v','req_addr':'arb_h_addr','req_len':'arb_h_len','req_tag':'arb_h_tag','req_we':'arb_h_we','req_wdata':'arb_h_wdata','req_wstrb':'arb_h_wstrb','rsp_rdy':'arb_r_rdy & {32{!hold_return}}'}.get(p,rhs)
            assignments.append(f'assign {prefix}_{p} = {rhs};')
        extra={'OPT_RECOVERY':1,'SELECT_STACK':2}
        instances.append(name+'_recovery #(\n'+',\n'.join(f' .{k}({v})' for k,v in (params|extra).items())+'\n) '+prefix+' (\n'+',\n'.join(' .'+k+'('+v+')' for k,v in connections.items())+'\n);')
    bench='''`timescale 1ns/1ps
// PREPARED NOT COMPILED: selected-stack2 minimum fixture, observer IDs only.
module tb;
logic clk=0, rst_n=0;
always #0.5 clk=~clk;
logic prime=0, prefetch=0, block_offer=0, fault_pulse=0;
logic recover=0, token=0, commit=0, hold_return=0;
logic b_offer=0, ckv_offer=0, b_is_write=0;
integer other_grants=0, other_reads=0, other_returns=0, other_writes=0;
integer other_qr_total=0, other_qw_total=0;
wire freeze, source_empty, restart_ready;
wire mux_empty,mux_visible,mux_ack,arb_empty,arb_visible,arb_ack;
wire back_empty,back_visible,back_ack;
integer cycles=0, accepted_reads=0, returned_reads=0, accepted_writes=0;
integer expected_writes=0, pc, qi, ri, oq, orq, ow;
longint observer_operation=0, oracle_visible_at=0;
string scenario;
'''+ '\n'.join(declarations+assignments+instances)+'''
// Independent quiescence oracle: no identities travel on candidate wires.
always @(posedge clk) begin
 if(rst_n) begin
  cycles=cycles+1;
  if(cycles>250000) $fatal(1,"bounded recovery case timeout; ownership retained");
  if(src_blk_v && src_blk_ready) expected_writes=expected_writes+2;
  for(pc=0;pc<32;pc=pc+1) begin
   if(back_req_v[pc] && back_req_rdy[pc] && back_req_tag[pc*17+14 +: 3]!=3'b100) begin
    other_grants=other_grants+1;
    if(back_req_we[pc]) other_writes=other_writes+1; else other_reads=other_reads+1;
   end
   if(back_rsp_v[pc] && back_rsp_rdy[pc] && back_rsp_tag[pc*17+14 +: 3]!=3'b100)
    other_returns=other_returns+1;
   if(back_req_v[pc] && back_req_rdy[pc] && back_req_tag[pc*17+14 +: 3]==3'b100) begin
    if(back_req_we[pc]) accepted_writes=accepted_writes+1;
    else accepted_reads=accepted_reads+1;
   end
   if(back_rsp_v[pc] && back_rsp_rdy[pc] && back_rsp_tag[pc*17+14 +: 3]==3'b100)
    returned_reads=returned_reads+1;
  end
 end
end
// Finite B/CKV interference, driven away from sampling edge. B onPC31 and
// CKV onPC5 do not alias WINDOW block0 WCpc0 / WSpc4 visibility oracle.
always @(negedge clk) if(rst_n) begin
 b_offer=(cycles%13==0); ckv_offer=(cycles%17==0); b_is_write=(cycles%2==0);
end
// Post-NBA sample prevents mistaking registered offers for absent ownership.
always @(negedge clk) if(rst_n) begin
 other_qr_total=0; other_qw_total=0;
 for(pc=0;pc<32;pc=pc+1) begin
  oq=0; orq=0; ow=0;
  for(qi=0;qi<back.g_recovery.u_impl.q_n[pc];qi=qi+1)
   if(back.g_recovery.u_impl.q_tag[pc][(back.g_recovery.u_impl.q_rp[pc]+qi)%64][16:14]==3'b100) begin
    if(back.g_recovery.u_impl.q_we[pc][(back.g_recovery.u_impl.q_rp[pc]+qi)%64]) ow=ow+1;
    else oq=oq+1;
   end else begin
    if(back.g_recovery.u_impl.q_we[pc][(back.g_recovery.u_impl.q_rp[pc]+qi)%64]) other_qw_total=other_qw_total+1;
    else other_qr_total=other_qr_total+1;
   end
  for(ri=0;ri<back.g_recovery.u_impl.r_n[pc];ri=ri+1)
   if(back.g_recovery.u_impl.r_tag[pc][(back.g_recovery.u_impl.r_rp[pc]+ri)%32][16:14]==3'b100) orq=orq+1; else other_qr_total=other_qr_total+1;
  if(back.g_recovery.u_impl.rec_reads[pc] != oq+orq || back.g_recovery.u_impl.rec_writes[pc] != ow)
   $fatal(1,"observer ring/ledger mismatch");
  // Existing schedule history records column timestamps, independent of new watermark.
  if((pc==0 || pc==4) && back.g_recovery.u_impl.last_wr[pc]>=0 && back.g_recovery.u_impl.last_wr[pc]+7274 > oracle_visible_at)
   oracle_visible_at=back.g_recovery.u_impl.last_wr[pc]+7274;
 end
 if(other_reads-other_returns != other_qr_total ||
    other_writes-back.g_recovery.u_impl.st_wr[31] != other_qw_total)
  $fatal(1,"observer unrelated owner conservation");
 if(restart_ready && (accepted_reads!=returned_reads || expected_writes!=accepted_writes ||
     back.g_recovery.u_impl.now<oracle_visible_at || hold_return))
  $fatal(1,"observer premature closed/visible fence");
 if(freeze && (src_packed_valid || src_kv_ok)) $fatal(1,"fault publication");
end

task automatic tick(); @(posedge clk); #0.001; endtask
task automatic freeze_fault();
 @(negedge clk); recover=1; fault_pulse=1;
 tick(); @(negedge clk); fault_pulse=0;
endtask
task automatic drain_and_restart();
 wait(restart_ready); @(negedge clk); commit=1;
 tick(); @(negedge clk); commit=0; recover=0; token=!token;
 observer_operation=observer_operation+1;
 tick(); if(src_fault) $fatal(1,"fault did not clear after certified fence");
endtask
initial begin
 if(!$value$plusargs("CASE=%s",scenario)) scenario="READ_HELD";
 repeat(3) tick(); @(negedge clk); rst_n=1;
 // Legal synthetic backing; no checkpoint/model payload reads.
 back.g_recovery.u_impl.mem[20]=0; back.g_recovery.u_impl.mem[124]=0;
 for(qi=262144;qi<264320;qi=qi+1) back.g_recovery.u_impl.mem[qi]=0;
 tick(); @(negedge clk); prime=1; tick(); @(negedge clk); prime=0;
 if(scenario=="READ_HELD") begin
  @(negedge clk); prefetch=1; tick(); @(negedge clk); prefetch=0; hold_return=1;
  wait(|back_rsp_v); freeze_fault(); repeat(12) tick();
  if(restart_ready) $fatal(1,"held return admitted restart");
  @(negedge clk); hold_return=0;
 end else if(scenario=="WC_INTENT" || scenario=="WS_VISIBLE") begin
  @(negedge clk); block_offer=1; tick(); @(negedge clk); block_offer=0;
  if(scenario=="WC_INTENT") wait(src.g_recovery.u_impl.state==2);
  else wait(src.g_recovery.u_impl.state==4);
  freeze_fault();
 end else $fatal(1,"unreviewed recovery scenario");
 drain_and_restart();
 if(other_grants==0) $fatal(1,"other clients never exercised");
 if(expected_writes!=accepted_writes || accepted_reads!=returned_reads)
  $fatal(1,"ownership not drained");
 $display("PREPARED_RECOVERY_CASE_PASS case=%s cycles=%0d reads=%0d replies=%0d writes=%0d observerop=%0d",scenario,cycles,accepted_reads,returned_reads,accepted_writes,observer_operation);
 $finish;
end
endmodule
'''
    (out/'tb.sv').write_text(bench)
    return hashlib.sha256(bench.encode()).hexdigest()


def control_mutants():
    return {
      'discard_retirement_omitted':{
        'file':'window_prefetch_recovery.sv',
        'old':"refill_received[reply_sector] <= 1;\n                            refill_pending <= refill_pending - 1'b1;",
        'new':"refill_received[reply_sector] <= 1;\n                            // MUTANT: do not retire owned faulted response.",
        'case':'READ_HELD','expected_failure':'bounded recovery case timeout; ownership retained'},
      'accepted_WS_intent_dropped':{
        'file':'window_prefetch_recovery.sv',
        'old':"WC_DONE: if (done_write) begin sec <= 5'd16; state <= WS; end",
        'new':"WC_DONE: if (done_write) begin state <= IDLE; end // MUTANT drops accepted WS intent",
        'case':'WC_INTENT','expected_failure':'observer premature closed/visible fence'},
      'issue_ACK_as_visibility':{
        'file':'idx_hbm_recovery.sv',
        'old':'assign rec_visible_empty = !rec_visible_valid;',
        'new':"assign rec_visible_empty = 1'b1; // MUTANT treats issue ACK as visible",
        'case':'WS_VISIBLE','expected_failure':'observer premature closed/visible fence'},
    }


def mutant_patches(out):
    # Diff only against added enabled namespaces; literal legacy is untouched.
    metadata={}
    for label,mutation in control_mutants().items():
        path=out/mutation['file'];base=path.read_text()
        i=base.index('module ',base.index('module ',base.index('module ')+1)+1)
        prefix,enabled=base[:i],base[i:]
        changed=prefix+edit(enabled,mutation['old'],mutation['new'])
        diff=''.join(difflib.unified_diff(base.splitlines(True),changed.splitlines(True),
                    fromfile=mutation['file'],tofile=mutation['file']))
        (out/(label+'.patch')).write_text(diff)
        metadata[label]={k:v for k,v in mutation.items() if k not in ('old','new')}
        metadata[label]['patch_sha256']=hashlib.sha256(diff.encode()).hexdigest()
    return metadata


def pinned_dependencies(out):
    records={}
    for filename in ('ot_chip_v41x_window_row_codec.sv',
                     'ot_chip_v41x_window_stage4.sv',
                     'ot_chip_v41x_hbm_rsp_pipe.sv'):
        origin='rtl/chip/'+filename
        data=read_origin(SOURCE,origin)
        target='pinned_'+filename
        (out/target).write_text(data)
        records[target]={'source_commit':SOURCE,'source_path':origin,
                         'sha256':hashlib.sha256(data.encode()).hexdigest(),
                         'byte_identical_unmodified_dependency':True}
    return records


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    copies=prepare(args.output)
    bench=prepared_bench(args.output)
    mutants=mutant_patches(args.output)
    dependencies=pinned_dependencies(args.output)
    print(json.dumps({'copies':copies,'bench_sha256':bench,'control_mutants':mutants,'dependencies':dependencies},indent=2))
