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


def cfg_source_census(text,master):
    profiles={'col_h9':{'r0':range(0,5),'r1':range(5,10),'r2':range(10,15),'r0_nx':range(0,5)},
              'col_h10':{'r0':range(0,6),'r1':range(6,11),'r2':range(11,16),'r0_nx':range(0,6)}}
    if master not in profiles:raise ValueError('unsupported actual frame master')
    expected={master+'_l4_lp_'+part:{f'u_c{pair}_{bank}' for pair in pairs for bank in range(7)}
              for part,pairs in profiles[master].items()}
    census={}
    for m in re.finditer(r'^\s*module\s+(\w+)\b(.*?)^\s*endmodule\b',text,re.M|re.S):
        names=re.findall(r'\bot_rom_4096x72_m8\s+(u_\w+)\s*\(',m[2])
        mentions=len(re.findall(r'\bot_rom_4096x72_m8\b',m[2]))
        if not mentions:continue
        if (m[1] not in expected or m[1] in census or mentions!=len(names)
                or len(names)!=len(set(names)) or set(names)!=expected[m[1]]):
            raise ValueError('actual per-module CFG bank identity set differs: '+m[1])
        census[m[1]]=len(names)
    if set(census)!=set(expected):raise ValueError('actual frame CFG module set differs')
    return census


XO_MONITOR='''        if (live) begin
            if (xo !== x_d) begin
                if (xo_checked < 1000000) $display("XO_MISMATCH edge %0d", edge_n);
            end
            xo_checked <= xo_checked + 1;
        end'''


def nx_testbench(text,plan,master):
    """NX has no XO port; do not apply the X-master forwarding monitor to it."""
    module=re.search(r'\bmodule\s+'+re.escape(master)+r'_l4_lp_asb_nx\b(.*?)\bendmodule',plan,re.S)
    if not module or re.search(r'\boutput\b[^;]*\bxo\b',module[1],re.S):
        raise ValueError('NX monitor scope requires an actual selected master without XO output')
    if text.count(XO_MONITOR)!=1:raise ValueError('original frame XO monitor changed')
    return text.replace(XO_MONITOR,'        // Selected NX master has no XO pins; xo_checked remains0.\n'
                        '        // RET, source fault and spine fault monitors remain active.')


def selected_plan_kit(record, source, master):
    """The plan kit the selected frame schedule actually binds.  A frame root (layer_prog/frame_root.py) names a kit
    from outside its base by ext/<absolute path>; the measurement pin (xs_bf.qualify_asbuilt_measurement) is the
    canonical rtl path, so that path must hold the same bytes."""
    plan = f'rtl/dsrom_sys/s81_dv/frame_lp/plan/{master}_l4_lp_plan_kit.sv'
    kits = [n for n in record['source_sha256'] if Path(n).name == Path(plan).name]
    if len(kits) != 1:
        raise ValueError('selected frame schedule must bind exactly one plan kit: '+str(kits))
    if kits[0] != plan and (source/plan).read_bytes() != (source/kits[0]).read_bytes():
        raise ValueError('selected plan kit differs from the source root plan path: '+kits[0])
    return plan, kits[0]


def quiescent_q(source, name, module):
    """Q leaf stub: every output tied 0 (BF-only active return composition)."""
    text=(source/name).read_text();start=text.index('module '+module)
    left=text.index('(',start);right=close_paren(text,left)
    left=text.index('(',right);right=close_paren(text,left)
    header=text[start:right]+';'
    outputs=re.findall(r'\boutput\s+wire\s+(?:\[[^]]+\]\s*)?(\w+)',header)
    if len(outputs)<3:raise ValueError('Q quiescent stub output schema changed')
    return '`timescale 1ns/1ps\n'+header+'\n'+''.join("assign "+n+" = '0;\n" for n in outputs)+'endmodule\n'


def bind_station_cell(source):
    """The bind's own whole-bus station register ot_dp_st, verbatim from tools/die_plan/bind.py CELLS (the cell the bind
    emits for every bound lane station, u_ist_<bus>_<j>; tools/die_plan/ts_relay_miter.py)."""
    import ast
    name='tools/die_plan/bind.py'
    tree=ast.parse((Path(__file__).resolve().parents[3]/name).read_text())
    cells=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
               and any(isinstance(t,ast.Name) and t.id=='CELLS' for t in n.targets))
    m=re.search(r'^\(\*[^\n]*\*\)\s*\nmodule ot_dp_st\b.*?^endmodule\b|^module ot_dp_st\b.*?^endmodule\b',cells,re.M|re.S)
    if not m:raise ValueError('bind CELLS has no ot_dp_st station cell')
    return name,'`timescale 1ns/1ps\n'+m[0]+'\n'


