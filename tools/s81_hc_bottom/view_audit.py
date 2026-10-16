import json,pathlib,subprocess,re,sys,hashlib
root=pathlib.Path(__file__).resolve().parents[2];out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'tools/hier_contract'));import native_pin_audit as a
inv=json.load(open('/home/ubuntu/artifacts/s81-suhc-homes-0811/inventory.json'))
views=[v for v in inv['historical_real_views'] if any(k in v['view'] for k in ('s81hc_cncla','s81hc_cnclb','s81hc_cnrsq_ref','s81hc_cntreeh2_ref'))]
recs=[]
for v in views:
 cell=v['cell'];view=v['view'];d=out/pathlib.Path(view).parts[2];d.mkdir(exist_ok=True)
 def get(path):return subprocess.check_output(['git','show','HEAD:'+path],cwd=root)
 raw=get(view+'/'+cell+'.lef');lf=raw.decode();m=re.search(r'^  PIN sk\n(.*?)^  END sk',lf,re.M|re.S);assert m,view
 b=m.group(1);layer=re.search(r'LAYER (\S+)',b)[1];rect=list(map(float,re.search(r'RECT\s+([^;]+)',b)[1].split()))
 for f in [cell+'_tt.lib','insertion.json']:(d/f).write_bytes(get(view+'/'+f))
 q=a.audit_one((str(root),cell,str(d)));q['original_view']=view;q['clock_pin']={'name':'sk','layer':layer,'rect_um':rect,'center_um':[(rect[0]+rect[2])/2,(rect[1]+rect[3])/2],'declared_use':'SIGNAL'};q['outline_um']=v['outline_um'];q['lef_sha256']=hashlib.sha256(raw).hexdigest()
 spec=json.loads(get(str(pathlib.Path(view).parents[1])+'/spec.json'));q['spec_params']=spec.get('params',{});q['qualification']='historical real view native screen only; current source-binding and all incident tuple/pin joins remain open'
 recs.append(q)
 print(view,q['pass'],q.get('launch_ps'),q.get('capture_ps'),q['clock_pin'],flush=True)
(root/'results/arch/s81_hc_current_1016/cnbot_historical_native_views.json').write_text(json.dumps(recs,indent=2)+'\n')
