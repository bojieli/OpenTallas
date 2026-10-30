from pathlib import Path
import shutil,json,re
p=Path('/srv/opentallas-scratch2/claude/codex-qc-a0-0336');old=p.with_name('codex-qc-a0-2249')/'physical/nl_ad2pB';kit=p/'physical/nl_widen';kit.mkdir(parents=True,exist_ok=True)
for x in old.iterdir():
 if x.name in ('run','diag','__pycache__') or x.suffix in ('.log','.rpt'):continue
 if x.is_dir():shutil.copytree(x,kit/x.name,dirs_exist_ok=True,copy_function=shutil.copy2)
 elif x.is_file():shutil.copy2(x,kit/x.name)
fr=json.load(open(p/'widen/nl_freeze_candidate.json'));(kit/'freeze.json').write_text(json.dumps(fr,indent=1)+'\n')
s=(kit/'macro_place.tcl').read_text()
for before,after in ((142.152,144.312),(268.32,272.64)):
 s=s.replace(f'round({before} * $dbu)',f'round({after} * $dbu)').replace(f'at {before} ',f'at {after} ')
s+='\n# Internal A0 physical rebuild: explicit row-derived clock-only reservations.\nsource /work/clock_corridors.tcl\n';(kit/'macro_place.tcl').write_text(s)
reserve=['set cc_b [ord::get_db_block]','set cc_u [$cc_b getDbUnitsPerMicron]']
for c in fr['candidate_clock_corridors']:
 r=c['clock_reserved_rect_um'];reserve.append('odb::dbBlockage_create $cc_b '+' '.join(f'[expr {{round({v:.6f}*$cc_u)}}]' for v in r))
reserve.append('puts "A0_CLOCK_CORRIDORS_RESERVED 4"');(kit/'clock_corridors.tcl').write_text('\n'.join(reserve)+'\n')
# All original graph-home identities and y positions retained. Move only points
# that land in a new reserved clock column into the nearest adjacent legal row
# pocket; actual legalization/density is measured by fresh PLACE.
count=0;maxdx=0;lines=[]
for line in (kit/'nl_graph_homes.tsv').read_text().splitlines():
 f=line.split('\t');x,y=float(f[1]),float(f[2]);new=x
 for c in fr['candidate_clock_corridors']:
  x0,y0,x1,y1=c['clock_reserved_rect_um'];rx0,_,rx1,_=c['row_rect_um']
  if x0<=new<=x1 and y0<=y<=y1:
   choices=[(rx0+x0)/2,(x1+rx1)/2];new=min(choices,key=lambda v:abs(v-new))
 if new!=x:count+=1;maxdx=max(maxdx,abs(new-x));f[1]=f'{new:.6f}'
 lines.append('\t'.join(f))
(kit/'nl_graph_homes.tsv').write_text('\n'.join(lines)+'\n')
# Exact current RTL/parameters/macros are unchanged: reuse synthesized vehicle,
# then rebuild floorplan + every placement stage (never inherit old placement).
for part in ('results','logs','reports'):
 base=old/f'run/{part}/asap7/kq_qfd_tile_nl_a0c_a0nl14icg2rr2/base';dest=kit/f'run/{part}/asap7/kq_qfd_tile_nl_a0c_a0nl14icg2rr2/base';dest.mkdir(parents=True,exist_ok=True)
 for f in base.glob('1*'):
  if f.is_file():shutil.copy2(f,dest/f.name)
(kit/'PREP.json').write_text(json.dumps(dict(scope='FRESH FLOORPLAN/PLACE ONLY',rtl_changed=False,synth_vehicle=str(old),source_pin_outline_unchanged=True,modified_graph_homes=count,max_graph_home_dx_um=maxdx),indent=1)+'\n')
print('PREP_WIDEN',count,maxdx)
