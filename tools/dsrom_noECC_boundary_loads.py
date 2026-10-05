#!/usr/bin/env python3
"""Actual retained element pin loads and output drivers; no invented parent IO."""
import gzip, hashlib, json, re
from pathlib import Path
from dsrom_noECC_liberty import block, cell_bodies
ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'results/uarch/dsrom_noECC_WAKE_cell_retention_20261002/terminal'
OUT=ROOT/'results/uarch/dsrom_noECC_capture_intrinsic_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    libs={corner:cell_bodies(corner) for corner in ('ss','ff')}
    result={}
    for case in ('q','bfcolumn'):
        path=MAP/case/'retained_mapped.json.gz'
        net=json.loads(gzip.decompress(path.read_bytes()))['modules']['ot_v41_rom_elem_w10']
        ins={b for p in net['ports'].values() if p['direction']=='input' for b in p['bits'] if isinstance(b,int)}
        outs={b for p in net['ports'].values() if p['direction']=='output' for b in p['bits'] if isinstance(b,int)}
        cache={}
        for corner in ('ss','ff'):
            for master in {c['type'] for c in net['cells'].values()} & libs[corner].keys():
                body=libs[corner][master];pins={}
                for m in re.finditer(r'\bpin\s*\(([^)]+)\)',body):
                    pb=block(body,m.start());cap=re.search(r'\bcapacitance\s*:\s*([\d.]+)',pb)
                    pins[m[1].strip(' "')]=float(cap[1]) if cap else 0
                cache[corner,master]=pins
        loads={corner:{b:[] for b in ins} for corner in ('ss','ff')};drivers={b:[] for b in outs}
        for name,c in net['cells'].items():
            if c['type']=='$scopeinfo':continue
            for pin,bits in c['connections'].items():
                direction=c['port_directions'][pin]
                for b in bits:
                    if direction=='input' and b in ins:
                        for corner in ('ss','ff'):
                            if c['type']=='ot_rom_4096x274_m8':
                                if pin!='clk':raise ValueError('Unmodeled macro boundary input')
                                cap=8.6838 if corner=='ss' else 10.3732
                            else:
                                if (corner,c['type']) not in cache or pin not in cache[corner,c['type']]:raise ValueError('Missing actual input pin model')
                                cap=cache[corner,c['type']][pin]
                            loads[corner][b].append(dict(cell=name,master=c['type'],pin=pin,cap_fF=cap,source=c.get('attributes',{}).get('src','')))
                    if direction=='output' and b in outs:
                        drivers[b].append(dict(cell=name,master=c['type'],pin=pin,source=c.get('attributes',{}).get('src','')))
        ports={}
        for name,p in net['ports'].items():
            x=dict(direction=p['direction'],width=len(p['bits']),bits=p['bits'])
            if p['direction']=='input':
                x['actual_pin_loads']={corner:[dict(bit=b,load_fF=sum(v['cap_fF'] for v in loads[corner].get(b,[])),sink_count=len(loads[corner].get(b,[])),sinks=loads[corner].get(b,[])) for b in p['bits']] for corner in ('ss','ff')}
            else:x['actual_element_drivers']=[dict(bit=b,drivers=drivers.get(b,[])) for b in p['bits']]
            ports[name]=x
        result[case]=dict(mapped_json_sha256=sha(path),ports=ports)
    sources=OUT/'inputs/parent_endpoint_sources';receipts=json.loads((sources/'receipts.json').read_text())
    for row in receipts:
        if sha(ROOT/row['copy'])!=row['sha256']:raise ValueError('Parent endpoint source changed')
    pair=(sources/'ot_v41_pair_w17w10_rne_wake_prepare.sv').read_text()
    field=(sources/'ot_v41_field_w17w10.sv').read_text()
    for flag in ('FIX_SECOND_ROW_INDEX','WAKE_REG','GRADUAL_RNE'):
        if not re.search(r'parameter integer '+flag+r'\s*=\s*0',pair):raise ValueError('Parent prepared opt-in contract changed')
        if flag in field:raise ValueError('Current field caller changed; re-audit actual passthrough')
    return dict(schema='opentallas.dsrom.actual-boundary-loads.v1',candidate='DS4096-TP4-S58-PAR2-NP2048',cases=result,
        parent_endpoint_source_receipts=receipts,
        exact_caller_gap='Pinned current field instantiates pair without FIX_SECOND_ROW_INDEX/WAKE_REG/GRADUAL_RNE passthrough; prepared pair defaults all three to0. Standalone measured element has all three1. Bind one additive opt-in parent caller before claiming the full mapped element is actual parent context. No source edit made here.',
        scope='Exact retained source pin loads, not external driver timing. No wire capacitance or parent receiver substituted.',
        parent_endpoint_join=dict(cfg=['pair.c_v','pair.c_a[4:0]','pair.c_d[47:0]'],go='pair.go && pair.act',
            stream='field passes packed xs/xb inputs directly to pair/u_e; parent broadcast/register provider must be bound, not inferred from a behavioral runtime',
            return_data='element pval/prow/ppos/pseg/pnseg -> first retn.a/b data/tag ports',
            return_valid='pv/perr -> first retn a_v/b_v/a_e/b_e; busy/fault -> field OR trees',
            reset='actual source async reset cones and eight WAKE set-to-one cells; parent reset launch/deassertion and buffer routes required'),
        remaining_required_numeric_parent_endpoints=['source-matched mapped pair config loader registers and go-act gate','actual packed-stream broadcast driver/register map','actual first return-node input pins and busy/fault OR receivers','root clock driver pin and reset driver/deassertion contract'],
        installed_CTS_not_prebuild_requirement=True,physical_admission=False)
if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'boundary_loads.json').write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
