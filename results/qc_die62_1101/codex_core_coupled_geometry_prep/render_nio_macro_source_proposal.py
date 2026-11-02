import pathlib,json,gzip,re,argparse,collections
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=argparse.ArgumentParser();p.add_argument('--proposal',required=True);p.add_argument('--join',required=True);a=p.parse_args();o=pathlib.Path(a.proposal);g=json.load(open(o/'MACRO_GEOMETRY.json'));j=json.load(gzip.open(pathlib.Path(a.join)/'MACRO_READER_CONSTRAINTS.json.gz'));raw=json.load(gzip.open(o/'DISABLED_PARENT_PLAN_UNRELEASED.json.gz'));fig,(ax,pa)=plt.subplots(1,2,figsize=(15,12),gridspec_kw={'width_ratios':[2.2,1]})
for m in g['macros']:
 x,y=m['origin_um'];dx,dy=m['track_offset_um'];x+=dx;y+=dy;w,h=m['outline_um'];z=m['halo_um'];fold=m['module']=='ot_coll_fold_slice';ax.add_patch(Rectangle((x-z,y-z),w+2*z,h+2*z,fc='#f0f0f0',ec='#aaa',lw=.4));ax.add_patch(Rectangle((x,y),w,h,fc='#f4d18a'if fold else'#c5d7e9',ec='#5d513b'if fold else'#36546d',lw=.7));n=m['inst']
 if 'g_bank['in n:n='F'+re.search('g_face_([01])',n)[1]+' codec'+re.search(r'g_bank\[(\d)\]',n)[1]
 elif'u_rx.u_mem'in n or'u_tx.u_mem'in n:n='F'+re.search('g_face_([01])',n)[1]+(' RX'if'u_rx.'in n else' TX')
 else:n=n.split('u_coll.')[-1].replace('.u_fs','').replace('.u_m','')
 ax.text(x+w/2,y+h/2,n+' '+m.get('orient','R0'),fontsize=7,ha='center',va='center')
 if fold:
  yy=y if m.get('orient')=='MX'else y+h;ax.plot([x+9.624,x+119.352],[yy,yy],color='#b3751f',lw=2);ax.scatter([x+2.952,x+5.352],[yy,yy],c='#b21d34',s=14)
groups=collections.defaultdict(list)
for e in j['direct_macro_edges']:groups[(e['source']['instance'],e['destination']['instance'])].append(e)
for es in groups.values():
 s=[sum(e['source']['xy_um'][k]for e in es)/len(es)for k in [0,1]];d=[sum(e['destination']['xy_um'][k]for e in es)/len(es)for k in [0,1]];ax.annotate('',xy=d,xytext=s,arrowprops={'arrowstyle':'->','lw':1 if len(es)>10 else .5,'color':'#327d99','alpha':.7})
for bus in raw['partition_types']['coll_core']['buses']:
 if bus.get('face')=='N':ax.plot(bus['window_um'],[1088.64,1088.64],color='#182a40',lw=3)
ax.set(xlim=(0,760.32),ylim=(0,1088.64),aspect='equal',xlabel='CORE local X (um)',ylabel='CORE local Y (um)',title=o.name+': 21 selected SRAMs + one proposed NIO view reused 8 times\nPF R0, XF MX; macro source reach only, no FF placement claim');ax.grid(alpha=.1)
for part in raw['partitions']:
 if part['name']not in ['coll_f1','coll_f2','coll_core','coll_ucie','coll_f3','ucie_kv','glue']:continue
 x,y=part['origin_um'];w,h=raw['partition_types'][part['type']]['outline_um'];pa.add_patch(Rectangle((x,y),w,h,fc='#f4d18a'if part['name']=='coll_core'else'#c5d7e9',ec='#567',lw=.8));pa.text(x+w/2,y+h/2,part['name']+'\n'+str(round(w,2))+'x'+str(round(h,2)),ha='center',va='center',fontsize=7)
pa.set(xlim=(0,1563.84),ylim=(6400,11520),aspect='equal',xlabel='Die X (um)',ylabel='Die Y (um)',title='Held coupled parent: existing type reuse\nDie edge and F3 public north retained');pa.grid(alpha=.1)
fig.text(.05,.025,'HOLD: paired CORE N/F3 S window remap is a source proposal only; no public ABI/phase credit.\nAll 2060 direct macro bit edges <=343.810um; all 11,308 macro-adjacent FF diamonds nonempty.\nFull source still needs opposite-face valid fanout repair, normal reset rederivation, selected CA/clock constants/cohorts and all FF sites.\nNIO native LEF/LIB/registered ABI/function/PPA, SRAM PG, parent source/START/boot/programme and physical TT/FF remain unqualified.',fontsize=10);fig.tight_layout(rect=(0,.09,1,1));fig.savefig(o/'MACRO_SOURCE_REVIEW_HOLD.png',dpi=150)
