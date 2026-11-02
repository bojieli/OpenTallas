#!/usr/bin/env python3
"""Build fail-closed TT FF/clock inventories from actual ODB records and selected Liberty.

No ODB or clock network mutation. The exact new full FF intent supplies only the
finite18 source aliases; all unchanged FFs must match their literal native names.
Clock edge/polarity comes from real Liberty functions and actual nets, not names.
"""
import argparse
import collections
import gzip
import hashlib
import importlib.util
import itertools
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
L=module('tt_actual_liberty',ROOT/'tools/dft/liberty.py')
M=module('tt_actual_memory',ROOT/'tools/autopilot/geom_memory.py')

def read(path):
    with (gzip.open(path,'rt') if str(path).endswith('.gz') else open(path)) as f:return json.load(f)

def primitive_clock(expression):
    expr=L.parse_function(expression)
    if expr[0]=='var':return expr[1],1
    if expr[0]=='not' and expr[1][0]=='var':return expr[1][1],-1
    raise ValueError('Unsupported multi-source clock expression: '+expression)

def path_function(cell,pin,physical_clocks):
    expression=cell['pins'].get(pin,{}).get('function')
    if not expression:raise ValueError('Missing actual Liberty clock-path function: '+cell['name']+'.'+pin)
    expr=L.parse_function(expression);variables=L.expr_vars(expr)
    if len(variables)==1:
        clock=next(iter(variables))
        if cell['pins'].get(clock,{}).get('direction')!='input':raise ValueError('Clock path depends on unmodeled internal state')
        values=[L.evaluate(expr,{clock:b}) for b in (0,1)]
        if values==[0,1]:return clock,1,'buffer',expression
        if values==[1,0]:return clock,-1,'inverter',expression
        raise ValueError('Clock-path function is not a buffer/inverter')
    candidates={p for p,q in cell['pins'].items() if q.get('clock') and q.get('direction')=='input' and p in variables}
    candidates|=physical_clocks&variables
    if len(candidates)!=1:raise ValueError('Clock gate has no unique typed actual clock input: '+cell['name'])
    clock=next(iter(candidates));others=sorted(variables-{clock});polarities=set()
    for bits in itertools.product((0,1),repeat=len(others)):
        env=dict(zip(others,bits));out=[L.evaluate(expr,dict(env,**{clock:b})) for b in (0,1)]
        if out==[0,1]:polarities.add(1)
        elif out==[1,0]:polarities.add(-1)
    if len(polarities)!=1:raise ValueError('Clock gate has ambiguous/no clock phase: '+cell['name'])
    return clock,next(iter(polarities)),'clock_gate',expression

def parse_dump(path):
    cells={};pins=collections.defaultdict(dict);ports={};drivers=collections.defaultdict(list);macro_xy={}
    for line in Path(path).read_text().splitlines():
        a=line.split('\t')
        if a[0]=='CELL':
            if a[1] in cells:raise ValueError('Duplicate actual native cell '+a[1])
            cells[a[1]]=dict(name=a[1],master=a[2],width_um=float(a[3]),height_um=float(a[4]),is_block=bool(int(a[5])),signal_pins=int(a[6]))
        elif a[0]=='PIN':
            if a[2] in pins[a[1]]:raise ValueError('Duplicate actual native ITerm')
            pins[a[1]][a[2]]=dict(direction=a[3],signal=a[4],net=a[5])
            if a[3]=='OUTPUT' and a[5]!='-':drivers[a[5]].append(('cell',a[1],a[2]))
        elif a[0]=='MPIN':macro_xy[a[1],a[2]]=[float(a[3]),float(a[4])]
        elif a[0]=='PORT':
            ports[a[1]]=dict(direction=a[2],signal=a[3],layer=a[4],xy_um=None if a[5]=='-' else [float(a[5]),float(a[6])],net=a[7])
            if a[2]=='INPUT' and a[7]!='-':drivers[a[7]].append(('port',a[1],None))
        elif a[0]!='META':raise ValueError('Unknown native record '+a[0])
    return cells,pins,ports,drivers,macro_xy

def macro_edges(paths,masters):
    edges=collections.defaultdict(lambda:collections.defaultdict(set))
    for path in paths:
        text=gzip.open(path,'rt').read() if str(path).endswith('.gz') else Path(path).read_text()
        for kind,_,body in M._groups(text):
            if kind!='library':continue
            for ck,name,cb in M._groups(body):
                if ck!='cell' or name not in masters:continue
                for pk,_,pb in M._groups(cb):
                    if pk not in ('pin','bus'):continue
                    for tk,_,tb in M._groups(pb):
                        if tk!='timing':continue
                        attrs=M._attrs(tb);clock=attrs.get('related_pin');tt=attrs.get('timing_type','')
                        if clock and tt in ('rising_edge','setup_rising','hold_rising'):edges[name][clock].add('posedge')
                        if clock and tt in ('falling_edge','setup_falling','hold_falling'):edges[name][clock].add('negedge')
    return edges