def bound_seams(text, top, depths):
    """The frame wrapper `top` with the bound plan's fint depths: each s81b_fint u_s<i><j> (2 boundary flops) is followed
    by depth - 2 whole-bus ot_dp_st stations on its q, exactly the stages frame_schedule_asb.py --bound-plan traces
    (SEAM_EXTRA) and the bind emits for the plan's fi_* lanes."""
    m=re.search(r'^module\s+'+re.escape(top)+r'\b.*?^endmodule\b',text,re.M|re.S)
    if not m:raise ValueError('frame wrapper missing: '+top)
    body,seen=m[0],set()
    def stage(mm):
        w,seam,cka,ckb,d,q=mm.groups()
        seen.add(seam)
        k=depths[seam]-2
        if k<0:raise ValueError('bound seam shallower than the as-built 2 flops: '+seam)
        if k==0:return mm[0]
        lines=[f'wire [{w}-1:0] {seam}_bq0;',f's81b_fint #(.W({w})) {seam} (.cka({cka}), .ckb({ckb}), .d({d}), .q({seam}_bq0));']
        for j in range(1,k+1):
            nxt=q if j==k else f'{seam}_bq{j}'
            if j<k:lines.append(f'wire [{w}-1:0] {nxt};')
            lines.append(f'ot_dp_st #(.W({w})) u_ist_{seam[2:]}_{j} (.clk({ckb}), .rst_n(rst_n), .d({seam}_bq{j-1}), '
                         f'.ea(1\'b0), .q({nxt}), .eq());')
        return '\n    '.join(lines)
    new=re.sub(r's81b_fint\s*#\(\.W\((\d+)\)\)\s*(u_s\d\d)\s*\(\.cka\((\w+)\),\s*\.ckb\((\w+)\),\s*\.d\((\w+)\),\s*\.q\((\w+)\)\);',
               stage,body)
    if seen!=set(depths):raise ValueError(f'bound plan seams {sorted(depths)} differ from the wrapper seams {sorted(seen)}')
    return text.replace(body,new)


