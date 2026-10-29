#!/usr/bin/env python3
"""Wire the emitted START provider to exact local raw-wavefront export ports.

The port map is physical source inventory, not a reset phase sign-off. Each
source is an existing registered raw relay. The selected settle guard is a
priced prototype hypothesis and must be checked on built clock/reset arrivals.
"""
import argparse,copy,json,re
from pathlib import Path


def patch(stages,sv,exports,settle):
    if exports['summary']['over_hop']:raise ValueError('local raw reset has over-reach sources')
    if settle<exports['summary']['max_relative_raw_release']+4:raise ValueError('settle does not cover raw release span plus 3-sync+1 guard')
    out=copy.deepcopy(stages);rows={r['stage']:r for r in exports['stages']};ports={}
    if set(rows)!={s['id'] for s in out['stages']}:raise ValueError('reset stages do not cover exact provider')
    for s in out['stages']:
        r=rows[s['id']];c=r['source'];name='wrst_'+c['part']+'__'+c['port'];name=re.sub(r'\W','_',name)
        ports[name]=dict(c)
        pattern=r'(u_st_'+re.escape(s['id'])+r'\s*\(\.clk\([^)]*\), \.rst_raw_n\()rst_raw_n(\))'
        # Canonical writer uses origin instance name 'u_<id>'. Match the exact
        # stage clock port as the independent attribution key.
        pattern=r'(\.clk\('+re.escape(s['clock_port'])+r'\), \.rst_raw_n\()rst_raw_n(\))'
        sv,n=re.subn(pattern,lambda m:m[1]+name+m[2],sv)
        if n!=1:raise ValueError(f"{s['id']}: expected one raw reset binding, found {n}")
        s['reset_port']=name;s['reset_source']=dict(c);s['reset_hop_um']=r['hop_um']
        if s['root']:
            sv,n=re.subn(r'ot_dp_landing_root #\(\.SETTLE\(\d+\)\)',f'ot_dp_landing_root #(.SETTLE({settle}))',sv)
            if n!=1:raise ValueError('expected one root settle parameter')
            s.update(settle=settle,flops=settle.bit_length()+1)
    sv,n=re.subn(r'    input  wire rst_raw_n,\n',''.join(f'    input  wire {p},\n' for p in sorted(ports)),sv)
    if n!=1 or re.search(r'\.rst_raw_n\(rst_raw_n\)',sv):raise ValueError('global raw reset binding remains')
    out.update(reset_form='local_wavefront',root_settle=settle,reset_ports=ports,
        reset_qualification='PROTOTYPE: exact source relays/reach, actual phase and timing NOT RUN',
        root_settle_guard=dict(raw_relative_span=exports['summary']['max_relative_raw_release'],guard_cycles=4,
            prototype_minimum=exports['summary']['max_relative_raw_release']+4,
            added_boot_cycles=settle-stages['root_settle'],added_steady_cycles=0))
    out['counts']['flops']=sum(s['flops'] for s in out['stages'])
    return out,sv


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('stages');a.add_argument('exports');a.add_argument('--settle',type=int,required=True);a.add_argument('--out',required=True);a=a.parse_args();src=Path(a.stages);o=Path(a.out);o.mkdir(parents=True,exist_ok=False)
    doc,sv=patch(json.load(open(src/'start_stages.json')),(src/'start_stages.sv').read_text(),json.load(open(a.exports)),a.settle)
    (o/'start_stages.json').write_text(json.dumps(doc,indent=1)+'\n');(o/'start_stages.sv').write_text(sv)
    for name in ['ctree.v','ctree.tcl']:(o/name).write_bytes((src/name).read_bytes())
    print(json.dumps(dict(counts=doc['counts'],reset_ports=len(doc['reset_ports']),guard=doc['root_settle_guard'])))
if __name__=='__main__':main()
