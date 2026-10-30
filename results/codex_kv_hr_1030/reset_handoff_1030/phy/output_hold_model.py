from pathlib import Path
import re,json,bisect,collections,math
P=Path(__file__).parent;L=P.parent/'hb_model'
def table(text,kind):
 b=re.search(kind+r'\s*\([^)]*\)\s*\{(.*?)\n\s*\}',text,re.S)[1];ax=[[float(x)for x in re.search(r'index_'+str(i)+r'\s*\("([^"]+)"',b)[1].split(',')]for i in[1,2]];vs=[[float(x)for x in r.split(',')]for r in re.findall(r'"([^"\n]+)"',b[b.index('values'):])];return ax,vs
def interp(tab,s,c):
 (x,y),v=tab;i=max(0,min(len(x)-2,bisect.bisect_right(x,s)-1));j=max(0,min(len(y)-2,bisect.bisect_right(y,c)-1));a=(s-x[i])/(x[i+1]-x[i]);b=(c-y[j])/(y[j+1]-y[j]);return(1-a)*(1-b)*v[i][j]+(1-a)*b*v[i][j+1]+a*(1-b)*v[i+1][j]+a*b*v[i+1][j+1]
lib={};cin={}
for cor in['TT','FF']:
 lib[cor]={}
 for cell in['BUFx2','HB4xp67']:
  text=(L/f'{cell}_ASAP7_75t_R_{cor}.txt').read_text();lib[cor][cell]={k:table(text,k)for k in['cell_rise','cell_fall','rise_transition','fall_transition']}
  cin[cor,cell]=float(re.search(r'pin\s*\(A\).*?\bcapacitance\s*:\s*([.0-9]+)',text,re.S)[1])
a={cor:{r[0]:r for line in(P/f'output_electrical_{cor}.tsv').read_text().splitlines()if(r:=line.split('\t'))}for cor in['TT','FF']};plans=[]
for ep,r in a['FF'].items():
 sl=float(r[1]);oldcap=float(r[4]);oldwire=float(r[8]);vals={}
 for n in range(1,5):
  gains=[]
  for trans,ix in [('rise',6),('fall',7)]:
   s=float(r[ix]);delay='cell_'+trans;slew=trans+'_transition';old=interp(lib['FF']['BUFx2'][delay],s,oldcap)
   load=cin['FF','HB4xp67'];new=interp(lib['FF']['BUFx2'][delay],s,load);s=interp(lib['FF']['BUFx2'][slew],s,load)
   for j in range(n):
    load=2.0 if j==n-1 else cin['FF','HB4xp67'];new+=interp(lib['FF']['HB4xp67'][delay],s,load);s=interp(lib['FF']['HB4xp67'][slew],s,load)
   gains.append(new-old-oldwire)
  vals[n]=min(gains)
  if sl+vals[n]>=5:break
 else:raise RuntimeError(('needs>4HB4',ep))
 # Uppercellcost with 2.2fF extra wirecharge per segment (<=10um@.22fF/um); oldoutputwire notcredited back.
 tr=a['TT'][ep];costs=[]
 for trans,ix in [('rise',6),('fall',7)]:
  s=float(tr[ix]);delay='cell_'+trans;slew=trans+'_transition';old=interp(lib['TT']['BUFx2'][delay],s,float(tr[5]));load=cin['TT','HB4xp67']+2.2;new=interp(lib['TT']['BUFx2'][delay],s,load);s=interp(lib['TT']['BUFx2'][slew],s,load)
  for j in range(n):
   load=(float(tr[5])if j==n-1 else cin['TT','HB4xp67'])+2.2;new+=interp(lib['TT']['HB4xp67'][delay],s,load);s=interp(lib['TT']['HB4xp67'][slew],s,load)
  costs.append(new-old+10*(n+1))
 plans.append({'port':ep,'old_last_driver':r[2],'old_last_master':r[3],'FF_slack_ps':sl,'TT_setup_ps':float(tr[1]),'new_HB4':n,'conservative_cell_gain_minus_oldwire_ps':vals[n],'FF_model_margin_ps':sl+vals[n],'TT_cell_cost_plus_wire_allowance_ps':max(costs),'TT_remaining_estimate_ps':float(tr[1])-max(costs)})
r={'status':'MODEL_ONLY_NOT_APPLIED_NOT_QUALIFIED','unique_negative_output_endpoints':len(plans),'rawrows':279,'existing_output_primitive_counts':{'INVplusBUF':2,'HB4':0},'new_HB4_count':sum(x['new_HB4']for x in plans),'new_count_histogram':dict(collections.Counter(x['new_HB4']for x in plans)),'new_area_um2':sum(x['new_HB4']for x in plans)*.10206,'min_FF_model_margin_ps':min(x['FF_model_margin_ps']for x in plans),'min_TT_remaining_estimate_ps':min(x['TT_remaining_estimate_ps']for x in plans),'max_TT_added_estimate_ps':max(x['TT_cell_cost_plus_wire_allowance_ps']for x in plans),'method':'Actualsame4CTS per-output trueFFnegativepaths +actual lastBUFx2 inputR/Fslew andnetC; updateexistingdriverloadtoHB4inputcap,propagateactualNLDMslew through1..4HB4,conservative minwire0,lastload2fF; subtractwholeoldoutputwiredelay. TTpriceeachnewsegment<=10um@.22fF/um plus10pswireallowance/segment. NativefreshGRT+TTFFactualgatesstillrequired.','plans':plans};(P/'output_hold_model.json').write_text(json.dumps(r,indent=1)+'\n');print({k:v for k,v in r.items()if k!='plans'})
