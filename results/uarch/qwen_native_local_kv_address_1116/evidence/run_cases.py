#!/usr/bin/env python3
"""11-case LOCAL_DIM_INPUT formatter check. usage: run_cases.py FORMATTER_SV OUTDIR (iverilog). Writes verdict.json."""
import json,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;fmt=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
C=json.load(open(H/'cases.json'));gold=json.load(open(H/'golden256.json'))['word512_hex_msb_first'];res={}
for c in C:
    x=out/'x.vvp'
    subprocess.run(['iverilog','-g2012','-s','tb',f"-Ptb.LOCALMODE={c['mode']}",'-o',str(x),str(H/'tb.sv'),str(fmt)],check=True)
    o=out/(c['name']+'.out');subprocess.run(['vvp',str(x),f"+INPUT={H/c['name']/'stim.hex'}",f"+OUTPUT={o}"],check=True,capture_output=True,timeout=300)
    L=o.read_text().splitlines();w=[l.split()[3] for l in L if l.startswith('WORD')];f=[l for l in L if l.startswith('FAULT')]
    st='PASS' if (w==gold and not f) else 'FAULT' if (f and not w) else 'TYPED_DATA_FAIL' if (len(w)==4 and w!=gold and not f) else 'OTHER'
    res[c['name']]=dict(expect=c['expect'],got=st,ok=st==c['expect'])
v=dict(all_ok=all(r['ok'] for r in res.values()),cases=res);(out/'verdict.json').write_text(json.dumps(v,indent=1)+'\n');print('FORMATTER_11CASE','PASS' if v['all_ok'] else 'FAIL',sum(r['ok'] for r in res.values()),'/',len(res))
sys.exit(0 if v['all_ok'] else 1)
