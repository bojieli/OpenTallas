from pathlib import Path
import json,re,tkinter,hashlib
p=Path('/home/ubuntu/coord/tmp/codex-cap-gate-0810');tk=tkinter.Tcl();out={}
for c in ['TT','FF']:
 s=(p/f'cap_policy_{c}.log').read_text();warn=set();paths={};stats={}
 for l in s.splitlines():
  m=re.search(r'Missing route to pin (.*?) in net (.*)\.$',l)
  if m:warn.add(m[2].replace('\\',''))
  if l.startswith('SO STD_'):k,v=l.split()[1:3];stats[k]=float(v)
  if l.startswith('CAP_PATH '):
   f=tk.splitlist(l);paths.setdefault(f[1]+'/'+f[2],{})['slack_ps']=float(f[3]);paths[f[1]+'/'+f[2]]['startpoint']=f[4];paths[f[1]+'/'+f[2]]['endpoint']=f[5]
  if l.startswith('CAP_POINT '):
   f=tk.splitlist(l);paths.setdefault(f[1]+'/'+f[2],{}).setdefault('points',[]).append({'pin':f[3],'arrival_ps':float(f[4])})
  if l.startswith('CAP_POINT_NET '):
   f=tk.splitlist(l);paths.setdefault(f[1]+'/'+f[2],{}).setdefault('nets',set()).update(x.replace('\\','') for x in tk.splitlist(f[4]))
 for k,r in paths.items():r['missing_route_warnings_on_path']=sorted(set(r['nets'])&warn);r['nets']=sorted(r['nets'])
 assert len(paths)==8 and all('slack_ps'in r for r in paths.values())
 out[c]={'native_exit':1,'failure_class':'AUX_COLLECTION_PRINTER_AFTER_ALL8_PATH_QUERIES','exact_error':'STA2204 get_full_name applied to multi-pin $loads collection','standard_timing':stats,'clock_insertion':json.load(open(p/f'postcts_gate_{c.lower()}.json')),'path_queries':paths,'EST0026_missing_route_net_count':len(warn),'EST0026_missing_route_nets':sorted(warn),'coverage_affected_paths':[k for k,r in paths.items() if r['missing_route_warnings_on_path']]}
x={'schema':'opentallas.cap_west2_partial_diagnostic.v1','kind':'partial_diagnostic_preserved_FAILURE','policy':'actualSDC833/setup0/hold25; unchangedcanonical9db functions, freshGRTestimation','corners':out,'remaining_globalTT':'d3_v[0] -> cw_n_d[126], −11.47ps/14endpoints; oldlweco_019416 andlweco_119417 sequential DATAchain','reset_correction':'u_rr.rst_n[15] recovery path MET+321.74, notthecriticalsetupfailure','closed':False,'pair_census':'NOT RUN due auxiliary printer failure (TT datafailure would stop it anyway)','next':'No physical rerun or pricing replay solely forprinter; preservealllogs; GRT-onlyguidecoverage and actualsourceRCXvsGRT basis limitations remain'}
(p/'PARTIAL_DIAGNOSTIC_CLASSIFIED.json').write_text(json.dumps(x,indent=2));print(json.dumps({c:{'std':r['standard_timing'],'warnnets':r['EST0026_missing_route_net_count'],'affected':r['coverage_affected_paths']} for c,r in out.items()},indent=1))