def prepare(source, schedule, out, master='col_h9', variant='asb_x', native_family=False,
            defines_manifest='asbuilt_kva3_g3tag2_sel.json', bound_plan=None):
    if variant not in ('asb_x','asb_nx'):raise ValueError('unsupported actual frame variant')
    source, schedule, out = Path(source), Path(schedule), Path(out)
    out.mkdir(parents=True, exist_ok=False)
    record = json.loads(schedule.read_text())
    for name, sha in record['source_sha256'].items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest() != sha:
            raise ValueError('selected frame source changed: '+name)
    overlays = {}
    plan, kit = selected_plan_kit(record, source, master)
    text = (source/kit).read_text()
    plan_text = text
    selected_wrapper=(source/'physical/die_plan/s81/bind/models/s81_asb_models.sv').read_text()
    cfg_census=cfg_source_census(text,master)
    # These INSTANCE arguments are precisely the missing simulation image rule;
    # they do not alter any port, arithmetic, clock or state transition.
    pattern = r'\b(dsfd_bf_col|dsfd_bf_front_roots)\s+(u_e\d+[we]?)\s*\('
    text, count = re.subn(pattern, lambda m: m[1]+' #(.INSTANCE({INSTANCE, "_'+m[2][2:]+'"})) '+m[2]+' (', text)
    if count != (12 if master=='col_h9' else 15):
        raise ValueError('unexpected actual BF front/column identity count: '+str(count))
    text,cfg_count=re.subn(r'\bot_rom_4096x72_m8\s+(u_c\d+_[0-6])\s*\(',
                          lambda m:'ot_rom_4096x72_m8 #(.INSTANCE({INSTANCE, "_'+m[1][2:]+'"})) '+m[1]+' (',text)
    if cfg_count!=sum(cfg_census.values()):raise ValueError('CFG overlay differs from source census')
    overlay = out/Path(plan).name
    overlay.write_text(text); overlays[plan] = overlays[kit] = str(overlay)
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
    # The GB plan kits (DIE-S81-65) instantiate the split rom_q element instead; it is quiesced the same way.
    quiet=['ot_v41_rom_elem_q_qxpq_w10']
    if re.search(r'^\s*ot_v41_rom_elem_q_qxpq_w10_gb_split\b',plan_text,re.M):quiet.append('ot_v41_rom_elem_q_qxpq_w10_gb_split')
    for module in quiet:
        qname=f'rtl/v41rom/{module}.sv'
        overlay=out/('quiescent_q.sv' if module=='ot_v41_rom_elem_q_qxpq_w10' else f'quiescent_{module}.sv')
        overlay.write_text(quiescent_q(source,qname,module))
        overlays[qname]=str(overlay)
    # Bound plan seam depths (S81-FRAME-FIX-1 11-11): a schedule traced with --bound-plan composes returns over the
    # plan's fint depths; the bench must carry the same stages, else every BF / q return through a deepened seam is early.
    bound=None
    sb=record.get('bound_plan')
    if (sb is None)!=(bound_plan is None):
        raise ValueError('bench bound plan must match the schedule: schedule '+str(sb and sb.get('plan'))+', bench '+str(bound_plan))
    if bound_plan is not None:
        raw=Path(bound_plan).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=sb['plan_sha256']:
            raise ValueError('bench bound plan differs from the schedule\'s: '+str(bound_plan))
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        import frame_schedule_asb as FSA
        depths=FSA.bound_seam_depths(json.loads(raw),master)
        if depths!=sb['seam_depths']:raise ValueError(f'bound seam depths {depths} differ from the schedule {sb["seam_depths"]}')
        wname='physical/die_plan/s81/bind/models/s81_asb_models.sv'
        if wname not in record['source_sha256']:raise ValueError('schedule does not bind the frame wrapper '+wname)
        overlay=out/'s81_asb_models_bound.sv'
        overlay.write_text(bound_seams(selected_wrapper,f'{master}_l4_lp_{variant}',depths));overlays[wname]=str(overlay)
        cname,cell=bind_station_cell(source)
        (out/'bind_station_cell.sv').write_text(cell)
        bound=dict(plan=str(bound_plan),plan_sha256=sb['plan_sha256'],seam_depths=depths,
                   seam_extra_stages={k:d-2 for k,d in depths.items() if d>2},station_cell=cname,
                   station_cell_sha256=hashlib.sha256((Path(__file__).resolve().parents[3]/cname).read_bytes()).hexdigest())
    tb ='rtl/dsrom_sys/s81_dv/frame/test/tb_s81dv_frame.sv'
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
    if variant=='asb_nx':text=nx_testbench(text,selected_wrapper,master)
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
    selected_defines=json.loads((source/defines_manifest).read_text())['defines']
    if any(not re.fullmatch(r'[A-Za-z_]\w*(?:=[A-Za-z0-9_]+)?',d) for d in selected_defines):
        raise ValueError('unsupported selected define spelling')
    for kind in ('walker','static'):
        lines=list(dict.fromkeys(inc))+['+define+'+d for d in selected_defines]
        for name in files:
            if name==core and kind=='walker':lines.append(str(out/'walker_core.sv'))
            else:lines.append(overlays.get(name,str(source/name)))
        if bound is not None:lines.append(str(out/'bind_station_cell.sv'))
        lines += [str(out/'wrapper.sv'),str(out/'tb.sv')]
        (out/(kind+'.f')).write_text('\n'.join(lines)+'\n')
    manifest=dict(source=str(source),schedule=str(schedule),master=master,variant=variant,
                  source_sha256=record['source_sha256'],overlay_scope='BF INSTANCE arguments only',
                  overlay_instances=count,cfg_image_instances=cfg_count,cfg_module_census=cfg_census,clock_ps=833,production_enabled=False,
                  hard_cfg_parameters={m:hard[m] for m in ('ot_s81_cfg7_seq','ot_s81_cfg7_seq_bfp')},
                  idle_q_assumption='Q leaf outputs stubbed to zero; BF-only active return composition',
                  native_family_hold=native_family,payload_skew_edges=4,
                  xo_forwarding_qualification='NOT_APPLICABLE_NO_XO_PORT' if variant=='asb_nx' else 'CHECKED',
                  selected_defines=selected_defines,defines_manifest=defines_manifest,plan_kit=kit,
                  plan_kit_sha256=hashlib.sha256((source/kit).read_bytes()).hexdigest(),quiescent_q_modules=quiet,
                  bound_plan=bound)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--schedule',required=True)
    p.add_argument('--out',required=True);p.add_argument('--master',default='col_h9');p.add_argument('--variant',default='asb_x')
    p.add_argument('--native-bf-family',action='store_true')
    p.add_argument('--defines-manifest',default='asbuilt_kva3_g3tag2_sel.json',help='source-root manifest whose defines the bench uses')
    p.add_argument('--bound-plan',default=None,help='the plan the schedule was traced with (frame_schedule_asb.py --bound-plan)')
    a=p.parse_args();prepare(a.source,a.schedule,a.out,a.master,a.variant,a.native_bf_family,a.defines_manifest,a.bound_plan)
