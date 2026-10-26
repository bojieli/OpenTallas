import odb
from pathlib import Path
for kind in ['data_on_protected_pin','provisional_clock']:
 d=odb.dbDatabase.create();odb.read_db(d,'/work/target.odb');b=d.getChip().getBlock()
 if kind=='data_on_protected_pin':b.findInst('a').findITerm('CK').connect(b.findNet('sig_mid'))
 else:
  n=b.findNet('clk');n.rename('clk_provisional');assert n.getName()=='clk_provisional'
 odb.write_db(d,'/work/guard_target_'+kind+'.odb')
Path('/work/guard_provisional.txt').write_text('clk_provisional\n')
print('GUARD_FIXTURES_READY')

d=odb.dbDatabase.create();odb.read_db(d,'/work/source.odb')
for cell in d.getChip().getBlock().getInsts():
 cell.setDoNotTouch(True);cell.setPlacementStatus('LOCKED')
odb.write_db(d,'/work/guard_source_already_dnt.odb')
