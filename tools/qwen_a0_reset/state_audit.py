"""Independent actual-native ownership census and reset-tree cut, OpenROAD Python."""
import os,json,collections,re,hashlib
import odb
base=os.environ['A0_OUT'];db=odb.dbDatabase.create();odb.read_db(db,base+'/candidate.odb');b=db.getChip().getBlock();m=json.load(open(base+'/manifest.json'))
def ins(i):return [p for p in i.getITerms() if p.getNet() and str(p.getIoType())=='INPUT' and str(p.getSigType()) not in ('POWER','GROUND')]
def outs(i):return [p for p in i.getITerms() if p.getNet() and str(p.getIoType())=='OUTPUT']
def label(p):return p.getInst().getName()+'/'+p.getMTerm().getName()
def clocks(i):return sorted({p.getNet().getName() for p in ins(i) if p.getMTerm().getName() in ('CLK','CK','CP','clk') or str(p.getSigType())=='CLOCK'})
def states(net,seen=None):
 seen=set() if seen is None else set(seen)
 if net.getId() in seen:return set()
 seen.add(net.getId());r=set()
 for p in net.getITerms():
  if str(p.getIoType())!='INPUT':continue
  i=p.getInst()
  if re.search('DFF|LATCH|DHL',i.getMaster().getName()):r.add((i.getName(),i.getMaster().getName(),p.getMTerm().getName(),tuple(clocks(i))))
  elif str(i.getMaster().getType())=='BLOCK':r.add((i.getName(),i.getMaster().getName(),p.getMTerm().getName(),tuple(clocks(i))))
  else:
   for o in outs(i):r.update(states(o.getNet(),seen))
 return r
rows=[]
for r in m['leaf_endpoints']:
 instance,pin=r['endpoint'].rsplit('/',1);i=b.findInst(instance);p=i.findITerm(pin)
 direct_async=pin in ('RESETN','SETN'); hard=str(i.getMaster().getType())=='BLOCK'
 targets={(i.getName(),i.getMaster().getName(),pin,tuple(clocks(i)))} if direct_async or hard else set().union(*(states(o.getNet()) for o in outs(i)))
 rows.append(dict(endpoint=r['endpoint'],clock=r['clock'],leaf=r['leaf'],kind='native_async_pin' if direct_async else 'hard_reset_pin' if hard else 'synchronous_reset_logic',target_states=[dict(instance=n,master=ma,input=p,clocks=list(cl)) for n,ma,p,cl in sorted(targets)]))
# Independent actual graph: every tree output counts all real native input pins,
# traversing only native BUF/INV. Raw must be one asynchronous reset pin.
def terminals(net,seen=None):
 seen=set() if seen is None else set(seen)
 if net.getId() in seen:return set()
 seen.add(net.getId());s=set()
 for p in net.getITerms():
  if str(p.getIoType())!='INPUT':continue
  i=p.getInst()
  if re.match(r'^(BUF|INV|HB).*ASAP7',i.getMaster().getName()):
   for o in outs(i):s.update(terminals(o.getNet(),seen))
  else:s.add(label(p))
 return s
checks=[]
for name in m['added_cells']+[m['face_stage2']]:
 i=b.findInst(name)
 if 'DFF' not in i.getMaster().getName():continue
 for o in outs(i):checks.append(dict(driver=label(o),clock=clocks(i),loads=sorted(terminals(o.getNet()))))
assert all(len(r['loads'])<=32 for r in checks)
raw=terminals(b.findNet('rst_n'));assert raw=={'a0_reset_face1/RESETN'},raw
sync=[r for r in rows if r['kind']=='synchronous_reset_logic'];assert len(sync)==28
report=dict(schema='opentallas.a0.native_reset_state_audit.v1',candidate_odb_sha256=hashlib.sha256(open(base+'/candidate.odb','rb').read()).hexdigest(),all_endpoint_counts=dict(collections.Counter(r['kind'] for r in rows)),raw_endpoints=sorted(raw),reset_drivers=checks,synchronous_endpoint_states=sync,all_endpoint_states=rows,original_async_clear='asynchronous native reset pin level; all clocks may stop',original_sync_clear='first resumed destination edge while leaf reset is still low; next local edge may release reset',physical_qualification=False)
json.dump(report,open(base+'/state_audit.json','w'),indent=2)
# Actual native reset cut: copy exact master/pin/net equations for all new
# cells and the changed original face reset state. No substitute FF equations.
chosen=[b.findInst(n) for n in m['added_cells']+[m['face_stage2']]]
clocknames=sorted({c for i in chosen for c in clocks(i)})
leafnets=['a0_reset_leaf_%02d_q'%n for n in range(19)]
ports=['rst_n']+clocknames
nets={p.getNet().getName() for i in chosen for p in i.getITerms() if p.getNet() and str(p.getSigType()) not in ('POWER','GROUND')}
def e(n):return '\\'+n+' '
with open(base+'/reset_cut.v','w') as f:
 f.write('module a0_actual_reset_cut('+','.join(ports)+',leaf);\ninput '+','.join(ports)+'; output [18:0] leaf;\n')
 for n in sorted(nets-set(ports)):f.write('wire '+e(n)+';\n')
 for n,net in enumerate(leafnets):f.write('assign leaf[%d] = %s;\n'%(n,e(net)))
 for i in chosen:
  pp=[p for p in i.getITerms() if p.getNet() and str(p.getSigType()) not in ('POWER','GROUND')]
  f.write(e(i.getMaster().getName())+' '+e(i.getName())+' ('+','.join('.'+e(p.getMTerm().getName())+'('+e(p.getNet().getName())+')' for p in pp)+');\n')
 f.write('endmodule\n')
print('A0_RESET_STATE_AUDIT_PASS',report['all_endpoint_counts'],'tree',len(checks),'maxloads',max(len(r['loads']) for r in checks))
