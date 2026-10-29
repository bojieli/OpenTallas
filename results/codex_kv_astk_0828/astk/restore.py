import odb
from collections import Counter
old=odb.dbDatabase.create();odb.read_db(old,'/work/original_3_place.odb')
original={i.getName():i.getPlacementStatus() for i in old.getChip().getBlock().getInsts()}
print('ORIGINAL_STATUS',dict(Counter(original.values())))
new=odb.dbDatabase.create();odb.read_db(new,'/work/run/results/asap7/hc_kv3_astk__190_08x181_44/base/3_place.odb')
b=new.getChip().getBlock(); before=Counter(i.getPlacementStatus() for i in b.getInsts());changed=0
for i in b.getInsts():
 s=original[i.getName()]
 if i.getPlacementStatus()!=s:i.setPlacementStatus(s);changed+=1
print('CORRECTED_BEFORE',dict(before),'RESTORED',changed)
odb.write_db(new,'/work/restored_placement_status.odb')
