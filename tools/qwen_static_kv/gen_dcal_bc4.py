#!/usr/bin/env python3
"""KV-DCAL 10-19 (MU release die, coherent codec2 K22 image): bc4 = the bc3safe structure (Codex 190b12e9f) on the
codec2 K22 image (5ae543bfa, d2d_cal_image_mu.svh SHA e7d4d2d0, D2D_TXDP_K 0x03030416).  The generator refuses any other
image or primitive.  Reset: RTL-owned 2-stage synchronous landing (land0 -> 4 kept land1 copies) then 19 kept release
copies, every reset source <= 23 loads; sticky `fault` (sequencer | COL | RUN | STALE | EARLY) is an output register.
Generate an ordinary-only behavioral reset-bank fork; originals remain immutable.
Each original nonblocking RHS reads old state. Only assignment destinations become
next-state wires. Scalar/sliced flops retain the exact original reset values.
"""
from pathlib import Path
import re, math, hashlib
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'rtl/qwen_sys/d2d_static_20261015'

FROZEN_PRIMITIVES = {'qkd_d2d_cal_seq_bootcfg.sv': '9c43fc17792f780f3b53d635437ed9a6da37737480e480a2ce95b122c4960ae4', 'ot_qwen_d2d_cal_seq.sv': '5edaee7a8c1650c6babfd9fae99b4f83a2cafc3eaed557934721778a5f977688', 'ot_qwen_d2d_cal_seq_dies_mu.sv': '5ed298078d7e2592628e0d70b64129254731664a3601b13efb6a8af2d0bd68a1', 'd2d_cal_image_mu.svh': 'e7d4d2d0f111661d72c5fd96864a18cbba580f5f9b103233f505d7f298dcb3ae'}
for name,expected in FROZEN_PRIMITIVES.items():
    actual=hashlib.sha256((D/name).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f'BC4 unsupported primitive/image {name}: {actual} != {expected}')
if "localparam [31:0] D2D_TXDP_K = 32'h03030416;" not in (D/'d2d_cal_image_mu.svh').read_text():
    raise SystemExit('BC4 image is not the codec2 K22 image (D2D_TXDP_K 0x03030416)')

def split_state(text, marker, widths, reset_expr, aliases=None):
    aliases=aliases or {}
    start=text.index(marker)
    split=text.index('end else begin',start)
    # These frozen blocks end immediately before endmodule.
    end=text.rindex('    end\nendmodule')
    reset=text[start:split]
    body=text[split+len('end else begin'):end]
    assert body.rstrip().endswith('end')
    body=body.rstrip()[:-3] # remove original else end
    vals=dict(re.findall(r'\b(\w+)\s*<=\s*([^;]+);',reset))
    for n,original in aliases.items(): vals[n]=vals[original]
    assert vals and set(vals)==set(widths),(set(vals)-set(widths),set(widths)-set(vals))
    decl=[];defaults=[];flops=[];bit=0
    for name,width in widths.items():
        decl.append(f'    reg [{width-1}:0] {name}_next;')
        defaults.append(f'        {name}_next = {name};')
        body=re.sub(r'\b'+name+r'(\[[^]]+\])?\s*<=',lambda m:name+'_next'+(m.group(1) or '')+' =',body)
        left=0
        while left<width:
            bank=bit//16; n=min(width-left,16-bit%16)
            sl='' if width==1 else f'[{left+n-1}:{left}]'
            resetval=f"{width}'({vals[name]})" if width>1 else vals[name]
            if width>1: resetval=f"(({resetval}) >> {left})"
            flops.append(f'    always @(posedge ck or negedge {reset_expr(bank)})\n        if (!{reset_expr(bank)}) {name}{sl} <= {resetval};\n        else {name}{sl} <= {name}_next{sl};')
            bit+=n;left+=n
    comb=[]
    for index,name in enumerate(widths):
        if name in aliases:
            comb.append(f'    always @* {name}_next = {aliases[name]}_next;')
            continue
        for part,lo in enumerate(range(0,widths[name],8 if 'rdy_copy0' in aliases else 16)):
            hi=min(widths[name],lo+(8 if 'rdy_copy0' in aliases else 16))-1
            temp=f'{name}_part{part}'
            decl.append(f'    reg [{widths[name]-1}:0] {temp};')
            single=body
            for other in widths:
                if other != name: single=re.sub(r'\b'+other+r'_next(?:\[[^]]+\])?\s*=\s*[^;]+;', ';',single)
            single=re.sub(r'\bx\s*=\s*ip >> 1;', ';',single)
            single=re.sub(r'\bx\b', '(ip >> 1)',single)
            for control in (['running','init'] if 'running_copy0' in aliases else []):
                single=re.sub(r'\b'+control+r'\b',f'{control}_copy{(index+part)%3}',single)
            if name=='e' and 'ep_q_copy0' in aliases:
                single=re.sub(r'\bep_rise\b',f'(epoch_go && !ep_q_copy{part})',single)
            if 'rdy_copy0' in aliases:
                single=re.sub(r'\bb_we\b',f'b_we_part{(index+part)%4}',single)
                single=re.sub(r'\bs_we\b',f's_we_part{(index+part)%3}',single)
            single=re.sub(r'\b'+name+r'_next\b',temp,single)
            sl=f'[{hi}:{lo}]'
            comb.append(f'    always @* begin\n        {temp} = {name};'+single+f'\n        {name}_next{sl} = {temp}{sl};\n    end')
    replacement='\n'.join(decl)+'\n'+'\n'.join(comb)+'\n'+'\n'.join(flops)+'\n' 
    return text[:start]+replacement+text[end+len('    end\n'):],math.ceil(bit/16),bit

