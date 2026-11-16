import json,sys,csv,collections,shutil
src,dst,census=sys.argv[1:4]
cen={}
for l in open(census):
    f=l.split('\t'); cen[f[1]]=int(f[3])
rows=list(csv.DictReader(open(src+'/hgsplit_rows.tsv'),delimiter='\t'))
rc=collections.Counter()
for r in rows:
    if r['status']=='OK': rc[r['type']]+=int(r['ring_cells'])
plan=json.load(open(src+'/plan_c.json'))
n=0
for tn,t in plan['partition_types'].items():
    if tn in rc and tn in cen:
        old=t.get('cells'); t['cells']=cen[tn]-rc[tn]
        t['note']=t['note']+" | KV-HGSPLIT-1115: cells %s -> %d = census nontap %d (OT_CELL_CENSUS floorplan, flagged-macro table) - %d hard ring child cells" % (old,t['cells'],cen[tn],rc[tn])
        print(tn,old,'->',t['cells']); n+=1
shutil.copytree(src+'/cores',dst+'/cores',dirs_exist_ok=True)
shutil.copy(src+'/hgsplit_rows.tsv',dst+'/hgsplit_rows.tsv')
json.dump(plan,open(dst+'/plan_c.json','w'),indent=1); open(dst+'/plan_c.json','a').write('\n')
print('set',n)
