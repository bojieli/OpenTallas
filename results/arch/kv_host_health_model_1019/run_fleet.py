import base64, hashlib, pathlib, subprocess
p = pathlib.Path(__file__).parent
payload = base64.b64encode((p/'machine.py').read_bytes()).decode()
runner = "import base64,pathlib,subprocess,sys; p=pathlib.Path('/tmp/kv-host-health-model-1019');p.mkdir(exist_ok=True);f=p/'machine.py';f.write_bytes(base64.b64decode("+repr(payload)+")); rc=subprocess.run([sys.executable,str(f)]+sys.argv[1:]).returncode;sys.exit(rc)"
for mutant in ('', 'drop_health', 'admission', 'status_snapshot'):
    out = subprocess.run(['/home/ubuntu/bin/ot-run','--mem','1','--threads','1','--dir','/tmp','--','python3','-c',runner]+([mutant] if mutant else []), stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (p/((mutant or 'baseline')+'.log')).write_bytes(out.stdout)
    print(mutant or 'baseline', out.returncode, out.stdout.decode()[-120:])
    assert (out.returncode == 0) == (mutant == '')
