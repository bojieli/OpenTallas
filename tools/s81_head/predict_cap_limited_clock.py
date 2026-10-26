#!/usr/bin/env python3
"""Prepare the next HEAD clock structure from Liberty caps and declared RC.

No CTS/GRT arrivals are inputs. This is a proposal, not a build authorization.
The common core generator must implement the recorded fixed-depth, bounded-load
tree (not a post-CTS balance operation) before this can become a trial kit.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re

ap=argparse.ArgumentParser()
ap.add_argument('--clock-tool',required=True)
ap.add_argument('--libdir',required=True)
ap.add_argument('--out',required=True)
a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
sp=importlib.util.spec_from_file_location('canonical_clock128',a.clock_tool)
ck=importlib.util.module_from_spec(sp);sp.loader.exec_module(ck)

def block(text,start):
    left=text.index('{',start);depth=1;k=left+1
    while depth:
        depth+=(text[k]=='{')-(text[k]=='}');k+=1
    return text[left+1:k-1]

def clock_caps(corner):
    files=sorted(Path(a.libdir).glob(f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_*'))
    # Match the canonical library vintage, never mix duplicate definitions.
    f=next((p for p in files if ('220123' if corner=='TT' else '211120') in p.name),files[0])
    text=gzip.open(f,'rt').read() if f.suffix=='.gz' else f.read_text()
    caps={}
    for m in re.finditer(r'cell\s*\((DFF[^)]+)\)',text):
        cb=block(text,m.end())
        pin=re.search(r'pin\s*\(CLK\)',cb)
        if not pin:continue
        pb=block(cb,pin.end())
        values=[float(x) for x in re.findall(r'(?:rise_|fall_)?capacitance\s*:\s*([\d.eE+-]+)',pb)]
        if values:caps[m.group(1)]=max(values)
    if not caps:raise ValueError(f'no actual DFF clock capacitances found in {f}')
    return caps,{'file':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}

# Existing core-outline and island geometry are fixed; new clock routes use M4
# horizontal/M5 vertical, 4W/4S. The C factor is a declared conservative planning
# assumption; R scales with physical width, never a measured timing correction.
rc={'M4':{'r_kohm_um':.0180365,'c_ff_um':.1275},'M5':{'r_kohm_um':.0189935,'c_ff_um':.098}}
ndr={'width_scale':4,'cap_factor_assumption':1.6,'base_width_um':.032,'spacing_um':.128}
quad_counts={'WS':8200,'WN':2953,'ES':8613,'EN':8955}
libs={c:ck.lib_cells(c,a.libdir) for c in ('TT','FF')}
caps={};cap_evidence={}
for c in libs:caps[c],cap_evidence[c]=clock_caps(c)
cases=[]
for topology,limit in ((top,n) for top in ('two_level_sides','direct_four_quadrants') for n in (16,24,32,40,48,64)):
    leaves=max(math.ceil(n/limit) for n in quad_counts.values())
    levels=math.ceil(math.log(leaves,4))
    result={'topology':topology,'max_sinks_per_leaf':limit,'max_leaves':leaves,'fixed_local_levels':levels,'corners':{}}
    for c in libs:
        lb=libs[c]['BUFx24_ASAP7_75t_R'];ffcap=max(caps[c].values());slew=20.;delay=0.;stages=[]
        # root stub; symmetric 82.08um W/E trunk; symmetric 82.08um N/S
        # trunk; quadrant root; fixed 4-ary local levels; final bounded leaf.
        specs=[('entry',2.,2*lb['cap']),('centre',164.16,2*lb['cap']),
               ('side',164.16,2*lb['cap']),('quadrant',4.32,lb['cap'])]
        if topology=='direct_four_quadrants':
            specs=[('entry',2.,2*lb['cap']),('four_way_fork',492.48,4*lb['cap']),('quadrant',4.32,lb['cap'])]
        specs += [(f'local{k}',max(8.,40./(2**k)),4*lb['cap']) for k in range(levels)]
        specs += [('leaf',40.,limit*ffcap)]
        for name,length,load in specs:
            ru=max(x['r_kohm_um'] for x in rc.values())/ndr['width_scale']
            cu=max(x['c_ff_um'] for x in rc.values())*ndr['cap_factor_assumption']
            if name=='four_way_fork':
                # Exact H-fork: two 82.08um shared W/E legs, each splitting
                # into 82.08um N/S legs. Driver sees all 6 wires/4 loads;
                # Elmore along ONE path sees only its downstream subtree.
                # CT_w/e buffers are absent in this proposed architecture.
                leg=82.08
                d,slew=ck.stage(lb,slew,0,cu*length,load)
                el=ru*leg*(cu*leg/2+2*lb['cap']+2*cu*leg)+ru*leg*(cu*leg/2+lb['cap'])
                d+=el;slew=math.sqrt(slew*slew+(2.2*el)**2)
            else:
                d,slew=ck.stage(lb,slew,ru*length,cu*length,load)
            delay+=d;stages.append({'name':name,'wire_um':length,'load_ff':load,'delay_ps':d,'slew_ps':slew})
        target=250. if c=='TT' else 202.5
        result['corners'][c]={'insertion_ps':delay,'target_ps':target,'within_20':abs(delay-target)<=20,
                               'clock_pin_cap_upper_ff':ffcap,'stages':stages}
    result['model_pass']=all(x['within_20'] for x in result['corners'].values());cases.append(result)
eligible=[r for r in cases if r['model_pass']]
proposal=min(eligible or cases,key=lambda r:max(abs(x['insertion_ps']-x['target_ps']) for x in r['corners'].values()))
report={'status':'PROPOSAL_ONLY; no launch before fixed-depth generator + slice + review',
        'target_ps':{'TT':250.,'FF':202.5},'rc':rc,'ndr':ndr,'actual_liberty_clock_caps':caps,
        'liberty_evidence':cap_evidence,'quad_counts':quad_counts,'candidates':cases,'selected':proposal,
        'prediction_verdict':'PASS_MODEL' if eligible else 'FAIL_MODEL_NO_BUILD',
        'generator_requirements':['Consume explicit per-node sink sets from the master-plan slice.',
          'Same fixed fanout/depth in all quadrants; no delay-buffer balance or clock ECO.',
          'Leaf total capacitance bounded by actual per-master CK caps plus planned wire cap.',
          'PG-connect fixed cells before dont_touch; dedicated FT arcs isolated from core IO.']}
(out/'plan.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'planned_ndr.tcl').write_text('''# Plan-defined, BEFORE any build. Not a post-CTS timing ECO.
create_ndr -name head_core_clock_4w -width {M4 0.128 M5 0.128} -spacing {M4 0.128 M5 0.128}
set b [ord::get_db_block]
set nd [$b findNonDefaultRule head_core_clock_4w]
foreach n [$b getNets] { if {[$n getSigType] eq "CLOCK"} { $n setNonDefaultRule $nd } }
set_routing_layers -signal M2-M5 -clock M4-M5
# Per-type generator must materialize the model's fixed-depth sink sets first.
''')
print(json.dumps({'verdict':report['prediction_verdict'],'selected':{k:v for k,v in proposal.items() if k!='corners'},
                  'TT':proposal['corners']['TT']['insertion_ps'],'FF':proposal['corners']['FF']['insertion_ps']}))