core=(D/'ot_qwen_d2d_cal_seq.sv').read_text()
core=core.replace('module ot_qwen_d2d_cal_seq #(','module ot_qwen_d2d_cal_seq_bc4 #(').replace('input  wire        rst_n,','input  wire [15:0] rst_bank_n,')
widths=dict(init=1,ip=7,cal_ready=1,running=1,fault=1,cfg_tx_we=1,cfg_rx_we=1,cfg_addr=6,cfg_data=32,cal_start=1,cal_seg=1,t=20,li=6,layer=6,go_d=2,ep_q=1,eact=1,e=32,tokbase=1,adm_pend=1,adm_run=1,adm_done=1,auto_go=1,pcnt=32,prun=1,tok_start=1)
aliases={**{f'ep_q_copy{i}':'ep_q' for i in range(2)},**{f'li_mux{i}':'li' for i in range(5)},**{f'ip_img{i}':'ip' for i in range(4)},**{f'{c}_copy{i}':c for c in ['running','init'] for i in range(3)}}
for n,o in aliases.items(): widths[n]=widths[o]
extra='\n'.join(f'    (* keep = 1, dont_touch = 1 *) reg [{widths[n]-1}:0] {n};' for n in aliases)+'\n'
core=core.replace('    integer x;',extra+'    integer x;')
# Constant-byte slices use separately kept, cycle-identical selector state.
core=core.replace('wire [TW-1:0] nxt = START[TW*li +: TW];', "wire [19:0] nxt = {"+", ".join(f"START[20*li_mux{i}+{4*i} +: 4]" for i in reversed(range(5)))+"};")
core=core.replace("cfg_data <= ip[0] ? RX_IMG[32*x +: 32] : TX_IMG[32*x +: 32];",'\n'.join(f'cfg_data[{8*i} +: 8] <= ip_img{i}[0] ? RX_IMG[32*(ip_img{i} >> 1)+{8*i} +: 8] : TX_IMG[32*(ip_img{i} >> 1)+{8*i} +: 8];' for i in range(4)))
core,nb,cbits=split_state(core,'    always @(posedge ck or negedge rst_n)',widths,lambda b:f'rst_bank_n[{b}]',aliases)
core=core.replace('    integer x;', '''    initial if (NE != 32 || NL != 36 || TW != 20 || GO_OFS != 0 || ADM != 1 || AUTO != 1)
        $fatal(1, "BC4 unsupported ordinary core profile");
    integer x;''')
assert nb<=16
bc=(D/'qkd_d2d_cal_seq_bootcfg.sv').read_text().replace('module qkd_d2d_cal_seq_pin_bc #(','module qkd_d2d_cal_seq_pin_bc4 #(')
bc=bc.replace('    reg [1:0] release_q;','')
a=bc.index('    always @(posedge ck or negedge rst_n)');z=bc.index('    wire s_tx',a)
# Four outer copies distribute input capture (43 bits), internal reset FFs,
# and first-stage async reset. Outer assertion is synchronous, exactly as frozen wrapper.
landing='''    // Own the exact frozen generated landing: SYNCHRONOUS assertion and release.
    (* keep = 1, dont_touch = 1 *) reg land0;
    (* keep = 1, dont_touch = 1 *) reg [3:0] land1;
    always @(posedge ck) begin land0 <= rst_n; land1 <= {4{land0}}; end
    (* keep = 1, dont_touch = 1 *) reg rel0;
    (* keep = 1, dont_touch = 1 *) reg [18:0] rel1;
    always @(posedge ck or negedge land1[3])
        if (!land1[3]) rel0 <= 0; else rel0 <= 1;
    genvar r;
    generate for (r=0;r<19;r=r+1) begin: release_copies
        always @(posedge ck or negedge land1[3])
            if (!land1[3]) rel1[r] <= 0; else rel1[r] <= rel0;
    end endgenerate
'''
capture=[('reload_q',1,'reload','0'),('epoch_go_q',1,'epoch_go','0'),('halt_q',1,'halt','1'),('b_tx_q',1,'bcfg_tx_we','0'),('b_rx_q',1,'bcfg_rx_we','0'),('b_addr_q',6,'bcfg_addr','0'),('b_data_q',32,'bcfg_data','0')]
for i in range(4):
    for name,signal in [('tx','bcfg_tx_we'),('rx','bcfg_rx_we')]:
        n=f'b_{name}_copy{i}'
        landing+=f'    (* keep = 1, dont_touch = 1 *) reg {n};\n'
        capture.append((n,1,signal,'0'))
