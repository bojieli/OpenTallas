import subprocess,json,pathlib
A=pathlib.Path(__file__).resolve().parent
code=r'''
import pathlib,hashlib,re,json,subprocess
B=pathlib.Path('/srv/opentallas-scratch/claude/hd4g/gen2e2');S=B/'src_6f783d0a1'
result={}
for name,sub,unit in [('ot_hgi_sfu_core_split3','sfu','oth-ubuntu-2925546-1792438892'),('ot_hbm_su_static_pgslice_lg__pv0','pgslice_correct_top','oth-ubuntu-3537412-1792439108')]:
 O=B/'source_unique_d14c90171'/sub; top='v16w_'+name
 h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 net=(O/(name+'.netlist.v')).read_text();wrapper=S/('v16w/'+top+'.sv');wrap=wrapper.read_text()
 ports=lambda t:re.search(r'module\s+\\?'+top+r'\s*\((.*?)\);',t,re.S).group(1)
 np=[x.strip().lstrip('\\') for x in ports(net).split(',')];wp=[re.findall(r'[A-Za-z_][A-Za-z0-9_$]*',x)[-1] for x in ports(wrap).split(',')]
 assert np==wp
 log=(O/(name+'.log')).read_text();assert 'End of script.' in log and 'ERROR:' not in log
 files=json.loads((O/(name+'.files.json')).read_text())
 paths=set(files['files']+[m['file'] for m in files['macros']]+['v16w/'+top+'.sv'])
 etmlog=(O/'etm.log').read_text() if (O/'etm.log').exists() else ''
 result[name]={'status':'SYNTH_PASS_NOT_PHYSICAL','output':str(O),'top':top,'ports':np,'exact_port_names_order':True,'netlist_sha256':h(O/(name+'.netlist.v')),'stat_sha256':h(O/(name+'.stat')),'log_sha256':h(O/(name+'.log')),'ys_sha256':h(O/(name+'.ys')),'input_hashes':{p:h(S/p) for p in sorted(paths)},'yosys_summary':re.search('End of script.*',log).group(),'systemd':subprocess.check_output(['systemctl','show',unit,'-p','Result','-p','ExecMainStatus','-p','ActiveState']).decode(),'etm_tt_done':'OT_ETM_DONE_tt' in etmlog,'etm_ff_done':'OT_ETM_DONE_ff' in etmlog,'etm_hashes':{p.name:h(p) for p in O.glob('*synth_*.lib')},'macro_area':'UNKNOWN_NOT_ZERO','macro_count':80 if sub=='sfu' else 192,'stdcell_area_um2':625246.999560 if sub=='sfu' else 554850.70632}
print(json.dumps(result,indent=2))
'''
# Normalize one level of escaping in raw embedded regex.
p=subprocess.run(['ssh','ot-epyc4','python3 -'],input=code,text=True,capture_output=True,check=True)
r=json.loads(p.stdout);(A/'reused_receipts.json').write_text(json.dumps(r,indent=2)+'\n');print({k:(v['etm_tt_done'],v['etm_ff_done']) for k,v in r.items()})
