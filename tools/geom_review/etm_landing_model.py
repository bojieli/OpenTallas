import json,re,math
from pathlib import Path
import argparse
ap=argparse.ArgumentParser(description='Estimate propagated ETM corridor delay/slew from exact TT INVBUF NLDM and planned wire lengths; never qualifies timing.')
ap.add_argument('--lib',required=True);ap.add_argument('--plan',required=True);ap.add_argument('--output',required=True)
args=ap.parse_args();lib=Path(args.lib).read_text()
def section(s,start):
 i=s.index('{',start);level=1;j=i+1
 while level:
  if s[j]=='{':level+=1
  if s[j]=='}':level-=1
  j+=1
 return s[i+1:j-1]
def table(cell,name):
 s=section(lib,lib.index('cell ('+cell+')'))
 t=section(s,s.index(name+' ('))
 a=[[float(z) for z in re.search('index_'+str(k)+r'\s*\("([^"]+)',t)[1].split(',')] for k in [1,2]]
 v=section(s,s.index(name+' ('))
 vv=v[v.index('values'):];rows=re.findall(r'"([^"]+)"',vv);data=[[float(z) for z in row.split(',')] for row in rows]
 return a,data
T={n:{q:table('BUFx'+str(n)+'_ASAP7_75t_R',q) for q in ['cell_rise','cell_fall','rise_transition','fall_transition']} for n in [8,24]}
def interp(t,slew,load):
 (xs,ys),d=t
 def at(x,a):
  x=max(a[0],min(a[-1],x))
  i=next((k for k in range(len(a)-1) if a[k]<=x<=a[k+1]),len(a)-2)
  return i,(x-a[i])/(a[i+1]-a[i])
 i,u=at(slew,xs);j,v=at(load,ys)
 return (1-u)*((1-v)*d[i][j]+v*d[i][j+1])+u*((1-v)*d[i+1][j]+v*d[i+1][j+1])
def evaluate(path,strength):
 # Last node is the macroface BUF8; intermediates have selected minimum drive.
 n=len(path);ins=[0]+[strength]*(n-2)+[8];caps={8:.852045,24:2.35026};arr=0;slew=20;stage=[]
 for i,(a,b) in enumerate(zip(path,path[1:])):
  L=abs(a[0]-b[0])+abs(a[1]-b[1]);cap=.113298*L+caps[ins[i+1]]
  if i==0:delay=.25*cap;slew=math.sqrt(20**2+(.5*cap)**2)
  else:
   delay=max(interp(T[ins[i]]['cell_rise'],slew,cap),interp(T[ins[i]]['cell_fall'],slew,cap))
   slew=max(interp(T[ins[i]]['rise_transition'],slew,cap),interp(T[ins[i]]['fall_transition'],slew,cap))
  rc=.0214161*L*(.113298*L/2+caps[ins[i+1]])
  arr+=delay+rc;slew=math.sqrt(slew*slew+(2.2*rc)**2)
  stage.append({'wire_um':L,'driver':24 if i==0 else ins[i],'load_ff':cap,'cell_delay_ps':delay,'wire_elmore_ps':rc,'sink_slew_ps_estimate':slew})
 # <=7um macroface output budget (actual worst actualfacepoint in plan).
 L=7;cap=.113298*L+2.9406
 delay=max(interp(T[8]['cell_rise'],slew,cap),interp(T[8]['cell_fall'],slew,cap));rc=.0214161*L*(.113298*L/2+2.9406)
 arr+=delay+rc
 return arr,stage,delay
p=json.load(open(args.plan))
for q in p['plans']:
 if q.get('status')!='GEOMETRY_CANDIDATE':continue
 q['nlDm_models']={}
 for b in [8,24]:
  extra,st,ld=evaluate(q['path_pin_centres_um'],b);v={'extra_ps':extra,'stages':st,'leaf_delay_ps':ld,'cell_load_units':'fF','wire_slew_model':'sqrt(input_slew^2+(2.2*Elmore)^2); planning estimate, not STA'}
  v['macro_arrival_ps_estimate']=q['actual_tt_source_arrival_ps']+extra
  v['target_error_ps']=v['macro_arrival_ps_estimate']-q['target_tt_macro_arrival_ps']
  q['nlDm_models'][str(b)]=v

json.dump(p,open(args.output,'w'),indent=2)