def source_alias_prefix(target):
    signal=target['source_identity'][0]
    # The enabled generate arm is part of the actual retained native hierarchy.
    # SF/S0 logical model identities intentionally retain their original names.
    if signal in ('u_bound.u_cland_origin.sf','u_bound.u_cland_origin.s0'):
        return signal.replace('.u_cland_origin.','.u_cland_origin.g_on.',1)
    if re.fullmatch(r'u_bound\.u_cland_origin\.g_on\.g_region\[[0-3]\]\.(?:s1|s2|pd)',signal):return signal
    if signal.endswith('.u_raw_copy.q'):return signal[:-2]+'/q'
    raise ValueError('Source alias is outside the finite regional mechanism')

def build(dump,lib_paths,sdc,intent,proposal,source_readset,netlist,ff_only=False):
    cells,pins,ports,drivers,macro_xy=parse_dump(dump);models=L.read_liberty(lib_paths);medges=macro_edges(lib_paths,{c['master'] for c in cells.values() if c['is_block']})
    actual_ff={n:c for n,c in cells.items() if not c['is_block'] and models.get(c['master'],{}).get('ff')}
    for n,c in cells.items():
        if c['signal_pins'] and c['master'] not in models:raise ValueError('Missing selected actual Liberty master: '+c['master'])
    declared=re.findall(r'create_clock -name clk -period ([0-9.]+) \[get_ports \{([^}]+)\}\]',Path(sdc).read_text())
    if len(declared)!=1 or float(declared[0][0])!=833 or set(declared[0][1].split())!=set(proposal['clock_ports']):
        raise ValueError('Actual SDC does not define the exact63port/833ps main cohort')
    if any(u!='ps' for u in re.findall(r'(?:set_units|set_cmd_units)[^\n]*?-time\s+(\S+)',Path(sdc).read_text())):raise ValueError('Unqualified actual SDC time-unit override')
    # The admitted native profile uses ps. Do not silently reinterpret a ns FF library.
    for path in lib_paths:
        text=gzip.open(path,'rt').read() if str(path).endswith('.gz') else Path(path).read_text()
        if re.search(r'\bff\s*\(',text) and not re.search(r'\btime_unit\s*:\s*"1ps"',text):raise ValueError('Actual FF Liberty time unit is not the admitted1ps profile')
    roots=set(proposal['clock_ports'])|{r['logical_root'] for r in proposal['retained_other_cohorts']};memo={}
    def trace(net,seen=()):
        if net in memo:return memo[net]
        if net in seen:raise ValueError('Actual clock path contains a loop')
        ds=drivers[net]
        if len(ds)!=1:raise ValueError('Actual clock net has missing/multiple drivers: '+net)
        kind,name,pin=ds[0]
        if kind=='port':
            if name not in roots:raise ValueError('Actual clock reaches an undeclared port: '+name)
            result=(name,[])
        else:
            c=cells[name];lib=models[c['master']]
            if lib.get('ff'):raise ValueError('Derived clock from a data FF is not admitted')
            physical={p for p,q in pins[name].items() if q['signal']=='CLOCK' and q['direction']=='INPUT'}
            cp,polarity,kind,expression=path_function(lib,pin,physical)
            pn=pins[name].get(cp)
            if not pn or pn['net']=='-':raise ValueError('Missing actual clock-path input ITerm')
            root,path=trace(pn['net'],seen+(net,))
            result=(root,path+[dict(instance=name,master=c['master'],input_pin=cp,output_pin=pin,kind=kind,polarity=polarity,clock_function=expression,contains_state=bool(lib.get('ff') or lib.get('latch')))])
        memo[net]=result;return result
    ff_records=[];model_to_native={};used_actual=set();normalized=collections.defaultdict(list)
    for name in actual_ff:normalized[name.replace('\\','')].append(name)
    for target in intent['targets']:
        name=target['model_name'];identity=target.get('source_identity')
        if identity:
            prefix=source_alias_prefix(target);matches=[]
            for normalized_name,raw_names in normalized.items():
                if re.fullmatch(re.escape(prefix)+r'(?:\[0\])?\$_[A-Z0-9_]+_',normalized_name):matches.extend(raw_names)
            if len(matches)!=1:raise ValueError('Missing/ambiguous actual regional source FF: '+name)
            actual=matches[0]
        else:actual=name
        if actual not in actual_ff:raise ValueError('Missing unchanged native FF: '+name)
        if actual in used_actual:raise ValueError('Two model states map to one actual native FF')
        used_actual.add(actual)
        model_to_native[name]=actual;c=actual_ff[actual]
        if c['master']!=target['master'] or abs(c['width_um']-target['width_um'])>1e-6 or abs(c['height_um']-target['height_um'])>1e-6:
            raise ValueError('Actual native FF footprint differs: '+name)
        lib=models[c['master']];cp,polarity=primitive_clock(lib['ff']['clocked_on'])
        pin=pins[actual].get(cp)
        if not pin or pin['net']=='-':raise ValueError('Missing actual FF clock ITerm: '+actual)
        root,path=trace(pin['net']);inversions=sum(r['polarity']==-1 for r in path);effective=(polarity==-1)^bool(inversions%2)
        row=dict(model_name=name,native_name=actual,master=c['master'],width_um=c['width_um'],height_um=c['height_um'])
        if identity:
            if root not in proposal['clock_ports'] or ('negedge' if effective else 'posedge')!=identity[1]:raise ValueError('Actual regional source clock root/edge differs: '+name)
            row.update(rtl_signal=identity[0],rtl_edge='negedge' if effective else 'posedge')
        ff_records.append(row)
    if set(model_to_native.values())!=set(actual_ff):raise ValueError('Extra/unpriced actual native FFs in full census')
    if len(model_to_native)!=38244 or len([q for q in ff_records if 'rtl_signal' in q])!=18:raise ValueError('Actual source is not the complete selected TT+13FF cohort')
    if ff_only:
        return dict(schema='opentallas.tt_actual_synth_ff_inventory.v1',source_event='tt_regional_origin_13ff',stage='mapped_synth_only',
                    status='PASS_NATIVE_FF_NAMES_FOOTPRINTS_ONLY',complete_ff_census=True,ff_cells=ff_records,
                    source_sha256=hashlib.sha256(Path(source_readset).read_bytes()).hexdigest(),netlist_sha256=hashlib.sha256(Path(netlist).read_bytes()).hexdigest(),
                    actual_dump_sha256=hashlib.sha256(Path(dump).read_bytes()).hexdigest(),
                    selected_liberties={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in lib_paths},
                    clock_bpin_and_macro_pose_join='NOT_RUN: no floorplan/placement authorized',row_site_join='HELD: pending complete row intent',
                    physical_release='HELD',placement_or_tree_applied=False,global_source_credit=False)
    ff_by_model={r['model_name']:r for r in ff_records}
    sink_records=[]
    for expected in proposal['assignments']+proposal['retained_other_cohorts']:
        name=expected['name']
        if '::' in name:
            actual,cp=name.split('::',1)
            if actual not in cells:raise ValueError('Missing actual macro clock instance')
            c=cells[actual];choices=medges[c['master']].get(cp,set())
            if not models[c['master']]['pins'].get(cp,{}).get('clock') or len(choices)!=1:raise ValueError('Actual macro clock has no unique typed Liberty edge')
            edge=next(iter(choices))
        else:
            actual=model_to_native[name];lib=models[cells[actual]['master']];cp,polarity=primitive_clock(lib['ff']['clocked_on']);edge='posedge' if polarity==1 else 'negedge'
        term=pins[actual].get(cp)
        if not term or term['net']=='-':raise ValueError('Missing actual clock ITerm')
        root,path=trace(term['net']);r=dict(model_name=name,native_iterm=actual+'/'+cp,root_port=root,cohort='clk' if root in proposal['clock_ports'] else root,edge=edge,path=path)
        target=ff_by_model.get(name)
        if target and 'rtl_signal' not in target:target=None
        if target:r.update(rtl_signal=target['rtl_signal'],rtl_edge=target['rtl_edge'])
        if '::' in name:
            if (actual,cp) not in macro_xy:raise ValueError('Missing actual typed macro clock ITerm geometry')
            r['xy_um']=macro_xy[actual,cp]
        sink_records.append(r)
    if len(model_to_native)!=38244 or len([q for q in ff_records if 'rtl_signal' in q])!=18:raise ValueError('Actual source is not the complete selected TT+13FF cohort')
    main_ports={}
    for name in proposal['clock_ports']:
        p=ports.get(name)
        if not p or p['direction']!='INPUT' or p['xy_um'] is None:raise ValueError('Missing placed actual clock BPin: '+name)
        main_ports[name]=dict(cohort='clk',period_ps=833,phase_ps=0,polarity=1,xy_um=p['xy_um'],layer=p['layer'])
    return dict(schema='opentallas.tt_actual_native_inventory.v1',source_event='tt_regional_origin_13ff',stage='mapped_preCTS',
                source_sha256=hashlib.sha256(Path(source_readset).read_bytes()).hexdigest(),netlist_sha256=hashlib.sha256(Path(netlist).read_bytes()).hexdigest(),
                actual_dump_sha256=hashlib.sha256(Path(dump).read_bytes()).hexdigest(),complete_ff_census=True,ff_cells=ff_records,ports=main_ports,sinks=sink_records,
                selected_liberties={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in lib_paths},placement_or_tree_applied=False)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('dump','sdc','intent','proposal','source-readset','netlist','out'):ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--lib',type=Path,action='append',required=True);ap.add_argument('--ff-only',action='store_true');a=ap.parse_args()
    result=build(a.dump,a.lib,a.sdc,read(a.intent),read(a.proposal),a.source_readset,a.netlist,a.ff_only)
    data=(json.dumps(result,separators=(',',':'))+'\n').encode()
    if str(a.out).endswith('.gz'):
        with gzip.GzipFile(filename=str(a.out),mode='wb',mtime=0) as f:f.write(data)
    else:a.out.write_bytes(data)
    print('TT_ACTUAL_NATIVE_INVENTORY',len(result['ff_cells']),'FFs',len(result.get('sinks',[])),'clock endpoints; metadata only')
