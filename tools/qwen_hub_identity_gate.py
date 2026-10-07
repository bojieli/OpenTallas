#!/usr/bin/env python3
"""Minimum full-NL4 metadata gate; unchanged outputs compared to actual predecessor."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
r=Path(__file__).resolve().parents[1];base=a.baseline or r;a.out.mkdir(parents=True,exist_ok=True)
source=r/'rtl/physical/ot_qwen_die_hub_identity.sv';original=source.read_text();rows=[]
deps=[base/x for x in ['rtl/physical/ot_qwen_die_hub.sv','rtl/physical/ot_qwen_die_cdc_ch.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv']]
for name,params,expected,mut in [('enabled',{},True,None),('defaultoff',{'ENABLE_IDENTITY':0},True,None),('source_mutant',{},False,('source_q <= pick;','source_q <= pick ^ 2\'d1;')),('tag_mutant',{},False,('tag_q <= hd[pick*523 + 512 +: 11];','tag_q <= hd[pick*523 + 512 +: 11] ^ 11\'d1;')),('credits_negative',{'NEG':1},False,None)]:
    s=original if mut is None else original.replace(*mut)
    if mut is not None: assert s!=original
    variant=a.out/(name+'.sv');variant.write_text(s);exe=a.out/(name+'.vvp')
    cmd=['iverilog','-g2012','-s','tb_qwen_die_hub_identity','-o',str(exe)]+['-Ptb_qwen_die_hub_identity.'+k+'='+str(v) for k,v in params.items()]+[str(r/'rtl/test/tb_qwen_die_hub_identity.sv'),str(variant)]+[str(x) for x in deps]
    c=subprocess.run(cmd,text=True,capture_output=True);assert c.returncode==0,c.stderr
    z=subprocess.run(['vvp',str(exe)],text=True,capture_output=True);(a.out/(name+'.log')).write_text(z.stdout+z.stderr)
    ok='PASS hub' in z.stdout
    rows.append(dict(case=name,expected_pass=expected,observed_pass=ok,gate_pass=ok==expected));print(name,z.stdout.strip())
# Top-level interface must expose both new buses, including disabled elaboration.
c=subprocess.run(['iverilog','-g2012','-s','ot_qwen_die_hub_identity_top','-o',str(a.out/'top.vvp'),str(source)]+[str(x) for x in deps[1:]],text=True,capture_output=True);assert c.returncode==0,c.stderr
out=dict(pass_all=all(x['gate_pass'] for x in rows),cases=rows,source_sha256=hashlib.sha256(original.encode()).hexdigest(),predecessor_sha256=hashlib.sha256(deps[0].read_bytes()).hexdigest(),scope='Four actual native lanes with stalls and independent clock phases. Both output metadata RTL mutations rejected. Existing outputs compared edge-for-edge against actual predecessor. No physical/protection qualification.')
(a.out/'validation.json').write_text(json.dumps(out,indent=2)+'\n');assert out['pass_all']