bit=0
for n,w,d,v in capture:
    for lo in range(0,w):
        bank=bit//16; sl='' if w==1 else f'[{lo}]';ds='' if w==1 else f'[{lo}]'
        landing+=f'    always @(posedge ck or negedge land1[{bank}])\n        if (!land1[{bank}]) {n}{sl} <= {v}; else {n}{sl} <= {d}{ds};\n'
        bit+=1
bc=bc[:a]+landing+bc[z:]
# Replace die-name wrapper with equivalent exact ordinary parameter constants.
a=bc.index('    qkd_d2d_cal_seq #(');z=bc.index('    // ---- merge',a)
seq=(D/'ot_qwen_d2d_cal_seq_dies_mu.sv').read_text();seq=seq[seq.index('module qkd_d2d_cal_seq '):]
inst=seq[seq.index('    ot_qwen_d2d_cal_seq #('):seq.rindex('endmodule')]
inst=inst.replace('ot_qwen_d2d_cal_seq #(','ot_qwen_d2d_cal_seq_bc4 #(').replace('.EP_SKEW(EP_SKEW)', '.EP_SKEW(EP_SKEW - 2)').replace('.rst_n(rst_n)', ".rst_bank_n({1'b0,rel1[14:0]})").replace('.tok_go(tok_go)', ".tok_go(1'b0)")
for old,new in [('reload','reload_q'),('epoch_go','epoch_go_q'),('halt','halt_q'),('cfg_tx_we','s_tx'),('cfg_rx_we','s_rx'),('cfg_addr','s_addr'),('cfg_data','s_data'),('cal_start','s_cs'),('cal_seg','s_seg'),('cal_ready','s_rdy'),('running','s_run'),('layer','s_layer'),('adm_done','s_adm'),('tok_start','s_tok'),('fault','s_fault')]:
    inst=inst.replace(f'.{old}({old})',f'.{old}({new})')
bc=bc[:a]+inst+bc[z:]
bc+= ''
extra=''
for i in range(3):
    extra+=f'    (* keep = 1, dont_touch = 1 *) reg rdy_copy{i};\n'

    extra+=f'    wire s_we_part{i} = (MUT == 1) ? 1\'b0 : ((s_tx || s_rx) && s_rdy && rdy_copy{i});\n'
extra+='    wire b_we_part3 = b_tx_copy3 || b_rx_copy3;\n'
for i in range(3): extra+=f'    wire b_we_part{i} = b_tx_copy{i} || b_rx_copy{i};\n'
bc=bc.replace('    reg rdy_q,',extra+'    reg rdy_q,')
outs=dict(cfg_tx_we=1,cfg_rx_we=1,cfg_addr=6,cfg_data=32,cal_start=1,cal_seg=1,cal_ready=1,running=1,layer=6,adm_done=1,tok_start=1,rdy_q=1,adm_act=1,btx_seen=1,brx_seen=1,f_col=1,f_run=1,f_stale=1,f_early=1,fault=1)
outaliases={f'rdy_copy{i}':'rdy_q' for i in range(3)}
for n,o in outaliases.items(): outs[n]=outs[o]
bc,on,obits=split_state(bc,'    always @(posedge ck or negedge rl)',outs,lambda b:f'rel1[{15+b}]',outaliases)
assert on<=4
bc=bc.replace('    initial if (EP_SKEW < 2)', '''    initial if (EP_SKEW != 3 || GO_OFS != 0 || START_ADJ != '0 || MUT < 0 || MUT > 1)
        $fatal(1, "BC4 unsupported ordinary top profile");
    initial if (EP_SKEW < 2)''')
for name,text in [('ot_qwen_d2d_cal_seq_bc4.sv',core),('qkd_d2d_cal_seq_bc4.sv',bc)]:
    (D/name).write_text('// Generated behavioral source by tools/qwen_static_kv/gen_dcal_bc4.py; originals untouched.\n'+text)
print(dict(core_bits=cbits,core_banks=nb,output_bits=obits,output_banks=on,input_bits=bit,outer_reset_loads=[16,16,16,bit-48+20],shared_rel0_D_loads=19,raw_external_reset_D_loads=1))
