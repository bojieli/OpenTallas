import subprocess,re,sys,json
from pathlib import Path
kind=sys.argv[1];root=Path.cwd();top='ot_s81sl_lep'+('_nh' if kind=='nh' else '')
libs=sorted(set(re.findall(r'Executing Liberty frontend: (\S+)',(root/f'native_synth_{kind}_wc4.log').read_text())))
assert libs, 'actual library list absent'
(root/f'libs_{kind}_wc4.json').write_text(json.dumps(libs,indent=2)+'\n')
args=['docker','run','--rm','-v',str(root/'src')+':/work:ro','-v',str(root)+':/run','openroad/orfs:asap7lock','python3','/work/tools/ref_tile/native_census.py','--netlist',f'/work/native_orfs_{kind}_wc4/results/asap7/{top}/base/1_2_yosys.v','--top',top,'--out',f'/run/native_{kind}_wc4.json']
for lib in libs:args+=['--liberty',lib]
p=subprocess.run(args)
sys.exit(p.returncode)
