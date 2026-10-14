#!/usr/bin/env python3
"""Real-child HBM SM candidate preparation. Does not revise a die contract.

Prepare source-pinned tile boundary elaborations with the twelve published hard
children blackboxed. Parent logic is retained, counted and must be hardened;
rectangle compaction cannot claim that this logic disappeared.
"""
import argparse
import hashlib
import json
import re
import subprocess
import fnmatch
import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = 'results/arch/hbm_native_1013/sm_compaction'
LEAVES = {'ot_hbm_accel_smh_' + n for n in ('pt_w', 'pt_e', 'xs', 'bdc', 'tcl', 'tct')}


def header(body):
    text = re.sub(r'//[^\n]*|/\*.*?\*/', '', body, flags=re.S)
    level = 0
    for i, char in enumerate(text):
        level += (char == '(') - (char == ')')
        if char == ';' and level == 0:
            return text[:i + 1]
    raise ValueError('missing module header')


def prepare(a):
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    source = subprocess.check_output(['git', 'show', a.source + ':rtl/hbm_accel/sm/ot_hbm_accel_smh.sv'], cwd=ROOT, text=True)
    # Retain preprocessor directives outside modules and every non-leaf body.
    def replace(m):
        name = m.group(1)
        return '(* blackbox *) ' + header(m.group(0)) + '\nendmodule' if name in LEAVES else m.group(0)
    sv = re.sub(r'\bmodule\s+(\w+)\b.*?\bendmodule\b', replace, source, flags=re.S)
    for path in ('rtl/lib/ot_hdly.sv', 'rtl/lib/ot_rst_relay.sv', 'rtl/hdc/ot_hdc_cg.sv', 'rtl/hbm_accel/cg/ot_cg_tile.sv'):
        sv += '\n' + subprocess.check_output(['git', 'show', a.source + ':' + path], cwd=ROOT, text=True)
    sv += '\n(* blackbox *) module ICGx1_ASAP7_75t_R(input CLK, ENA, SE, output GCLK); endmodule\n'
    (out / 'boundary.sv').write_text(sv)
    defs = ['SYNTHESIS', 'OT_SMH_CG_ENREG', 'OT_SMH_XLK', 'OT_FP_DATA_NORST', 'OT_SMH_DRST0', 'OT_SMH_RSTRELAY', 'OT_SMH_RSTPIN', 'OT_SMH_HIER', 'OT_SMH_PTW_OHDLY', 'OT_SMH_PRODUCTION_SHAPE']
    for v in ('eg', 'wg'):
        (out / (v + '.ys')).write_text('read_verilog -sv ' + ' '.join('-D' + d for d in defs) + ' boundary.sv\nhierarchy -check -top ot_hbm_accel_smh_tile_' + v + '\nproc\nsetattr -mod -unset keep_hierarchy\nflatten\nopt_clean\ncheck\nwrite_json ' + v + '.json\n')
    (out / 'sources.json').write_text(json.dumps({'source_commit': a.source, 'sm_source_sha256': hashlib.sha256(source.encode()).hexdigest(), 'boundary_sha256': hashlib.sha256(sv.encode()).hexdigest(), 'defines': defs, 'hard_masters': sorted(LEAVES), 'status': 'BOUNDARY_ELABORATION_ONLY'}, indent=2) + '\n')


