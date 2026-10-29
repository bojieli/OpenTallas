import json,re,pathlib,odb
b=odb.read_db(odb.dbDatabase.create(),'/kit/run/results/asap7/hbc_hnx_lane_x/base/6_final.odb').getChip().getBlock();u=b.getDbUnitsPerMicron()
log=pathlib.Path('/kit/signoff_m10b/tt/sta.log').read_text();names=re.findall(r'^([^\s]+/[^\s]+)\s+320\.00\s+[\d.]+\s+-[\d.]+\s+\(VIOLATED\)',log,re.M)
def cell(i):
 x,y=i.getLocation();m=i.getMaster();return dict(name=i.getName(),master=m.getName(),x=x/u,y=y/u,w=m.getWidth()/u,h=m.getHeight()/u)
def net(n):
 if n is None:return None
 return dict(name=n.getName(),iterms=[dict(cell=cell(t.getInst()),pin=t.getMTerm().getName(),direction=t.getIoType()) for t in n.getITerms()],bterms=[t.getName() for t in n.getBTerms()])
out={'slew':{},'hold':{},'reset':{},'points':[]}
imap={i.getName().replace(chr(92),''):i for i in b.getInsts()}
for name in names:
 cn,pn=name.rsplit('/',1);i=b.findInst(cn);out['slew'][name]=net(i.findITerm(pn).getNet())
for name in ['gt[0]$_DFF_P_','u_tcc.u_h1.g_lane[1].u_add.u.s1_exp[2]$_DFF_P_','u_tcc.u_h1.g_lane[1].u_add.u.y[17]$_DFF_P_']:
 i=imap.get(name)
 if i is None:continue
 out['hold'][name]=dict(cell=cell(i),data=net(i.findITerm('D').getNet()),clock=net(i.findITerm('CLK').getNet()))
for name in ['r_bdc','r_g','r_tcc']:
 out['reset'][name]=net(b.findBTerm(name).getNet())
for i in b.getInsts():
 if 'FILLER' not in i.getMaster().getName() and 'DECAP' not in i.getMaster().getName():out['points'].append(cell(i))
pathlib.Path('/d/actual_hold.json').write_text(json.dumps(out))
print('DUMP_DONE',len(names),len(out['points']))
