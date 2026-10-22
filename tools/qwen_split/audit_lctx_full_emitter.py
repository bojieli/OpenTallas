#!/usr/bin/env python3
"""Independent whole-instance/alias audit of emitted RTL against proved graph."""
import argparse,hashlib,json,re,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--graph',required=True);p.add_argument('--source',required=True);p.add_argument('--helpers',required=True);a=p.parse_args()
d=json.loads(Path(a.graph).read_text());g=d['graph'];s=Path(a.source).read_text();h=Path(a.helpers).read_text()
with tempfile.TemporaryDirectory() as td:
 pp=Path(td)/'pre.sv';subprocess.run(['iverilog','-g2012','-DSYNTHESIS','-E','-o',str(pp),a.source],check=True);s=pp.read_text()
def bit(b):return 'n_'+str(b) if isinstance(b,int) else "1'b"+b
def bus(bs):return bit(bs[0]) if len(bs)==1 else '{'+','.join(bit(b) for b in reversed(bs))+'}'
def canon(s):return re.sub(r'\s+','',s)
inst={int(i):(mod,int(pid),dict(re.findall(r'\.(\w+)\(([^()]*)\)',body))) for mod,pid,i,body in re.findall(r'(qfd_lctx_full32_\w+)\s+#\(\.ID\((\d+)\)\)\s+u_(\d+)\(([^;]+)\);',s)}
mac={int(i):dict(re.findall(r'\.(\w+)\(([^()]*)\)',body)) for i,body in re.findall(r'ot_rom_4096x72_m8\s+hard_rom_(\d+)\(([^;]+)\);',s)}
used=set()
for i,(name,c) in enumerate(g['cells'].items()):
 expected={p:bus(bs) for p,bs in c['connections'].items()}
 if c['type']=='ot_rom_4096x72_m8':assert mac[i]==expected,(i,name);continue
 mod,pid,pins=inst[i];want='qfd_lctx_full32_'+c['type'].strip('$_').lower()
 assert mod==want and pid==i and pins==expected,(i,name,mod,want);used.add(mod)
assert len(inst)+len(mac)==len(g['cells']) and len(mac)==3
aliases=0
for name,p in g['ports'].items():
 equation=('assign '+bus(p['bits'])+' = '+name+';') if p['direction']=='input' else ('assign '+name+' = '+bus(p['bits'])+';')
 assert canon(equation) in canon(s),name;aliases+=1
truth={
 'and':'assignY=A&B;', 'or':'assignY=A|B;', 'xor':'assignY=A^B;', 'not':'assignY=~A;', 'mux':'assignY=S?B:A;',
 'dff_p':'always@(posedgeC)Q<=D;',
 'dff_pn0':"always@(posedgeCornegedgeR)if(!R)Q<=1'b0;elseQ<=D;",
 'dff_pn1':"always@(posedgeCornegedgeR)if(!R)Q<=1'b1;elseQ<=D;",
 'sdff_pp0':"always@(posedgeC)if(R)Q<=1'b0;elseQ<=D;",
}
for mod in used:
 body=re.search(r'module\s+'+re.escape(mod)+r'\b(.*?)endmodule',h,re.S)[1];kind=mod.removeprefix('qfd_lctx_full32_');assert kind in truth
 expected=truth[kind];actual=canon(body);logic=actual[actual.index('always@'):] if 'always@' in actual else actual[actual.index('assignY='):]
 assert logic==expected,(mod,logic,expected)
print(json.dumps(dict(status='PASS',scope='All emitted generic cell/macro connections, complete external aliases and actual helper truth tables match the separately proved graph; no startup/ROM-content/physical claim',cell_instances=len(inst),rom_instances=len(mac),external_port_aliases=aliases,helper_types=len(used),source_sha256=hashlib.sha256(Path(a.source).read_bytes()).hexdigest(),helpers_sha256=hashlib.sha256(Path(a.helpers).read_bytes()).hexdigest()),indent=2))
