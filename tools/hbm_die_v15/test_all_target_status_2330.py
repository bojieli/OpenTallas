#!/usr/bin/env python3
"""Exercise the actual63 target ids from v16 spec, every readiness/active/fault and two mutants."""
import json, pathlib, subprocess, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
s=json.loads((ROOT/'tools/hbm_die_v15/v16_specs/cp2.json').read_text())
p=next(i['params'] for i in s['instances'] if i['name']=='host_status')
assert (p['NT'],p['NF'])==(67,100)
# Every bit of the actual root is driven once, and the ingress accepts exactly these ids.
for port,width in [('t_ready',p['NT']),('t_active',p['NT']),('t_fault',p['NF'])]:
    bits=[]
    for edge in s['edges']:
        if edge['dst'][:2]==['host_status',port]: bits.extend(range(*edge['dst'][2:]))
    assert sorted(bits)==list(range(width)), (port, bits)
ids=[(int(p['TGTS'].split("'h")[1],16)>>(8*k))&255 for k in range(p['NT'])]
h=json.loads((ROOT/'tools/hbm_die_v15/v16_specs/host_misc.json').read_text())
mask=next(i['params']['TARGET_MASK'] for i in h['instances'] if i['name']=='host_cp_ingress')
assert int(mask.split("'h")[1],16)==sum(1<<t for t in ids)
assert len(set(ids))==p['NT']

with tempfile.TemporaryDirectory(prefix='hbm-status-') as td:
    d=pathlib.Path(td);(d/'all_targets.svh').write_text(f"localparam integer NT={p['NT']},NF={p['NF']};\nlocalparam [NT*8-1:0] TGTS={p['TGTS']};\n")
    for m in (0,1,2):
        subprocess.run(['iverilog','-g2012','-I'+td,'-Ptb_hbm_all_target_status.MUT='+str(m),'-s','tb_hbm_all_target_status','-o',str(d/'sim'),
            str(ROOT/'rtl/hbm_accel/host_static_20261015/ot_hbm_status_join.sv'),
            str(ROOT/'rtl/hbm_accel/host_static_20261015/tb_hbm_all_target_status.sv')],check=True)
        r=subprocess.run(['vvp',str(d/'sim')],capture_output=True,text=True)
        print(f'MUT{m} rc={r.returncode}: {r.stdout.strip()}')
        assert (r.returncode==0 and 'ALL_TARGET_STATUS PASS' in r.stdout) if m==0 else (r.returncode!=0 and 'FATAL:' in r.stdout)
print('ALL_TARGET_STATUS_GATE PASS')
