from pathlib import Path
import subprocess,json,time
R=Path(__file__).resolve().parent
book=json.loads((R/'fixed_booking.json').read_text());assert book['first_capture_label']==7272 and book['second_capture_label']==11368 and book['source_launch_shift']==3920
rows=[]
for name,extra,needle in [('positive',[],'NATIVE_RELOAD_PASS jobs=2 host=1061 V=252 resets=1 faults=0 external_KIT2'),('bad_payload',['+bad_payload'],'NATIVE_RELOAD_COMMAND_PAYLOAD'),('bad_returned_user',['+bad_kit'],'NATIVE_RELOAD_RETURN_KIT')]:
 t=time.time();cmd=[str(R/'obj/Vtb'),'+first_book=7272']+extra
 with (R/(name+'.log')).open('w')as f:p=subprocess.run(cmd,cwd=R/'fixtures',stdout=f,stderr=subprocess.STDOUT)
 s=(R/(name+'.log')).read_text()
 ok=(p.returncode==0 and needle in s and s.count('NATIVE_RELOAD_V job=')==252 and s.count('NATIVE_RELOAD_SEQ_END job=')==2 and s.count('NATIVE_RELOAD_RETURN_KIT job=')==2 and 'NATIVE_RELOAD_CONFIG_IMAGE_OK' in s)if name=='positive' else(p.returncode!=0 and ('Assertion failed' in s) and needle in s)
 rows.append(dict(case=name,rc=p.returncode,expected_outcome=ok,seconds=time.time()-t,command=cmd,summary=[x for x in s.splitlines()if any(z in x for z in ['%Fatal','NATIVE_RELOAD_PASS','NATIVE_RELOAD_KS_RX','NATIVE_RELOAD_KIT job','NATIVE_RELOAD_RETURN_KIT job','NATIVE_RELOAD_SEQ_END','NATIVE_RELOAD_CONFIG_IMAGE_OK'])]))
 result=dict(verdict='PASS'if len(rows)==3 and all(x['expected_outcome']for x in rows)else'FAIL_OR_INCOMPLETE',rows=rows,scope='actual compiled jobs1+2 through real PMA/LEP→SEQHOST, full54 real KIT return before no-reset reload',source_book=book,bootstrap_words=35,extra_MC_replay_adopted=False,whole_array_simulated=False,layer_retirement_qualified=False,current_wc1_adopted=False,physical_activation=False,RTL_pin_cycle_delta=0)
 (R/'final_result.json').write_text(json.dumps(result,indent=2)+'\n');print(name,p.returncode,ok,flush=True)
 if not ok:raise SystemExit(2)
