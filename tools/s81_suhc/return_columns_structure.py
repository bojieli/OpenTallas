#!/usr/bin/env python3
"""Actual elaborated parent/root ownership; no timing or full-token claim."""
import pathlib,argparse,subprocess,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--half',choices=['a','b'],required=True);p.add_argument('--reference',required=True);p.add_argument('--out',required=True);a=p.parse_args()
r=pathlib.Path(__file__).resolve().parents[2];o=pathlib.Path(a.out);o.mkdir(parents=True,exist_ok=True);src=r/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_return_columns.sv';top='ot_s81_hc_ctr'+a.half+'_columns'
ys='read_verilog -sv '+a.reference+' '+str(src)+'; hierarchy -top '+top+' -chparam READ_STAGE 1 -chparam CHAIN_STEP 6; proc; opt_clean; write_json '+str(o/'elaborated.json')
x=subprocess.run(['yosys','-p',ys],stdout=(o/'yosys.log').open('w'),stderr=subprocess.STDOUT)
if x.returncode:raise SystemExit('yosys failed')
d=json.loads((o/'elaborated.json').read_text());m=d['modules'][top];cells=m['cells'];assert len(cells)==4,(len(cells),list(cells))
roots=m['ports']['clk_col']['bits'];assert len(roots)==4 and len(set(roots))==4
seen=[]
for name,c in sorted(cells.items()):
 assert c['type'] in d['modules'] and not c['type'].startswith('$dff'),c
 bits=c['connections']['clk'];assert len(bits)==1 and bits[0] in roots,(name,bits,roots);seen+=bits
assert sorted(seen)==sorted(roots),(seen,roots)
assert 'clk_merge' not in m['ports']
receipt=dict(status='PASS',scope='actual Yosys hierarchy: parent contains exactly four child cells, zero local logic/FF; four distinct clock port bits each reach one actual child; not CTS/physical/completeness',top=top,params={'READ_STAGE':1,'CHAIN_STEP':6},source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),child_cells=list(sorted(cells)),clock_bits=roots)
(o/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
