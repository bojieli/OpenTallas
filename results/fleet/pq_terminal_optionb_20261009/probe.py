import json,subprocess,pathlib,os,copy,hashlib
root=pathlib.Path('/srv/opentallas-scratch/codex/pq-terminal-optionb-20261009');tag='r1_probe';names=[]
def many(fmt,n):
 for i in range(n):names.append(fmt.format(i=i))
many('u_sp.g_ixb[{i}].u_ix/q/ff',32);many('u_sp.g_ixq[{i}].u_ix/q/ff',8);many('u_sp.g_reg[0].g_sel[{i}].u_s/q/ff',4);many('u_sp.g_reg[0].u_rsfm/q/ff',1);many('u_sp.g_cc[{i}].u_cc/q/ff',3);many('u_sp.g_aqi[{i}].u_c/q/ff',9);many('u_sp.g_qwe[{i}].u_we/q/ff',8);many('u_sp.g_bwb[{i}].u_bwb/q/ff',16);many('u_sp.u_aoh{i}/q/ff',2);many('u_sp.g_grp[{i}].u_rep/q/ff',1)
for j in range(5):names.append('u_sp.g_reg[0].u_oh'+str(j)+'/q/ff')
many('u_sp.g_ixc[{i}].u_ix/q/ff',64)
for j in range(16):names.append('u_sp.g_aq[0].u_aq/g_s11c['+str(j)+'].u_c/q/ff')
many('u_sp.g_reg[0].g_sel[{i}].u_g/q/ff',4)
sta={'setup_tt':{'worst_slack_ps':0,'violating_d_pins':0,'errors':[]},'setup_ss':{'worst_slack_ps':-200,'violating_d_pins':12},'hold_ff':{'worst_slack_ps':0,'violating_d_pins':0,'errors':[]},'closes_signoff':False}
phy={'design':{'signal_integrity_violations':{'max_slew_violations':0,'max_cap_violations':0,'max_fanout_violations':0},'drc':0,'antenna':0,'area_um2':1}}
cases=[]
for name,expected in [('tt_ff_zero_ss_negative',0),('missing_tt',1),('negative_tt',1),('negative_ff',1),('sta_error',1),('nonfinite_tt',1),('boolean_tt',1),('slew',1),('cap',1),('fanout',1),('drc',1),('antenna',1),('missing_replica',1)]:
 d=copy.deepcopy(sta);p=copy.deepcopy(phy);ns=list(names)
 if name=='missing_tt':del d['setup_tt']
 if name=='negative_tt':d['setup_tt']['worst_slack_ps']=-0.01
 if name=='negative_ff':d['hold_ff']['worst_slack_ps']=-0.01
 if name=='sta_error':d['setup_tt']['errors']=['Tcl failed']
 if name=='nonfinite_tt':d['setup_tt']['worst_slack_ps']=float('nan')
 if name=='boolean_tt':d['setup_tt']['worst_slack_ps']=True
 if name in ['slew','cap','fanout']:p['design']['signal_integrity_violations']['max_'+name+'_violations']=1
 if name in ['drc','antenna']:p['design'][name]=1
 if name=='missing_replica':ns.pop(0)
 out=root/name;out.mkdir();(out/(tag+'_corner_sta.json')).write_text(json.dumps(d));(out/(tag+'.json')).write_text(json.dumps(p));base=out/('work_'+tag)/'orfs/results/asap7/probe/base';base.mkdir(parents=True);(base/'6_final.v').write_text(''.join('DFFHQNx1 '+n+' ();\n' for n in ns));r=subprocess.run(['python3',str(root/'terminal.py'),str(out),tag],env=dict(os.environ,OT_FS_MARGIN='1'),capture_output=True,text=True);v=json.loads((out/(tag+'_terminal.json')).read_text());assert r.returncode==expected,(name,r.stdout,r.stderr,v);cases.append({'case':name,'expected_rc':expected,'actual_rc':r.returncode,'verdict':v['verdict'],'replicas_preserved':v['replicas']['passed']})
receipt={'host':'ot-epyc1tb','helper_sha256':hashlib.sha256((root/'terminal.py').read_bytes()).hexdigest(),'cases':cases,'verdict':'PASS','policy':'TT>=0/FF>=0; negative SS sensitivity accepted; SI/DRC/antenna/replicas and missing/error/nonfinite TT fail closed'};(root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
