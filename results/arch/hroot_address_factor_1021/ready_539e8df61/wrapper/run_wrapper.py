from pathlib import Path
import subprocess,json,hashlib
image='openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29';p=Path.cwd()
r=subprocess.run(['docker','run','--rm','--user','1000:1000','-v',str(p)+':/work','-w','/work',image,'bash','whole_wrapper.sh'],capture_output=True,text=True);Path('docker.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
cmd=['python3','native_census.py','--netlist','whole_wrapper.v','--top','qkd_hr_ingest_eng','--out','whole_native.json','--liberty','ot_sram_1r1w_32x128_m1_tt.lib']
for q in sorted(Path('libs').glob('*.lib')):cmd+=['--liberty',str(q)]
r=subprocess.run(cmd,capture_output=True,text=True);Path('whole_native.log').write_text(r.stdout+r.stderr);print(r.stdout+r.stderr);Path('command.json').write_text(json.dumps(dict(image=image,cmd=cmd,rc=r.returncode,source_sha256={q:hashlib.sha256(Path(q).read_bytes()).hexdigest() for q in ['qkd_host_native_engine_n32.sv','qkd_hr_ingest_eng.v','whole_wrapper.v']}),indent=2)+'\n');raise SystemExit(r.returncode)