def collect(a):
    out = Path(a.work)
    rows = {}
    for v in ('eg', 'wg'):
        m = json.loads((out / (v + '.json')).read_text())['modules']['ot_hbm_accel_smh_tile_' + v]
        hard = {n: c for n, c in m['cells'].items() if c['type'] in LEAVES}
        own = {n: c for n, c in m['cells'].items() if c['type'] not in LEAVES}
        seq = {n: c for n, c in own.items() if any(s in c['type'].lower() for s in ('dff', 'latch'))}
        sink_bits = sum(len(c['connections'].get('Q', [])) for c in seq.values())
        kinds = {}
        for c in own.values():
            kinds[c['type']] = kinds.get(c['type'], 0) + 1
        assert len(hard) == 12, (v, len(hard))
        rows[v] = {'hard_children': [{'instance': n, 'master': c['type']} for n, c in hard.items()], 'parent_cells': len(own), 'parent_cell_types': kinds, 'parent_sequential_Q_bits': sink_bits, 'parent_logic_requires_real_leaf_views': True, 'status': 'NOT_PHYSICAL_FIT_OR_CLOCK_PROOF'}
    (out / 'boundary_census.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps(rows))


def grt_projection(a):
    """An explicitly incomplete routing probe of only retained hard-hard nets."""
    out=ROOT/a.out
    geom=json.load(open(out/'real_pin_geometry_candidate.json'))
    for variant in ('eg','wg'):
        m=json.load(open(out/(variant+'.json')))['modules']['ot_hbm_accel_smh_tile_'+variant]
        nodes=collections.defaultdict(list); children=[]
        for name,cell in m['cells'].items():
            row=next((r for r in geom['variants'][variant]['children'] if fnmatch.fnmatchcase(name,r['instance'])),None)
            if row is None:continue
            lef=row['view']+'/'+cell['type']+'.lef'
            children.append({'instance':name,'logical_module':cell['type'],'view_lef':lef,'view_lib':{c:row['view']+'/'+cell['type']+'_'+c+'.lib' for c in ('tt','ff','ss')},'xy_um':row['at_um'],'orientation':row['orient'],'component_namespace':variant,'component_child':name})
            for port,bits in cell['connections'].items():
                for i,bit in enumerate(bits):
                    if isinstance(bit,int):nodes[bit].append({'instance':name,'port':port,'lsb':i,'width':1,'direction':cell['port_directions'][port]})
        connections=[{'net':'n'+str(bit),'endpoints':eps,'kind':'clock' if any(e['port']=='clk'for e in eps) else 'reset' if any(e['port']in('rst_a','rst_n')for e in eps) else 'signal'} for bit,eps in nodes.items() if len(eps)>=2]
        component={'children':children,'connections':connections,'status':'DIAGNOSTIC_HARD_TO_HARD_PROJECTION_NOT_FULL_TILE','omitted_parent_sequential_Q_bits':995,'omitted_parent_and_boundary_nets':True,'full_tile_route_closed':False}
        path=out/(variant+'_hard_projection.json');path.write_text(json.dumps(component,indent=2)+'\n')
        candidate_children=json.loads(json.dumps(children))
        for index,child in enumerate(candidate_children):child['instance']='hard_'+variant+'_'+str(index)
        candidate={'variant':'DIAGNOSTIC_SMH_REAL_HARD_NETS_ONLY','children':candidate_children,'functional_namespace_maps':[{'namespace':variant,'component_path':str(path.relative_to(ROOT)),'component_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}]}
        cp=out/(variant+'_grt_candidate.json');cp.write_text(json.dumps(candidate,indent=2)+'\n')
        sys.path.insert(0,str(ROOT/'tools'))
        import hbm_native_component_grt_1013 as G
        G.CAND=str(cp.relative_to(ROOT))
        from argparse import Namespace
        G.cmd_gen(Namespace(namespace=variant,case='smh_compact_'+variant+'_hard_only',work=str(out/('grt_'+variant)),margin=8.64,iters=50,allow_missing=False))
        manifest=out/('grt_'+variant)/'manifest.json'
        data=json.load(open(manifest));data['scope']='DIAGNOSTIC ONLY: retained hard-hard nets; 995 parent state bits and boundary routes omitted, no full tile, die or throughput closure claim.';manifest.write_text(json.dumps(data,indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=('prepare', 'collect', 'grt_projection'))
    p.add_argument('--source', default='f6ee9d6d1')
    p.add_argument('--out', default=OUT)
    p.add_argument('--work', default='.')
    a = p.parse_args()
    {'prepare':prepare,'collect':collect,'grt_projection':grt_projection}[a.command](a)
