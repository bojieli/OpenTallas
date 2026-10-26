#!/usr/bin/env python3
"""Opt-in one-physical-clock adapters for alias-proven q3sync core templates.

No clocks are shorted and no legacy source is edited. The generated wrapper has
one physical `clk` pin and wires every qualified inner clock bit to it. Native
same-edge evidence is projected from the real producer and its testbench into a
small Yosys bit-identity vehicle. Physical use additionally requires the emitted
pin delta in the HBM plan batch and a newly reviewed clock tree.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from q3_sync_profile import mask, match_paren, parse_instance_at, split_top

TOPS = {
    'body': 'ot_hfd_coll_q3_body_core',
    'edge': 'ot_hfd_coll_q3_edge_core',
    'vm': 'ot_hfd_coll_q3_vm_core',
    'reduce': 'ot_hfd_coll_q2_reduce_core',
    'ring_ag': 'ot_hfd_coll_q2_ring_ag_core',
}
GLOBAL_WIDTHS = {'clk_program': 1, 'clk_control': 1, 'clk_issue': 1,
                 'clk_arg': 1, 'clk_vmasm': 16, 'clk_upipe': 16,
                 'clk_qslots': 29, 'clk_ring': 17, 'clk_reduce': 33,
                 'clk_vmwrite': 16, 'clk_link': 15}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ports(text, top):
    m = re.search(r'\bmodule\s+'+re.escape(top)+r'\s*\(', mask(text))
    if not m:
        raise ValueError('missing fixed ANSI profile top '+top)
    a = m.end()-1; b = match_paren(mask(text), a)
    out = []
    for item in split_top(mask(text[a+1:b-1]), text[a+1:b-1], r','):
        q = re.fullmatch(r'\s*(input|output|inout)\s+(?:(?:wire|logic|reg)\s+)?'
                         r'(?:(signed|unsigned)\s+)?((?:\[\s*\d+\s*:\s*\d+\s*\]\s*)*)([A-Za-z_]\w*)\s*', item)
        if not q:
            raise ValueError('nonliteral or ambiguous port: '+item[:100])
        width=1
        for hi,lo in re.findall(r'\[\s*(\d+)\s*:\s*(\d+)\s*\]',q[3]):
            width *= abs(int(hi)-int(lo))+1
        out.append(dict(name=q[4], direction=q[1], signed=q[2] or '', dims=q[3].strip(), width=width))
    if not out or len({p['name'] for p in out}) != len(out):
        raise ValueError('empty/duplicate interface')
    return out


def connections(text, module, macro=False):
    """Only actual named cell instances, never declarations or comments."""
    s=mask(text); found=[]
    pat=(r'`'+re.escape(module)+r'\b') if macro else r'\b'+re.escape(module)+r'\b'
    for m in re.finditer(pat,s):
        ins=parse_instance_at(s,m.end())
        if ins is None:
            continue
        _,a,b=ins; conn={}
        for item in split_top(s[a+1:b-1],text[a+1:b-1],r','):
            q=re.fullmatch(r'\s*\.([A-Za-z_]\w*)\s*\((.*)\)\s*',item,re.S)
            if not q or q[1] in conn:
                raise ValueError('positional/ambiguous native connection')
            conn[q[1]]=q[2].strip()
        found.append(conn)
    return found


def common_expr(expr, clk='clk'):
    expr=re.sub(r'\s+','',expr)
    if expr==clk:
        return True
    # Keep the actual native repetition count expression; Yosys resolves its
    # width with the same NLINK=3 specialization as the selected q3 template.
    return bool(re.fullmatch(r'\{[A-Za-z_0-9()+*]+\{'+re.escape(clk)+r'\}\}',expr))


def native_expr(expr):
    """A role must be a literal slice of a real native clock input, no logic."""
    expr=expr.strip()
    if expr.startswith('{') and expr.endswith('}'):
        parts=split_top(mask(expr[1:-1]),expr[1:-1],r',')
        if len(parts)<2:raise ValueError('unproven native clock concatenation')
        return set().union(*(native_expr(p)for p in parts))
    q=re.fullmatch(r'\s*([A-Za-z_]\w*)\s*(\[\s*\d+\s*(?::\s*\d+\s*)?\])?\s*',expr)
    if not q or q[1] not in GLOBAL_WIDTHS:
        raise ValueError('unproven native clock expression: '+expr)
    if q[2]:
        ns=[int(v) for v in re.findall(r'\d+',q[2])]
        if max(ns)>=GLOBAL_WIDTHS[q[1]]:
            raise ValueError('native clock slice out of range')
    return {q[1]}


def declaration(p, direction=None):
    return ' '.join(x for x in [direction or p['direction'],'wire',p['signed'],p['dims'],p['name']] if x)


def emit(profile_dir, role_contract, native, testbench, out, census_path=None):
    profile_dir,out=Path(profile_dir),Path(out);out.mkdir(parents=True,exist_ok=True)
    role_contract=json.loads(Path(role_contract).read_text())
    if census_path is None:raise ValueError('qualified q3sync census required')
    census=json.loads(Path(census_path).read_text())
    if (census.get('status')!='PASS_GENERATED' or census.get('unclassified_total') or
        census.get('unresolved_instantiations') or not census.get('inputs_clean_at_commit') or
        census.get('modules_in_closure')!=32):
        raise ValueError('unqualified q3sync source closure')
    nt,bt=Path(native).read_text(),Path(testbench).read_text()
    for name,width in GLOBAL_WIDTHS.items():
        hits=re.findall(r'(?m)^\s*input\s*(?:wire\s*)?(\[\s*\d+\s*:\s*\d+\s*\])?\s*'+re.escape(name)+r'\s*;',mask(nt))
        if len(hits)!=1:raise ValueError('ambiguous native clock declaration '+name)
        nums=[int(x)for x in re.findall(r'\d+',hits[0])]
        actual=abs(nums[0]-nums[1])+1 if nums else 1
        if actual!=width:raise ValueError('native clock specialization width changed '+name)
    tbi=connections(bt,'DUT',macro=True)
    if len(tbi)!=1:
        raise ValueError('native testbench needs one explicit DUT instance')
    aliases=tbi[0]
    for p in GLOBAL_WIDTHS:
        if p not in aliases or not common_expr(aliases[p]):
            raise ValueError('native common edge not proven for '+p)
    # Fixed native model shape is intentional: never generalize this evidence to
    # H0/H1 clk_pair or another NLINK/phase specialization.
    nl=re.search(r'\bNLINK\s*=\s*(\d+)',mask(bt))
    if not nl or int(nl[1])!=3:
        raise ValueError('qualified native phase certificate is NLINK=3 only')
    probe=['`timescale 1ps/1ps']
    records={}; instance_lines=[]
    for core,legacy in TOPS.items():
        top=legacy+'__q3sync';path=profile_dir/(top+'.sv')
        text=path.read_text();ps=ports(text,top)
        clocks=set(role_contract['cores'][core]['clocks'])
        if clocks!=set(census['totals_per_core'][core]['clocks']['top_clock_ports']):
            raise ValueError('incomplete clock roles vs qualified elaborated census '+core)
        by={p['name']:p for p in ps}
        if not clocks or not clocks<=by.keys() or any(by[n]['direction']!='input' for n in clocks):
            raise ValueError('clock role inventory mismatch '+core)
        if 'clk' in by and 'clk' not in clocks:
            raise ValueError('canonical clock collides with data port')
        ni=connections(nt,legacy)
        if len(ni)!=1:
            raise ValueError(f'{core}: expected one native split instance, found{len(ni)}')
        for c in clocks:
            if c not in ni[0]:raise ValueError(core+': native clock missing '+c)
            native_expr(ni[0][c])
        new=top+'__oneclk';data=[p for p in ps if p['name']not in clocks]
        lines=['// GENERATED opt-in clock adapter: inner RTL/reset/data unchanged.',
               '`timescale 1ns/1ps','`default_nettype none',
               'module '+new+' (', '    input wire clk,' if data else '    input wire clk']
        lines.extend('    '+declaration(p)+(',' if j<len(data)-1 else '') for j,p in enumerate(data))
        lines+=[');','    '+top+' u_core (']
        cs=[]
        for p in ps:
            expr=('clk' if p['width']==1 else '{'+str(p['width'])+'{clk}}') if p['name']in clocks else p['name']
            cs.append('        .'+p['name']+'('+expr+')')
        lines += [',\n'.join(cs),'    );','endmodule','`default_nettype wire']
        target=out/(new+'.sv');target.write_text('\n'.join(lines)+'\n')
        cp=[p for p in ps if p['name']in clocks]
        stub='q3_'+core+'_clock_stub'
        probe += ['(* blackbox *) module '+stub+' (',',\n'.join('    '+declaration(p,'input') for p in cp),'); endmodule']
        instance_lines += ['  '+stub+' '+core+' (',',\n'.join('    .'+p['name']+'('+ni[0][p['name']]+')' for p in cp),'  );']
        records[core]=dict(top=top, wrapper=new, source_sha256=sha(path),wrapper_sha256=sha(target),
            clocks=[dict(name=p['name'],width=p['width'],native_connection=ni[0][p['name']]) for p in cp],
            data_ports=data,nonclock_bits=sum(p['width']for p in data),
            dropped_clock_bits=sum(p['width']for p in cp),new_clock_bits=1,
            data_cycle_delta=0,boot_cycle_delta=0,defines_delta=[],
            physical='NOT_BUILT: apply clock pin delta to HBM plan batch then review new common-root stage')
    probe += ['module native_clock_alias_probe(input wire clk);','  localparam NLINK=3;']
    for p,w in GLOBAL_WIDTHS.items():
        probe += [f'  wire [{w-1}:0] {p} = {aliases[p]};']
    probe += instance_lines+['endmodule']
    (out/'native_clock_alias_probe.sv').write_text('\n'.join(probe)+'\n')
    cert=dict(schema='opentallas.q3.common_clock.v1',status='NEEDS_BIT_ID_PROOF',
        period_ps=833,edge='posedge',native_sha256=sha(native),testbench_sha256=sha(testbench),
        profile_census_sha256=sha(census_path),profile_source_commit=census['source_commit'],
        profile_generated_files={e['source']:sha(profile_dir/e['emitted'])for e in census['emitted']},
        native_clock_bindings={p:aliases[p]for p in GLOBAL_WIDTHS},cores=records,
        signoff='NOT_RUN',phase_scope='qualified q3 NLINK3 native scalar aliases only; H0/H1 excluded')
    (out/'manifest.json').write_text(json.dumps(cert,indent=2)+'\n')
    return cert


def check_bits(netlist, manifest):
    x=json.loads(Path(netlist).read_text());m=json.loads(Path(manifest).read_text())
    top=x['modules']['native_clock_alias_probe'];root=top['ports']['clk']['bits']
    if len(root)!=1 or not isinstance(root[0],int):raise ValueError('missing native scalar clock bit')
    total=0
    for core,r in m['cores'].items():
        cell=top['cells'][core]
        for p in r['clocks']:
            bits=cell['connections'][p['name']]
            if len(bits)!=p['width'] or any(b!=root[0] for b in bits):
                raise ValueError(f"{core}.{p['name']}: native clock bit alias/phase mismatch")
            total+=len(bits)
    return dict(status='PASS_NATIVE_BIT_IDS',clock_bits=total,canonical_bit=root[0],netlist_sha256=sha(netlist))


def emit_edge_miter(out, mutant=None):
    """Small mechanism vehicle: every actual alias bit clocks data/valid/fault.

    Inner arithmetic and reset RTL are unchanged; this proves the only adapter
    mechanism, including each vector clock bit and both half-edge observations.
    """
    out=Path(out);m=json.loads((out/'manifest.json').read_text())
    lines=['`timescale 1ps/1fs','module tb;','reg clk=0; always #416.5 clk=~clk;',
           'realtime last=-1;always @(posedge clk)begin if(last>=0&&$realtime-last!=833.0)$fatal(1,"PERIOD");last=$realtime;end',
           'localparam NLINK=3;']
    for p,w in GLOBAL_WIDTHS.items():lines.append(f"wire[{w-1}:0] {p}={m['native_clock_bindings'][p]};")
    count=sum(p['width']for r in m['cores'].values()for p in r['clocks'])
    lines += [f'localparam N={count};','reg[N-1:0] d=1,nq=0,cq=0,nv=0,cv=0,nf=0,cf=0;']
    j=0
    for core,r in m['cores'].items():
        text=(out/(r['wrapper']+'.sv')).read_text()
        cc=connections(text,r['top'])
        if len(cc)!=1:raise ValueError('adapter does not contain exactly one unchanged inner core')
        cp=ports(text,r['wrapper'])
        expected=[dict(name='clk',direction='input',signed='',dims='',width=1)]+r['data_ports']
        if cp!=expected:raise ValueError('adapter changes non-clock interface')
        for p in r['data_ports']:
            if cc[0].get(p['name'])!=p['name']:raise ValueError('adapter changes data/control wire '+p['name'])
        for p in r['clocks']:
            tag=core+'_'+p['name'];width=p['width'];cand=cc[0][p['name']]
            if mutant==core+'.'+p['name']:cand='~('+cand+')'
            lines += [f"wire[{width-1}:0] n_{tag}={p['native_connection']};",
                      f"wire[{width-1}:0] c_{tag}={cand};"]
            for bit in range(width):
                lines += [f'always @(posedge n_{tag}[{bit}]) begin nq[{j}]<=d[{j}];nv[{j}]<=d[{(j+1)%count}];nf[{j}]<=~d[{(j+2)%count}];end',
                          f'always @(posedge c_{tag}[{bit}]) begin cq[{j}]<=d[{j}];cv[{j}]<=d[{(j+1)%count}];cf[{j}]<=~d[{(j+2)%count}];end']
                j+=1
    lines += ['integer k,i;initial begin',
              'for(k=0;k<500;k=k+1)begin',
              '@(posedge clk);#1;if(k>=2&&(nq!==cq||nv!==cv||nf!==cf))$fatal(1,"CLOCK_ADAPTER_MISMATCH posedge %0d",k);',
              '#50;for(i=0;i<N;i=i+1)d[i]=$random;',
              '@(negedge clk);#1;if(k>=2&&(nq!==cq||nv!==cv||nf!==cf))$fatal(1,"CLOCK_ADAPTER_MISMATCH negedge %0d",k);',
              'end $display("CLOCK_ADAPTER_PASS 500 edges,147 data/valid/fault lanes");$finish;end','endmodule']
    p=out/('edge_miter_mutant.sv'if mutant else'edge_miter.sv');p.write_text('\n'.join(lines)+'\n');return p


def check_adapter(netlist, manifest, core):
    m=json.loads(Path(manifest).read_text());r=m['cores'][core]
    x=json.loads(Path(netlist).read_text())['modules'][r['wrapper']]
    if set(x['ports'])!={'clk'}|{p['name']for p in r['data_ports']}:
        raise ValueError('changed physical data interface')
    cell=x['cells']['u_core'];root=x['ports']['clk']['bits']
    if len(x['cells'])!=1 or cell['type']!=r['top']:
        raise ValueError('adapter must contain only the unchanged qualified core')
    total=0
    for p in r['clocks']:
        if cell['connections'][p['name']]!=root*p['width']:
            raise ValueError('inner clock bit differs from canonical clock')
    for p in r['data_ports']:
        if cell['connections'][p['name']]!=x['ports'][p['name']]['bits']:
            raise ValueError('changed data/valid/fault/reset bit '+p['name'])
        total+=p['width']
    return dict(status='PASS_ADAPTER_BIT_IDS',core=core,nonclock_bits=total,
                netlist_sha256=sha(netlist))


def emit_stub(out):
    out=Path(out);m=json.loads((out/'manifest.json').read_text());lines=[]
    for r in m['cores'].values():
        source=ports((out/(r['wrapper']+'.sv')).read_text(),r['wrapper'])
        clocks=[dict(name=p['name'],direction='input',width=p['width'],signed='',
                     dims=''if p['width']==1 else f"[{p['width']-1}:0]")for p in r['clocks']]
        lines+=['(* blackbox *) module '+r['top']+' (',',\n'.join(declaration(p)for p in clocks+r['data_ports']),'); endmodule']
    p=out/'qualified_core_port_stubs.sv';p.write_text('\n'.join(lines)+'\n');return p


def qualify(out):
    import subprocess,time
    out=Path(out).resolve();run=out/f'gate_{time.time_ns()}';run.mkdir()
    m=json.loads((out/'manifest.json').read_text());tool=Path(__file__).resolve()
    def command(name,args,expect=0):
        p=subprocess.run(args,capture_output=True,text=True)
        (run/(name+'.log')).write_text(p.stdout+p.stderr)
        if expect==0 and p.returncode:
            raise ValueError(name+' failed; see '+str(run/(name+'.log')))
        return p
    def ys(name,files,top):
        target=run/(name+'.json')
        command(name,['yosys','-Q','-T','-p',
            'read_verilog -sv '+' '.join(str(p)for p in files)+
            '; hierarchy -top '+top+'; proc; write_json '+str(target)])
        return target
    try:
        n=ys('native_alias',[out/'native_clock_alias_probe.sv'],'native_clock_alias_probe')
        native=check_bits(n,out/'manifest.json')
        stub=emit_stub(out);adapters=[]
        for core,r in m['cores'].items():
            n=ys(core+'_adapter',[stub,out/(r['wrapper']+'.sv')],r['wrapper'])
            adapters.append(check_adapter(n,out/'manifest.json',core))
        bench=emit_edge_miter(out)
        binary=run/'positive.out';command('edge_compile',['iverilog','-g2012','-s','tb','-o',str(binary),str(bench)])
        p=command('edge_run',['vvp',str(binary)])
        if 'CLOCK_ADAPTER_PASS'not in p.stdout:raise ValueError('edge miter lacks completed verdict')
        bench=emit_edge_miter(out,'edge.arg_clk');binary=run/'mutant.out'
        command('mutant_compile',['iverilog','-g2012','-s','tb','-o',str(binary),str(bench)])
        p=command('mutant_run',['vvp',str(binary)],expect=None)
        if p.returncode==0 or'CLOCK_ADAPTER_MISMATCH'not in p.stdout:
            raise ValueError('wrong inner clock mutant survived or failed for another cause')
        # Independent bit-ID negative control catches a changed physical source
        # even without relying on simulation data or initialization.
        text=(out/'native_clock_alias_probe.sv').read_text()
        old='.arg_clk('+next(p['native_connection']for p in m['cores']['edge']['clocks']if p['name']=='arg_clk')+')'
        if text.count(old)!=1:raise ValueError('ambiguous native clock mutant location')
        text=text.replace('module native_clock_alias_probe(input wire clk);',
                          'module native_clock_alias_probe(input wire clk); wire badclk=~clk;').replace(old,'.arg_clk(badclk)')
        mutant=run/'wrong_native_clock.sv';mutant.write_text(text)
        n=ys('wrong_native_clock',[mutant],'native_clock_alias_probe')
        try:check_bits(n,out/'manifest.json')
        except ValueError:pass
        else:raise ValueError('native bit-ID mutant survived')
        result=dict(status='PASS_CLOCK_ADAPTER',scope='clock adapter only; numeric bodies unchanged and not requalified here',
            manifest_sha256=sha(out/'manifest.json'),native=native,adapter_bit_proofs=adapters,
            nonclock_bits=sum(r['nonclock_bits']for r in adapters),edge_miter=dict(period_ps=833,cycles=500,
            clock_lanes=native['clock_bits'],signals=['data','valid','fault'],warmup_edges=2,verdict='PASS'),
            mutants=dict(wrong_inner_clock='CAUGHT negedge2',wrong_native_bit_source='CAUGHT'),
            data_cycle_delta=0,boot_cycle_delta=0,defines_delta=[],physical='NOT_BUILT',run_dir=run.name,
            wrappers={r['wrapper']:sha(out/(r['wrapper']+'.sv'))for r in m['cores'].values()})
        (run/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
        # Convenience copy is created only once; failed attempts retain their own
        # immutable run directory and can never be overwritten by a later pass.
        target=out/'qualification.json'
        if target.exists():raise ValueError('qualification.json already exists; use a fresh output directory')
        target.write_text(json.dumps(result,indent=2)+'\n')
        return result
    except Exception as exc:
        (run/'failure.json').write_text(json.dumps(dict(status='FAIL',cause=str(exc)),indent=2)+'\n')
        raise


def adapt_recipe(core, recipe, staged, receipt, adapter_dir):
    """Attach a proven adapter to the existing q3 source-profile API.

    The plan module identity may stay unchanged, but its clock pin table MUST
    have only `clk`; the ordinary source/plan interface gate enforces this.
    """
    import copy
    d=Path(adapter_dir).resolve();m=json.loads((d/'manifest.json').read_text())
    q=json.loads((d/'qualification.json').read_text());r=m['cores'][core]
    if (q.get('status')!='PASS_CLOCK_ADAPTER' or q.get('manifest_sha256')!=sha(d/'manifest.json') or
        q.get('data_cycle_delta')!=0 or q.get('boot_cycle_delta')!=0 or q.get('defines_delta')!=[] or
        q.get('edge_miter',{}).get('period_ps')!=833 or q.get('native',{}).get('clock_bits')!=147):
        raise ValueError('common clock adapter qualification missing or mismatched')
    path=d/(r['wrapper']+'.sv')
    if (q['wrappers'].get(r['wrapper'])!=sha(path) or r['wrapper_sha256']!=sha(path) or
        receipt['port_inventory']['top']!=r['top'] or recipe['profile_top']!=r['top'] or
        any(m['profile_generated_files'].get(rel)!=digest for rel,digest in receipt['generated_files'].items())):
        raise ValueError('common clock adapter does not match selected qualified source')
    old={tuple(p)for p in receipt['port_inventory']['ports']}
    clocks={p['name']for p in r['clocks']}
    data={(p['name'],p['direction'],p['width'])for p in r['data_ports']}
    if {p for p in old if p[0]not in clocks}!=data:
        raise ValueError('common clock adapter changes selected data/reset interface')
    if {p[0]for p in old if p[0]in clocks}!=set(receipt['clock_ports']):
        raise ValueError('common clock adapter clock role inventory mismatch')
    rec,st,rc=copy.deepcopy(recipe),dict(staged),copy.deepcopy(receipt)
    rel='tools/hbm_b2/q3sync/oneclk/'+path.name
    rec['files']=list(rec['files'])+[rel];rec['profile_top']=r['wrapper'];st[rel]=path
    rc['clock_ports']=['clk'];rc['generated_files'][rel]=sha(path)
    ps=ports(path.read_text(),r['wrapper'])
    rc['port_inventory']=dict(method='qualified common-clock adapter literal ANSI',top=r['wrapper'],
        ports=[(p['name'],p['direction'],p['width'])for p in ps],source_file=rel,source_sha256=sha(path))
    rc['common_clock_adapter']=dict(generator='tools/hbm_b2/q3sync/q3_common_clock.py',
        manifest_sha256=sha(d/'manifest.json'),qualification_sha256=sha(d/'qualification.json'),
        native_bit_proof=q['native'],original_clock_bits=r['dropped_clock_bits'],
        physical_clock_pin='clk',data_cycle_delta=0,boot_cycle_delta=0,defines_delta=[],
        physical='NOT_BUILT: requires explicit HBM clock-pin plan batch and new geometry review')
    return rec,st,rc


def main():
    a=argparse.ArgumentParser();sp=a.add_subparsers(dest='command',required=True)
    e=sp.add_parser('emit')
    for k in ['profile-dir','clock-roles','native','testbench','out','profile-census']:e.add_argument('--'+k,required=True)
    c=sp.add_parser('check-bits');c.add_argument('--netlist',required=True);c.add_argument('--manifest',required=True)
    b=sp.add_parser('edge-miter');b.add_argument('--out',required=True);b.add_argument('--mutant')
    d=sp.add_parser('check-adapter');d.add_argument('--netlist',required=True);d.add_argument('--manifest',required=True);d.add_argument('--core',choices=TOPS,required=True)
    f=sp.add_parser('emit-stubs');f.add_argument('--out',required=True)
    g=sp.add_parser('qualify');g.add_argument('--out',required=True)
    v=a.parse_args()
    try:
        if v.command=='emit':r=emit(v.profile_dir,v.clock_roles,v.native,v.testbench,v.out,v.profile_census)
        elif v.command=='check-bits':r=check_bits(v.netlist,v.manifest)
        elif v.command=='check-adapter':r=check_adapter(v.netlist,v.manifest,v.core)
        elif v.command=='emit-stubs':print(emit_stub(v.out));return
        elif v.command=='qualify':r=qualify(v.out)
        else:
            print(emit_edge_miter(v.out,v.mutant));return
    except (ValueError,KeyError,FileNotFoundError)as exc:
        raise SystemExit('NOT_QUALIFIED: '+str(exc))
    print(json.dumps(dict(status=r['status'],cores=len(r.get('cores',{})),clock_bits=r.get('clock_bits'))))

if __name__=='__main__':main()
