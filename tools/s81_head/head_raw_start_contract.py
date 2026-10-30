"""Declare HEAD raw START-reset uses/opens from actual emitted source wiring.

Only existing registered raw wavefront export metadata is accepted. No RTL, pin,
geometry, latency or input binding is changed. Run on the final source assembly.
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'die_plan'))
import schema as S
import landing_contract as LC
import gen_rtl as G


def enrich(plan,side,stages,top,plan_path=None):
    plan=copy.deepcopy(plan);side=copy.deepcopy(side)
    P=S.Plan(plan,Path(plan_path) if plan_path else None)
    pinmap={tn:{p['name']:p for p in t.get('clock',{}).get('landing_contract',{}).get('pins',[])} for tn,t in P.types.items()}
    raw_outputs={};cache={}
    for tn,t in P.types.items():
        for row in t.get('reset_start_raw_exports',[]):
            if row.get('existing_port'):continue
            good,why=LC._typed_raw_reset_output(P,tn,row['port'],pinmap,cache)
            if not good:raise ValueError(f'{tn}.{row["port"]}: {why}')
            raw_outputs.setdefault(tn,set()).add(row['port'])
    def connections(instance):
        found=list(re.finditer(r'(?m)^\s*\w+(?: #\([^\n]*\))? '+re.escape(instance)+r' \(\n(.*?)\n\s*\);',top,re.S))
        if len(found)!=1:raise ValueError('expected one actual top instance '+instance)
        pairs=re.findall(r'\.([A-Za-z_]\w*)\(([^()]*)\)',found[0][1])
        if len({p for p,_ in pairs})!=len(pairs):raise ValueError('duplicate actual top port '+instance)
        return dict(pairs)
    provider=connections('u_die_start_stages');part_connections={};new={};existing=0
    raw_wires=set()
    for pn,part in P.parts.items():
        rows=P.types[part['type']].get('reset_start_raw_exports',[])
        if not rows:continue
        part_connections[pn]=connections(G.sv_id(pn))
        for row in rows:
            wire=part_connections[pn].get(row.get('existing_port',row['port']))
            if row.get('existing_port') and not wire:continue
            if not wire or not re.fullmatch(r'[A-Za-z_]\w*',wire):
                raise ValueError('raw output lacks an actual named top wire '+pn+'.'+row['port'])
            raw_wires.add(wire)
    actual_reset_ports={port for port,wire in provider.items() if wire in raw_wires}
    if actual_reset_ports!=set(stages.get('reset_ports',{})):
        raise ValueError('stage reset-port inventory differs from actual top provider wiring')
    for stage in stages.get('stages',[]):
        port=stage.get('reset_port');source=stage.get('reset_source',{})
        expected=stages.get('reset_ports',{}).get(port,{})
        if not expected or any(source.get(k)!=expected.get(k) for k in ('part','type','port','instance','net')):
            raise ValueError('stage reset source differs from provider port inventory')
    for port,source in stages.get('reset_ports',{}).items():
        pn=source['part'];tn=P.parts[pn]['type'];name=source['port']
        rows=[r for r in P.types[tn].get('reset_start_raw_exports',[]) if r['port']==name]
        if len(rows)!=1:raise ValueError('provider names undeclared raw export '+pn+'.'+name)
        row=rows[0]
        if (source.get('type'),source.get('instance'),source.get('net'))!=(tn,row['instance'],row['net']):
            raise ValueError('provider source differs from declared raw export '+pn+'.'+name)
        if pn not in part_connections:part_connections[pn]=connections(G.sv_id(pn))
        actual_port=row.get('existing_port',name);wire=part_connections[pn].get(actual_port)
        if not wire or not re.fullmatch(r'[A-Za-z_]\w*',wire) or provider.get(port)!=wire:
            raise ValueError('provider reset is not wired to its actual raw output '+pn+'.'+actual_port)
        if row.get('existing_port'):existing+=1;continue
        canonical='wr_'+re.sub(r'[^A-Za-z0-9_]','_',pn)+'__'+name
        if wire!=canonical:raise ValueError('raw export wire differs from complete_top canonical wire')
        new[(pn,name,wire)]=dict(src_part=pn,src_port=name,net=wire)
    sp=side['count_aligned']['start_pins'];old=sp.get('reset_inputs',[])
    old=[e for e in old if e.get('src_port',LC.RAW_RESET_PIN_OUT) not in raw_outputs.get(P.parts[e['src_part']]['type'],())]
    sp['reset_inputs']=old+[new[k] for k in sorted(new)]
    net=plan['clock']['landing_network'];edges={(e[q]['part'],e[q]['bus']) for e in net['edges'] for q in ('src','dst')}
    declared=LC.start_declaration(sp,{pn:p['type'] for pn,p in P.parts.items()},
        {tn:{name:p['dir'] for name,p in pins.items()} for tn,pins in pinmap.items()},edges,raw_outputs)
    net['start_tree'].update(uses=declared['uses'],open=declared['open'])
    opened=[o for o in declared['open'] if o['pin'] in raw_outputs.get(P.parts[o['part']]['type'],())]
    return plan,side,dict(used_raw_outputs=len(new),open_raw_outputs=len(opened),existing_reset_provider_ports=existing,
                          reset_provider_ports=len(stages.get('reset_ports',{})),added_cycles=0)


def main():
    a=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','sidecar','stages','top'):a.add_argument(name)
    a.add_argument('--out',required=True);a=a.parse_args()
    plan,side,report=enrich(json.load(open(a.plan)),json.load(open(a.sidecar)),json.load(open(a.stages)),Path(a.top).read_text(),a.plan)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    (out/'source_plan.json').write_text(json.dumps(plan,indent=1)+'\n')
    (out/'source_sidecar.json').write_text(json.dumps(side,indent=1)+'\n')
    (out/'report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
