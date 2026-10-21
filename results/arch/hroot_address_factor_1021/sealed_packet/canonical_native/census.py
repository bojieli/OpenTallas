from pathlib import Path
import subprocess,json,hashlib
cmd=['python3','native_census.py','--netlist','resynth.v','--top','qkd_host_native_engine_n32','--out','native_canonical.json','--liberty','ot_sram_1r1w_32x128_m1_tt.lib']
for p in sorted(Path('libs').glob('*.lib')):cmd+=['--liberty',str(p)]
r=subprocess.run(cmd,capture_output=True,text=True);Path('native_canonical.log').write_text(r.stdout+r.stderr);print(r.stdout+r.stderr);Path('census_command.json').write_text(json.dumps({'cmd':cmd,'rc':r.returncode,'resynth_sha256':hashlib.sha256(Path('resynth.v').read_bytes()).hexdigest()},indent=2)+'\n');raise SystemExit(r.returncode)
