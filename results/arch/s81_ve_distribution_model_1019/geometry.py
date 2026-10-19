"""Geometric point embedding, not legal-cell placement or routed-wire evidence."""
import gzip,json,math,collections
from pathlib import Path
P=Path(__file__).resolve().parent
r=json.loads(gzip.decompress((P.parent/'s81_ve_current_model_1019/endpoint_roots.json.gz').read_bytes()))
f=json.loads((P/'fixed_point.json').read_text());n={x['instance']:x['copies'] for x in f['copies']}
def inst(pin):return pin.rsplit('/',1)[0]
inv={inst(x['driver']['pin']):x for x in r if (x['driver']['master'] or '').startswith('CKINV')}
for x in r:
    end={}
    for s in x['sinks']:
        for t in inv[inst(s['pin'])]['sinks'] if inst(s['pin']) in inv else [s]:end[t['pin']]=t
    x['sinks']=list(end.values())
r=[x for x in r if inst(x['driver']['pin']) not in inv and x['driver']['pin']!='PORT/clk' and x['driver']['signal']!='CLOCK']
reset=json.loads((P.parent/'s81_ve_current_model_1019/native_corrected.json').read_text())['over405'][0]['driver']['pin']
resetinst=inst(reset)
def xy(t):return [172.8,129.6] if inst(t['pin'])==resetinst else [t['xy'][0],t['xy'][1]*.75]
maxedge=0.; wire=0.;extra=0;terms=0;bad=[]
for x in r:
    a=xy(x['driver']);cnt=0
    for t in x['sinks']:
        b=xy(t);d=abs(a[0]-b[0])+abs(a[1]-b[1]);copies=1 if t['role']=='output' else n.get(inst(t['pin']),1)
        maxedge=max(maxedge,d);wire+=d*copies;terms+=copies;cnt+=copies;extra+=copies-1
        if d>405:bad.append([x['driver']['pin'],t['pin'],d])
    assert math.ceil(cnt/n.get(inst(x['driver']['pin']),1))<=32
out=dict(outline_um=[345.6,259.2],area_um2=345.6*259.2,aspect=4/3,one_full_width_standard_cell_band=True,macros=0,lattice_pitch_um=43.2,embedding='Existing endpoint x unchanged; y multiplied by .75. Every copy co-located with original; sole over405 reset cell and all of its input endpoints moved to center. Zero-area points.',moved_reset_root=reset,endpoint_pairs_over405=bad,max_direct_manhattan_um=maxedge,expanded_sink_terms=terms,additional_nonclock_input_pin_terms=extra,sum_expanded_pin_manhattan_um=wire,partition_rule='For each driver output, all destination-copy PIN loads partition into <=32-load sets across its n copies; abstract connectivity only.',scope='Constructive point-connectivity witness. Not legal placement: finite cell dimensions, no overlap, kept copy ownership, routed detours, buffers/vias, PG and clock access not checked. No latency or frequency claim follows.')
(P/'geometry.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
