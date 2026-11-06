from pathlib import Path
from collections import Counter
import json,sys,hashlib
R=Path('/srv/opentallas-scratch2/claude/codex-qc-tapsplit-1106');SRC=R/'src';sys.path.insert(0,str(SRC/'tools/die_plan'));import taps as T,schema as S
POR=SRC/'physical/die_plan/qwen_compute/plan_of_record';raw=json.loads((POR/'plan_qc52.json').read_text());tn='sle_su_c';t=raw['partition_types'][tn];base=json.loads(json.dumps(t));rows=[l.split() for l in (R/'probe/east/sinks.txt').read_text().splitlines()];actual=[(a[1],float(a[2]),float(a[3])) for a in rows if a[0]=='SINK' and a[-1]=='0'];hard=[a[1] for a in rows if a[0]=='SINK' and a[-1]=='1'];mac={a[1]:list(map(float,a[2:])) for a in rows if a[0]=='MACRO'}
geom=[]
for hc in t['hard_cores']:
 n=hc.get('physical_inst','u_bound.u_'+hc['inst']);assert n in mac,n
 x,y=hc['origin_um'];dx,dy=hc.get('track_offset_um',[0,0]);x+=dx;y+=dy;w,h=hc['outline_um'];o=hc.get('orient','R0')
 if o in ['R90','R270','MXR90','MYR90']:w,h=h,w
 expected=[x,y,x+w,y+h];err=max(abs(a-b) for a,b in zip(expected,mac[n]));geom.append({'instance':n,'max_bbox_error_um':err});assert err<.002,(n,expected,mac[n])
B=8.64;bins=Counter((int(x//B),int(y//B)) for _,x,y in actual);data={'bin_um':B,'n':len(actual),'bins':[[round((i+.5)*B,3),round((j+.5)*B,3),n] for (i,j),n in sorted(bins.items())]}
EV=SRC/'physical/die_plan/qwen_compute/tap_split_1106/east_event';EV.mkdir(exist_ok=True)
(EV/'east_sink_bins.json').write_text(json.dumps(data,separators=(',',':'))+'\n');c=t['clock'];c.update(sink_bins_file=str((EV/'east_sink_bins.json').relative_to(SRC)),tap_mode='density',tap_max_sinks=1200,tap_target_sinks=900,tap_radius_um=200.)
P=S.Plan(raw,str(POR/'plan_qc52.json'));new=T.density_taps(P,tn,False);old=[(a[1],float(a[2]),float(a[3])) for a in rows if a[0]=='TAP' and '_c' not in a[1]];pts=[(x,y,1) for n,x,y in actual];ol,of,_=T.assign(old,pts,1200,200,max_distance_um=200);nl,nf,_=T.assign(new,pts,1200,200,max_distance_um=200)
report={'type':tn,'source_placement':'Intel2 APf6a8a1576762 actual3_place','soft_sinks':len(actual),'hard_root_sinks_excluded':hard,'old_taps':len(old),'new_taps':len(new),'old_max_load_after_cap':max(ol),'old_max_reach_um':max(of),'new_max_load_after_cap':max(nl),'new_max_reach_um':max(nf),'new_tap_rows':new,'actual_macro_geometry':geom,'source_window_unchanged_ps':120,'physical_cts':'NOT RUN','data_cycles_changed':0};assert max(nl)<=1200 and max(nf)<=200,report
(EV/'model.json').write_text(json.dumps(report,indent=1)+'\n');H=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest();(EV/'clock_patch.json').write_text(json.dumps({tn:{'base_type_sha256':H(base),'clock':c}},indent=1)+'\n');(EV/'render_inputs.json').write_text(json.dumps({tn:{'outline_um':t['outline_um'],'hard_cores':t['hard_cores'],'bins':data['bins'],'taps':new}},separators=(',',':'))+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['new_tap_rows','actual_macro_geometry']},indent=1))
