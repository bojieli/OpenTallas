import gzip, hashlib, json, sys
from pathlib import Path
here=Path(__file__).resolve().parent
root=next(p for p in [here,*here.parents] if (p/'tools/die_plan/schema.py').is_file())
sys.path.insert(0, str(root/'tools/die_plan'))
import schema as S
import gen_phys as G
import infra_sites as I

src=Path(sys.argv[1]);raw=S.load(src);P=S.Plan(raw,src)
out=dict(source=str(src),sha256=hashlib.sha256(src.read_bytes()).hexdigest(),types={})
for tn,sn in [('vsN4','L9x2'),('vsN2','L153x2')]:
    t=P.types[tn]
    parts=[n for n,p in P.parts.items() if p['type']==tn]
    assert len(parts)==1, (tn,'replica pin maps need separate validation',parts)
    pins=[list(p) for p in G.type_pins(P,tn) if p[0] in (sn+'_i',sn+'_o')]
    out['types'][tn]=dict(target=sn,outline_um=t['outline_um'],ft_slots=t['ft_slots'],
        cores=[list(c) for c in I.type_cores(t)],pins=pins,parts=parts,
        island=[678.24,652.32,704.16,678.24],
        unmodeled_internal_stations=len(t.get('internal_stations',[])))
with gzip.open(Path(__file__).parent/'export.json.gz','wt',compresslevel=3) as f:json.dump(out,f)
print({t:(len(v['pins']),len(v['ft_slots'])) for t,v in out['types'].items()})
