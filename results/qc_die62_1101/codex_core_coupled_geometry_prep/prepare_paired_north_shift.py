import pathlib,json,gzip,shutil,argparse
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);p.add_argument('--delta',type=float,required=True);a=p.parse_args();i=pathlib.Path(a.source);o=pathlib.Path(a.out);o.mkdir(exist_ok=True);g=json.load(open(i/'MACRO_GEOMETRY.json'));raw=json.load(gzip.open(i/'DISABLED_PARENT_PLAN_UNRELEASED.json.gz'));changes=[]
for row in raw['partition_types']['coll_core']['buses']:
 if row.get('face')=='N':
  old=row['window_um'][:];row['window_um']=[round(v+a.delta,6)for v in old];changes.append(dict(type='coll_core',bus=row['name'],before=old,proposed=row['window_um']))
for row in raw['partition_types']['coll_ftm']['ft_slots']:
 for side in ['in','out']:
  k=side+'_window_um'
  if row.get(side+'_face')=='S'and k in row:
   old=row[k][:];row[k]=[round(v+a.delta,6)for v in old];changes.append(dict(type='coll_ftm',slot=row['name'],side=side,before=old,proposed=row[k]))
g['north_bank_remap_total_um']=round(g['north_bank_remap_total_um']+a.delta,6);g['revision']='Finite paired north-window shift after actual CA-chain native-grid failure; priorgeometry retained; no data edge, clock/tap or reach-budget change.'
for f in ['NEW_FOLD_NIO_PIN_POLICY_UNQUALIFIED.json']:shutil.copy(i/f,o/f)
shutil.copytree(i/'PROPOSED_macro_pins',o/'PROPOSED_macro_pins',dirs_exist_ok=True);(o/'MACRO_GEOMETRY.json').write_text(json.dumps(g,indent=2)+'\n');(o/'PAIRED_NORTH_PIN_WINDOW_PROPOSAL.json').write_text(json.dumps(dict(status='DISABLED_PAIRED_PIN_WINDOW_SOURCE_EVENT_UNRELEASED',source=str(i),delta_um=a.delta,total_delta_um=g['north_bank_remap_total_um'],changes=changes),indent=2)+'\n')
with gzip.open(o/'DISABLED_PARENT_PLAN_UNRELEASED.json.gz','wt')as f:json.dump(raw,f,separators=(',',':'))
