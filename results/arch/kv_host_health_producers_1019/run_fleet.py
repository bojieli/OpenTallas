import base64,pathlib,subprocess,sys
p=pathlib.Path(__file__).parent
payload=base64.b64encode((p/'capture_checks.py').read_bytes()).decode()
runner='import base64,sys; exec(compile(base64.b64decode('+repr(payload)+'),"capture_checks.py","exec"))'
for mutant in ('','drop_on_clear','pulse_without_retention','reset_certifies_clean'):
 r=subprocess.run(['/home/ubuntu/bin/ot-run','--mem','1','--threads','1','--dir','/tmp','--','python3','-c',runner]+([mutant] if mutant else []),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (p/((mutant or 'baseline')+'.log')).write_bytes(r.stdout)
 print(mutant or 'baseline',r.returncode,r.stdout.decode()[-160:])
 assert (r.returncode==0)==(not mutant)
