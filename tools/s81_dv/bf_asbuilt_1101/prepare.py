#!/usr/bin/env python3
"""Current as-built frame BF calendar probe, with simulation-only image identities."""
from pathlib import Path
import argparse
import hashlib
import json
import re


def close_paren(text, start):
    level=0
    for i in range(start,len(text)):
        if text[i]=='(':level+=1
        elif text[i]==')':
            level-=1
            if not level:return i+1
    raise ValueError('unclosed module header')


def prepare(source, schedule, out, master='col_h9', variant='asb_x', native_family=False):
    source, schedule, out = Path(source), Path(schedule), Path(out)
    out.mkdir(parents=True, exist_ok=False)
    record = json.loads(schedule.read_text())
    for name, sha in record['source_sha256'].items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest() != sha:
            raise ValueError('selected frame source changed: '+name)
    overlays = {}
    plan = f'rtl/dsrom_sys/s81_dv/frame_lp/plan/{master}_l4_lp_plan_kit.sv'
    text = (source/plan).read_text()
    # These INSTANCE arguments are precisely the missing simulation image rule;
    # they do not alter any port, arithmetic, clock or state transition.
    pattern = r'\b(dsfd_bf_col|dsfd_bf_front_roots)\s+(u_e\d+[we]?)\s*\('
    text, count = re.subn(pattern, lambda m: m[1]+' #(.INSTANCE({INSTANCE, "_'+m[2][2:]+'"})) '+m[2]+' (', text)
    if count != (12 if master=='col_h9' else 15):
        raise ValueError('unexpected actual BF front/column identity count: '+str(count))
    text,cfg_count=re.subn(r'\bot_rom_4096x72_m8\s+(u_c\d+_[0-6])\s*\(',
                          lambda m:'ot_rom_4096x72_m8 #(.INSTANCE({INSTANCE, "_'+m[1][2:]+'"})) '+m[1]+' (',text)
    if cfg_count!=140:raise ValueError('unexpected actual CFG bank identity count: '+str(cfg_count))
    overlay = out/Path(plan).name
    overlay.write_text(text); overlays[plan] = str(overlay)
    core = 'rtl/v41rom/ot_v41_bf_front_core_roots.sv'
    text = (source/core).read_text()
    old = '    wire issue = (STATIC_PROGRAM != 0) ? prog_issue_u : issue_available;'
    if text.count(old) != 1:
        raise ValueError('walker reference patch does not match selected BF core')
    (out/'walker_core.sv').write_text(text.replace(old, '    wire issue = issue_available; // measurement reference only'))
    hard=json.loads((source/f'rtl/dsrom_sys/s81_dv/frame_lp/kit/{master}_l4_lp_kit_vg.hard_params.json').read_text())['masters']
    for module in ('ot_s81_cfg7_seq','ot_s81_cfg7_seq_bfp'):
        name=f'rtl/v41die/{module}.sv'
        text=(source/name).read_text();start=text.index('module '+module)
        left=text.index('(',start);right=close_paren(text,left)
        head=text[start:right]
        for param,value in hard[module].items():
            head,n=re.subn(r'(\bparameter\s+(?:integer\s+)?'+param+r'\s*=\s*)[^,\n)]+',lambda m:m[1]+value,head)
            if n!=1:raise ValueError('exact hard parameter missing: '+module+'.'+param)
        overlay=out/(module+'.sv');overlay.write_text(text[:start]+head+text[right:]);overlays[name]=str(overlay)
    # BF-only active composition. Q results are explicitly quiescent, rather
    # than pretending stripped Q hard parameters are the selected die masters.
    qname='rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv'
    text=(source/qname).read_text();start=text.index('module ot_v41_rom_elem_q_qxpq_w10')
    left=text.index('(',start);right=close_paren(text,left)
    left=text.index('(',right);right=close_paren(text,left)
    header=text[start:right]+';'
    outputs=re.findall(r'\boutput\s+wire\s+(?:\[[^]]+\]\s*)?(\w+)',header)
    if len(outputs)<3:raise ValueError('Q quiescent stub output schema changed')
    overlay=out/'quiescent_q.sv'
    overlay.write_text('`timescale 1ns/1ps\n'+header+'\n'+''.join("assign "+n+" = '0;\n" for n in outputs)+'endmodule\n')
    overlays[qname]=str(overlay)
    tb = 'rtl/dsrom_sys/s81_dv/frame/test/tb_s81dv_frame.sv'
    text = (source/tb).read_text()
    if text.count('always #0.5 clk = ~clk;') != 1:
        raise ValueError('bench clock form changed')
    text = text.replace('always #0.5 clk = ~clk;', 'initial forever begin #0.416 clk = 1; #0.417 clk = 0; end')
    if native_family:
        old='wire [1100:0] xw2 = {xs[1100:565], xw[564:550], xs[549:1], xw[550] | xw[551] | xs[283] | xs[565] | xs[569]};'
        new='''reg native_family_q=0;
    always @(posedge clk) if(!rst_n) native_family_q<=0; else if(xw[550]) native_family_q<=xw[565];
    wire native_family=xw[550] ? xw[565] : native_family_q;
    wire [1100:0] xw2 = {xs[1100:566], native_family, xw[564:550], xs[549:1], xw[550] | xw[551] | xs[283] | native_family | xs[569]};'''
        if text.count(old)!=1:raise ValueError('legacy family-pulse driver changed')
        text=text.replace(old,new)
    (out/'tb.sv').write_text(text)
    (out/'wrapper.sv').write_text(f'''`timescale 1ns/1ps
module bf_asbuilt_frame #(parameter INSTANCE="f")
 (input wire clk, cr, cr_s, rst_n, input wire [1103:0] x,
  input wire [3:0] xk, output wire [1103:0] xo,
  output wire [3:0] xok, output wire [69:0] ret);
 {master}_l4_lp_{variant} #(.INSTANCE(INSTANCE)) u_f
  (.ck_r0(clk),.ck_r1(clk),.ck_r2(clk),.rst_n(rst_n),.x(x),
   {'.xo(xo),.xok(xok),' if variant=='asb_x' else ''}.ret(ret));
 {'assign xo=x; assign xok={4{clk}};' if variant=='asb_nx' else ''}
endmodule
''')
    # The original frame bench's functional source set plus the exact selected
    # frame schedule sources. Unreachable modules are not elaborated.
    files=[]; inc=[]
    for line in (source/'tools/s81_dv/frame_bench.f').read_text().splitlines():
        line=line.strip()
        if not line or line.startswith('#'):continue
        if line.startswith('+incdir+'):
            inc.append('+incdir+'+str(source/line[len('+incdir+'):]))
        else: files.append(line)
    files += [n for n in record['source_sha256'] if n.endswith(('.sv','.v'))]
    files += ['rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv']
    files = list(dict.fromkeys(files))
    selected_defines=json.loads((source/'asbuilt_kva3_g3tag2_sel.json').read_text())['defines']
    if any(not re.fullmatch(r'[A-Za-z_]\w*(?:=[A-Za-z0-9_]+)?',d) for d in selected_defines):
        raise ValueError('unsupported selected define spelling')
    for kind in ('walker','static'):
        lines=list(dict.fromkeys(inc))+['+define+'+d for d in selected_defines]
        for name in files:
            if name==core and kind=='walker':lines.append(str(out/'walker_core.sv'))
            else:lines.append(overlays.get(name,str(source/name)))
        lines += [str(out/'wrapper.sv'),str(out/'tb.sv')]
        (out/(kind+'.f')).write_text('\n'.join(lines)+'\n')
    manifest=dict(source=str(source),schedule=str(schedule),master=master,variant=variant,
                  source_sha256=record['source_sha256'],overlay_scope='BF INSTANCE arguments only',
                  overlay_instances=count,cfg_image_instances=cfg_count,clock_ps=833,production_enabled=False,
                  hard_cfg_parameters={m:hard[m] for m in ('ot_s81_cfg7_seq','ot_s81_cfg7_seq_bfp')},
                  idle_q_assumption='Q leaf outputs stubbed to zero; BF-only active return composition',
                  native_family_hold=native_family,payload_skew_edges=4,
                  selected_defines=selected_defines)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--schedule',required=True)
    p.add_argument('--out',required=True);p.add_argument('--master',default='col_h9');p.add_argument('--variant',default='asb_x')
    p.add_argument('--native-bf-family',action='store_true')
    a=p.parse_args();prepare(a.source,a.schedule,a.out,a.master,a.variant,a.native_bf_family)
