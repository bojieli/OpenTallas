#!/usr/bin/env python3
"""Generate the complete HEAD START/reset source wiring from one composed plan.

Physical region clock ports and virtual-stage clock ports are deliberately
explicit for the clock-tree binder. No guessed clock wire or raw reset source
is installed. Full leaf-header bind/LEC and final clock assembly remain gates.
"""
import argparse,copy,hashlib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve();sys.path.insert(0,str(HERE.parents[1]/'die_plan'))
import schema as S
import gen_rtl as G
import clock_landings as C
from head_start_reset_aliases import declare,patch_rtl


def complete_top(text,plan,stages):
    wires={};unused=[];new_wires=[]
    for p in plan['partitions']:
        rows=plan['partition_types'][p['type']].get('reset_start_raw_exports',[])
        if not rows:continue
        pn=p['name'];mod=plan['partition_types'][p['type']]['module']
        pat=re.compile(r'(?m)^(    '+re.escape(mod)+r'(?: #\([^\n]*\))? '+re.escape(G.sv_id(pn))+r' \(\n)(.*?)(\n    \);)',re.S)
        m=pat.search(text)
        if not m:raise ValueError(f'missing native top instance {pn}')
        con=[]
        for r in rows:
            key=(pn,r['port'])
            if r.get('existing_port'):
                connections=re.findall(r'\.'+re.escape(r['existing_port'])+r'\(([^)]*)\)',m[2])
                if len(connections)!=1:raise ValueError('existing reset top output is not one connection')
                if connections[0]:
                    if not re.fullmatch(r'[A-Za-z_]\w*',connections[0]):raise ValueError('existing reset top net is not named')
                    wires[key]=connections[0]
                else:
                    w='wr_'+C.ident(pn)+'__'+r['existing_port'];wires[key]=w;new_wires.append(w)
                    old='.'+r['existing_port']+'()';replacement='.'+r['existing_port']+'('+w+')'
                    mbody=m[2].replace(old,replacement)
                    text=text[:m.start(2)]+mbody+text[m.end(2):]
                    m=pat.search(text)
            else:
                w='wr_'+C.ident(pn)+'__'+r['port'];wires[key]=w;new_wires.append(w)
                con.append('        .'+r['port']+'('+w+')')
        body=m[2].rstrip()+(',\n'+',\n'.join(con) if con else '')
        text=text[:m.start(2)]+body+text[m.end(2):]
    ports=stages['reset_ports'];used={(v['part'],v['port']) for v in ports.values()}
    if not used<=set(wires):raise ValueError('START reset provider has unknown export wire')
    unused=[dict(part=k[0],port=k[1],reason='uniform type export unused on this instance; actual raw registered Q') for k in sorted(set(wires)-used)]
    outs={o['net'] for o in stages['die_outputs']};decl=''
    # Native gen_rtl emits an ANSI header; remove only these exact old external
    # START input declarations, replacing them with internally driven wires.
    for n in sorted(outs):
        text,k=re.subn(r',\n    input  wire '+re.escape(n)+r'(?=[,\n])','',text)
        if k!=1:raise ValueError(f'{n}: expected one native external START input, found{k}')
        decl+='    wire '+n+';\n'
    h=re.search(r'(?m)^module \w+ \(.*?\n\);',text,re.S)
    if not h:raise ValueError('native ANSI top header missing')
    clocks=[s['clock_port'] for s in stages['stages']]
    addition=''.join(',\n    input wire '+n for n in clocks)
    text=text[:h.end()-3]+addition+text[h.end()-3:]
    h=re.search(r'(?m)^module \w+ \(.*?\n\);',text,re.S)
    decl+=''.join('    wire '+v+';\n' for v in sorted(new_wires))
    text=text[:h.end()]+ '\n'+decl+text[h.end():]
    con=['        .'+n+'('+wires[(v['part'],v['port'])]+')' for n,v in sorted(ports.items())]
    con+=['        .'+n+'('+n+')' for n in clocks+sorted(outs)]
    end=text.rfind('endmodule')
    text=text[:end]+'    ot_die_start_stages u_die_start_stages (\n'+',\n'.join(con)+'\n    );\n'+text[end:]
    return text,unused


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('compose');a.add_argument('provider');a.add_argument('exports');a.add_argument('--observer-spec',required=True);a.add_argument('--observer-rtl',required=True);a.add_argument('--out',required=True);a.add_argument('--origin-export-copy',action='append',default=[],help='carry an already-qualified retained START export-copy type into this source plan');a=a.parse_args()
    src=Path(a.compose);provider=Path(a.provider);out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    plan=json.load(open(src/'landed_plan.json'));side=json.load(open(src/'landed_sidecar.json'));exports=json.load(open(a.exports));stages=json.load(open(provider/'start_stages.json'))
    observer=json.load(open(a.observer_spec));side['collector']['observer']=observer;plan['clock']['landing_network']['root_observer']=observer
    for tn in a.origin_export_copy:
        if tn not in plan['partition_types']:raise ValueError('unknown retained origin-copy type '+tn)
        plan['partition_types'][tn].setdefault('clock',{})['landing_origin_export_copy']=True
    plan=declare(plan,exports);P=S.Plan(plan,src/'landed_plan.json');L=C.Landings(plan,side);ep=G.bus_epochs(P)
    observer_text=Path(a.observer_rtl).read_text();L.validate_observer_native(lambda tn:observer_text,G.parse_leaf_ports)
    (out/'ot_dp_cells.sv').write_text(G.CELLS)
    aliases=0;count=0;reused=0
    for tn,t in sorted(P.types.items()):
        if t.get('hard'):continue
        text=L.type_rtl(tn,G.wrapper(P,tn,ep))
        rows=exports['types'].get(tn,[]);text=patch_rtl(text,rows)
        (out/(t['module']+'.sv')).write_text(text);aliases+=sum(not r.get('existing_port') for r in rows);reused+=sum(bool(r.get('existing_port')) for r in rows);count+=1
    top=L.top_rtl(G.die_top(P,ep),{tn:t['module'] for tn,t in P.types.items()})
    top,spares=complete_top(top,plan,stages);(out/(G.sv_id(P.name)+'_top.sv')).write_text(top)
    (out/'start_stages.sv').write_bytes((provider/'start_stages.sv').read_bytes())
    (out/'source_plan.json').write_text(json.dumps(plan,indent=1)+'\n');(out/'source_sidecar.json').write_text(json.dumps(side,indent=1)+'\n')
    report=dict(types=count,uniform_raw_exports=aliases,reused_type_raw_outputs=reused,retained_origin_export_copy_types=a.origin_export_copy,reset_inputs=len(stages['reset_ports']),
        connected_start_outputs=len(stages['die_outputs']),unused_uniform_exports=spares,
        observer=observer,observer_rtl_sha256=hashlib.sha256(observer_text.encode()).hexdigest(),
        stage_clock_ports=len(stages['stages']),physical_clock_groups=len(set(side['count_aligned']['frame_clock_regions'].values())),
        scope='SOURCE ASSEMBLY: full leaf-header bind/LEC, real clock assembly, physical reset phase, and token pass NOT RUN',
        added_boot_cycles=stages['root_settle_guard']['added_boot_cycles'],added_steady_cycles=0)
    (out/'report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='unused_uniform_exports'}))
if __name__=='__main__':main()
