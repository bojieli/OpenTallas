# IDLE-S 2026-10-15: A-half mapping without -chparam (yosys 0.68 duplicate-paramod assert): specialise the column
# defaults in a source copy (COLUMN/READ_STAGE/CHAIN_STEP only; no logic edit), record hashes, run unchanged ABI synth.
from pathlib import Path
import subprocess,sys,json,hashlib,re
r=Path('/tmp/s81_return_columns_v4_1015');half=sys.argv[1];col=int(sys.argv[2]);top=f'ot_s81_hc_ctr{half}_column'
out=r/'model'/f'{half}{col}_spec';out.mkdir(parents=True,exist_ok=True)
src=r/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_return_columns.sv';t=src.read_text()
hdr=re.search(r'module\s+'+top+r'\s*#\((.*?)\)\s*\(',t,re.S);assert hdr
h=hdr.group(1);h2=re.sub(r'READ_STAGE\s*=\s*\d+','READ_STAGE = 1',h);h2=re.sub(r'CHAIN_STEP\s*=\s*\w+','CHAIN_STEP = 6',h2);h2=re.sub(r'COLUMN\s*=\s*\d+',f'COLUMN = {col}',h2)
spec=out/'ot_s81_hc_return_columns_spec.sv';spec.write_text(t[:hdr.start(1)]+h2+t[hdr.end(1):])
srcs=[r/'proof/reference.sv',spec]
(out/'source_binding.json').write_text(json.dumps({'method':'default-specialised copy (COLUMN/READ_STAGE/CHAIN_STEP) of the committed source; no logic edit','top':top,'params':{'COLUMN':col,'READ_STAGE':1,'CHAIN_STEP':6},'orig_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'sources':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in srcs}},indent=2)+'\n')
cmd=['python3','/home/ubuntu/OpenTallas/tools/run_abi3_physical.py','--view','asap7','--stages','synth','--top',top]+sum([['--source',str(p)] for p in srcs],[])+['--clock-port','clk','--clock-period-ns','0.833333','--keep-workdir',str(out/'mapped'),'--output',str(out)+'.json']
raise SystemExit(subprocess.run(cmd).returncode)
