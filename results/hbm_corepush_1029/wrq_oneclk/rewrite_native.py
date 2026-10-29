#!/usr/bin/env python3
"""Guarded native caller clock-interface rewrite for qualified WRQ one-root view.
Only the five redundant clock named-connections disappear. All nonclock named
connections and DEPTH parameters remain exact. Original source is never edited.
"""
from pathlib import Path
import argparse, hashlib, json, re
ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('clock_receipt',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
s=a.source.read_text();receipt=json.loads(a.clock_receipt.read_text())
assert hashlib.sha256(s.encode()).hexdigest()==receipt['sha256'],'source changed: refresh native clock identity receipt first'
rows={r['path']:r for r in receipt['rows'] if r['module']=='ot_hbm_sm_vm_wr_q_t_lanes4'}
assert set(rows)=={'smw_NW','smw_NE'}
clocks=['clk','clk_cal','clk_l0','clk_l1','clk_l2','clk_l3'];seen=[]
pattern=re.compile(r'(?P<head>\bot_hbm_sm_vm_wr_q_t_lanes4\s*(?:#\s*\([^;]*?\))?\s+(?P<inst>\w+)\s*\()(?P<body>.*?)(?P<tail>\n\s*\);)',re.S)
def rewrite(m):
    name=m['inst'];assert name in rows,('unexpected native writer',name)
    ports=re.findall(r'\.([A-Za-z_][A-Za-z0-9_]*)\s*\(([^()]*)\)',m['body'])
    rest=re.sub(r'\.([A-Za-z_][A-Za-z0-9_]*)\s*\(([^()]*)\)','',m['body'])
    assert not rest.replace(',','').strip(),('unsupported connection syntax',name)
    d=dict(ports);assert len(d)==len(ports)
    assert all(d[c].strip()==rows[name]['clock_reset_ports'][c] for c in clocks)
    assert len({d[c].strip() for c in clocks})==1
    assert d['rst_n'].strip()==rows[name]['clock_reset_ports']['rst_n']
    assert '.DEPTH(4)' in re.sub(r'\s+','',m['head'])
    kept=[(p,e) for p,e in ports if p not in clocks[1:]]
    assert {p:e for p,e in kept if p!='clk'}=={p:e for p,e in ports if p not in clocks}
    seen.append({'instance':name,'removed':{c:d[c] for c in clocks[1:]},'kept_clock':d['clk'],'nonclock_connections':len(kept)-1})
    return m['head']+'\n'+',\n'.join('    .'+p+'('+e+')' for p,e in kept)+m['tail']
out=pattern.sub(rewrite,s)
assert len(seen)==2 and {r['instance'] for r in seen}==set(rows)
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(out)
report={'classification':'CANDIDATE native caller for one-clock physical source profile; not adopted or elab-qualified','source_sha256':receipt['sha256'],'out_sha256':hashlib.sha256(out.encode()).hexdigest(),'rows':seen,'data_reset_parameters_changed':False,'added_cycles':0,'required':'Use physical oneclk recipe, atomic plan pin event and fresh selected-source bind'}
a.out.with_suffix('.rewrite.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report))
