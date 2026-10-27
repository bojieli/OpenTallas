import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2] / 'tools' / 'die_plan'))
import odb
import psm_distributed_load as P
D=odb.dbDatabase.create()
T=odb.dbTech_create(D,'tiny')
layer=odb.dbTechLayer_create(T,'M7','ROUTING')
L=odb.dbLib_create(D,'tiny',T)
M=odb.dbMaster_create(L,'macro'); M.setType('BLOCK'); M.setWidth(1000); M.setHeight(2000)
mt=odb.dbMTerm_create(M,'VDD','INOUT','POWER'); pin=odb.dbMPin_create(mt)
odb.dbBox_create(pin,layer,100,0,120,2000); odb.dbBox_create(pin,layer,300,0,320,2000)
M.setFrozen()
C=odb.dbChip_create(D,T); B=odb.dbBlock_create(C,'top')
net=odb.dbNet_create(B,'VDD'); net.setSigType('POWER')
i=odb.dbInst_create(B,M,'u'); i.setOrient('MX'); i.setLocation(100,200); i.setPlacementStatus('FIRM'); i.findITerm('VDD').connect(net)
c=P.distribute(D,odb); print(c)
i=B.findInst('u'); print(i.getLocation(),i.getOrient()); assert tuple(i.getLocation())==(100,200); assert i.getOrient()=='MX'
assert len(list(net.getITerms()))==2
assert len(list(i.getMaster().getMTerms()))==2
print('NATIVE_SPLIT_PASS')
try: P.split_rectangles([(None,0,0,1,2),(None,0,0,1,3)])
except ValueError: print('UNEQUAL_AREA_MUTANT_CAUGHT')
else: raise AssertionError('unequal area current model accepted')
