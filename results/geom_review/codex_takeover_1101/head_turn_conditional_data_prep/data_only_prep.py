from pathlib import Path
import sys,json,math
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/head-wave-path-query-1102/hd_st_n3_turn/geom5/geom.tsv');old=json.load(open(P/'balanced_prep.json'));roots=[]
for ri,r in enumerate(old['roots']):
 data=[];held=[]
 for a in r['leaf_groups']:
  for z in a['members']:
   i=z['id'];ss=[e for ni in D.drives.get(i,[])for e in D.nets[ni][2]]
   ok=D.cells[i][1].startswith('AO21x1_')and len(ss)==1and ss[0][0]=='i'and not ss[0][2]and D.cells[ss[0][1]][1].startswith(('DFFHQN','DFFLQN'))
   (data if ok else held).append(z)
 data.sort(key=lambda z:(z['xy'][0],z['xy'][1],z['instance']));leaf=[]
 for k in range(0,len(data),16):
  a=data[k:k+16];pt=[sum(z['xy'][0]for z in a)/len(a),572.4+ri*.54];leaf.append(dict(index=len(leaf),xy=pt,fanout=len(a),members=a,max_leaf_centre_l1_um=max(abs(z['xy'][0]-pt[0])+abs(z['xy'][1]-pt[1])for z in a)))
 upper=[]
 for k in range(0,len(leaf),8):
  a=leaf[k:k+8];pt=[sum(z['xy'][0]for z in a)/len(a),568.62+ri*.54];upper.append(dict(index=len(upper),xy=pt,fanout=len(a),children=[z['index']for z in a]))
 roots.append(dict(original_root=r['root'],root_master=r['root_master'],root_inputs=r['root_inputs'],original_xy=r['root_xy'],clone_xy=[r['root_xy'][0],576.18+ri*.54],data_leaf_pins=len(data),protected_other_leaf_pins=held,leaf_groups=leaf,upper_groups=upper,additional_BUF=len(leaf)+len(upper),additional_OR=1))
res=dict(scope='CONDITIONAL DATA-only structural tree PREP; no RTL/native mutation/STA/timinggain; upstream forwardedclock frame still unqualified',root_copies=len(roots),new_BUF=sum(r['additional_BUF']for r in roots),new_OR=len(roots),new_cells=sum(r['additional_BUF']+1for r in roots),existing_40_BUFFs_retained=True,DATA_leaf_pins=sum(r['data_leaf_pins']for r in roots),held_other_leaf_pins=sum(len(r['protected_other_leaf_pins'])for r in roots),added_upstream_input_pins=3*len(roots),new_FF=0,new_cycles=0,clock_or_public_pin_edits=0,roots=roots,holds=['All originalORs/40BUFs and23nonDATA/shared leaf pins retained; removing DATA fanout changes oldnet loads, not assumed electrically free','Five samefunctionOR copies add15upstream input loads; sharedcounter/control/reset effects require actual paired analysis','152schematic BUF centres are guide concepts only, not native row/TAP/body/PG legality or selected master sizing','Exact native ITerm identity required for2067rewires; dump IDs/instance names alone are not an executable ECO','Fresh proof/sourceepoch/context authority and exact postprofile timing must precede any physical scope'])
(P/'data_only_prep.json').write_text(json.dumps(res,indent=1)+'\n')
fig,ax=plt.subplots(figsize=(14,7));pts=[g.ctr(c)for c in D.cells.values()if 10<c[2]<240 and 560<c[3]<604.8];ax.scatter([p[0]for p in pts],[p[1]for p in pts],s=2,color='.8',alpha=.45,label='Actual unchanged native cell centres')
for ri,r in enumerate(roots):
 col=plt.cm.tab10(ri);cx,cy=r['clone_xy'];ax.scatter([cx],[cy],marker='s',c=[col],s=35);ax.text(cx+1,cy,r['original_root'].split('/')[-1]+' copy',fontsize=7,color=col)
 for u in r['upper_groups']:
  ux,uy=u['xy'];ax.plot([cx,ux],[cy,uy],color=col,lw=.7);ax.scatter([ux],[uy],s=14,c=[col])
  for j in u['children']:
   z=r['leaf_groups'][j];x,y=z['xy'];ax.plot([ux,x],[uy,y],color=col,lw=.5);ax.scatter([x],[y],s=7,c=[col])
   for q in z['members']:ax.plot([x,q['xy'][0]],[y,q['xy'][1]],color=col,lw=.2,alpha=.25)
ax.set(xlim=(10,240),ylim=(562,604),xlabel='um',ylabel='um',title='Turn conditional DATA-only control-tree pricing:5OR copies+152BUF,2067 DATA leaf pins\nOriginalOR/BUF/control/FF/clock/publicpins retained;15new upstream loads; no native legality or timing claim');ax.legend(loc='upper left',fontsize=8);fig.tight_layout();fig.savefig(P/'conditional_data_tree.png',dpi=150)
print({k:v for k,v in res.items()if k not in['roots','holds']})
