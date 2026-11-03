from pathlib import Path
import json,shutil
P=Path(__file__).parent;out=P/'clockaware_v2';out.mkdir(exist_ok=True);(out/'.keep').touch()
for name in ['geom_rules.py','homes_for_final_audit.json','origin_instance_regions.json','origin_regional_candidate.json','finish_local_candidate.py']:
 shutil.copy2(P/name,out/name)
# Finite revised candidate: gm0 +one existing8.64PG period; FIFO3/gm1 keep their original homes.
deltas=[('u_bound.u_core.u_gi.u_cal.g_fifo\\[3\\].u_fifo',-17.28),('u_bound.u_core.u_gi.u_cal.g_m\\[0\\].u_pm',-8.64),('u_bound.u_core.u_gi.u_cal.g_m\\[1\\].u_pm',8.64)]
with (P/'port_geom_repack3.tsv').open() as src,(out/'port_geom_repack3.tsv').open('w') as dst:
 for line in src:
  a=line.rstrip('\n').split('\t')
  if a[0]=='C':
   for prefix,dx in deltas:
    if a[8]==prefix or a[8].startswith(prefix+'::'):
     a[4]=str(float(a[4])+dx);a[6]=str(float(a[6])+dx)
     line='\t'.join(a)+'\n';break
  dst.write(line)
print('CLOCKAWARE_FINITE_SOURCE_MODEL_PREP',out,flush=True)
