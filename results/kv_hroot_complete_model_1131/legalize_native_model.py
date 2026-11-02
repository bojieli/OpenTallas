from pathlib import Path
import json,math,re
R=Path(__file__).resolve().parent
# Reuse the exact widest-drive/native-row footprint scanner; no CAD or ODB edit.
exec(compile((R/'ring_footprint_model.py').read_text().split('out=[]')[0],str(R/'ring_footprint_model.py'),'exec'))
D=G.Design(R/'model_ring.tsv')
selected={i for i,c in D.cells.items() if c[0]=='S' and any(s in c[-1] for s in ('u_bin_','u_bout_','u_ist_','u_u_efault.','u_u_fch.'))}
selected_names={D.cells[i][-1] for i in selected}
for row in occ:occ[row]=[t for t in occ[row] if t[2] not in selected_names]
ring=json.loads((R/'ring_footprint_proposal.json').read_text())
for m in ring['moves']:
 i=names[m['name']];c=D.cells[i];reserve(c[2],c[3],m['reserved_width_um'],m['height_um'],m['name'])
native=json.loads((R/'proposal_after_rings.json').read_text())
assert native['status'].startswith('Optimization terminated successfully')
targets={m['name']:m['new'] for m in native['moves']}
out=[]
for i in sorted(selected,key=lambda i:sum(abs(a-b) for a,b in zip(targets.get(D.cells[i][-1],G.ctr(D.cells[i])),G.ctr(D.cells[i])))):
 out.append(place(i,[4.32,4.32,1896.48,833.76],targets.get(D.cells[i][-1],G.ctr(D.cells[i]))))
bad=[];rr=G.r2r_metrics(D,capture_pairs=bad)
clks=set(json.loads((R/'source_clock_pin_classification.json').read_text())['actual_clock_pins'])
pin=G.pin_reg_metrics(D,re.compile(r'^strap_'),clock_pins=clks,land=lr['caps'])
data_bad=[p for p in bad if 'u_rrl_' not in p['launch']]
print('native sites',len(out),'max legalized displacement',max(m['target_distance_um'] for m in out))
print('FULLPIN',pin);print('RAW_R2R',rr);print('DATA_BAD',len(data_bad),data_bad[:6])
result=dict(scope='PREP native-row+actual widest-drive footprints; no ODB application.11 raw reset failures retain their verdict until exact parent boot/START join and real graph rewire.',native_sites=out,pin_metrics=pin,raw_r2r=rr,raw_bad_pairs=bad,data_bad_pairs=data_bad)
(R/'complete_footprint_proposal.json').write_text(json.dumps(result,indent=2))
with (R/'complete_model.tsv').open('w') as f:
 for line in (R/'model_ring.tsv').open():
  if line.startswith('C\t'):
   a=line.rstrip().split('\t');c=D.cells[int(a[1])];a[4:8]=[f'{v:.6f}' for v in c[2:6]];line='\t'.join(a)+'\n'
  f.write(line)
