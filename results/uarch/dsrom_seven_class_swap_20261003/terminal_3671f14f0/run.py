import subprocess,pathlib,json,time,hashlib,os
s=pathlib.Path('/tmp/ds-seven-class-3671f14f0-source');r=pathlib.Path(__file__).parent
rec={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=s,text=True).strip(),'pid':os.getpid(),'host':os.uname().nodename,'scope':'raw seven-class boundary bank, not full parent/protected/physical','status':'RUNNING','sources':{}}
files=['results/uarch/dsrom_seven_class_swap_20261003/inputs/ratio_fifo.sv','rtl/model_ready_ds_seven_class_20261003/ot_ds_owned_ratio_boundary.sv','rtl/model_ready_ds_seven_class_20261003/ot_ds_seven_class_boundary_bank.sv','tests/rtl/dsrom_seven_class/tb.sv']
for f in files:rec['sources'][f]=hashlib.sha256((s/f).read_bytes()).hexdigest()
(r/'versions.log').write_text(subprocess.run(['iverilog','-V'],capture_output=True,text=True).stdout+subprocess.run(['vvp','-V'],capture_output=True,text=True).stderr)
(r/'headroom.log').write_text(subprocess.check_output(['free','-m'],text=True)+subprocess.check_output(['df','-h',str(r)],text=True)+pathlib.Path('/proc/loadavg').read_text())
def save():(r/'record.json').write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n')
save()
cmd=['iverilog','-g2012','-s','tb','-o',str(r/'gate.vvp')]+[str(s/f) for f in files]
for label,c in [('compile',cmd),('simulation',['vvp',str(r/'gate.vvp')])]:
 start=time.time()
 with (r/(label+'.log')).open('w') as log:p=subprocess.run(['/usr/bin/time','-v','-o',str(r/(label+'.resources'))]+c,stdout=log,stderr=subprocess.STDOUT,cwd=s)
 rec[label]={'command':c,'exit_code':p.returncode,'elapsed_s':time.time()-start};save()
 if p.returncode:rec['status']='FIRST_FAILURE_'+label.upper();save();raise SystemExit(p.returncode)
rec['status']='PASS_RAW_BOUNDARY_ONLY' if 'PASS DS_SEVEN_CLASS_RAW_COMPOSED classes=7 planes=14 cases=58 reset_debt_preserved=1' in (r/'simulation.log').read_text() else 'TERMINAL_MARKER_MISMATCH'
rec['terminal']=(r/'simulation.log').read_text();save();print(json.dumps(rec,indent=2))
