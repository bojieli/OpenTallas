#!/usr/bin/env python3
"""Actual composed ASTK physical port recut using already-published private face registers.

Native controller already contains timing/replica/AM_G_PIN=0 fixes; do not reapply old transforms.
Only incoming external fault gains the published one cycle; command and nominal token cycles unchanged.
"""
import json,re,sys,hashlib,shutil
from pathlib import Path

def emit(raw,pins,physical):
 end=raw.index('\n);')+len('\n);');body=raw[end:]
 decl={m.group(3):(m.group(1),int(m.group(2) or 0),0) for m in re.finditer(r'(input|output) wire (?:\[(\d+):0\] )?(\w+)',raw[:end])}
 base={x['name'].split('[')[0] for x in pins['pins']}
 tcs=sorted(n for n in base if n.endswith('__tc'));assert len(tcs)==4
 actualtc=re.findall(r'\bqkd_astk_zn(?:_head_p|_s)?\b[^;]+?\.tc\(([^)]+)\)',body)
 assert len(actualtc)==4,len(actualtc)
 # Every physical command port observes its exact current zone input; no inferred leaf bindings.
 for i,n in enumerate(tcs):
  decl[n]=('output',14,0)
  body+=f'\n' if False else ''
  expr=f'codex_tc_faces[{15*i} +: 15]' if physical else actualtc[i]
  body=body.replace('endmodule',f'    assign {n} = {expr};\nendmodule',1)
 # Single canonical entry clock/reset, as all native aliases are co-timed in the parent.
 for n in list(decl):
  if n.endswith('__ck'):
   body=re.sub(r'\b'+re.escape(n)+r'\[0\]', 'ck[0]',body);del decl[n]
  elif n.endswith('__rst_n'):
   body=re.sub(r'\b'+re.escape(n)+r'\[0\]', 'rst_n[0]',body);del decl[n]
 decl['ck']=('input',0,0);decl['rst_n']=('input',0,0)
 qo='u_strip_u_strip_u_ctl__qo';assert decl[qo]==('output',571,0)
 body,c=re.subn(r'\s*assign '+qo+r'\[571\] = [^;]+;', '',body);assert c==1,c
 decl[qo]=('output',570,0)
 if physical:
  # Current ctl_g0 already carries the exact private face implementations behind PORT_REGS.
  body,c=re.subn(r'(qkd_astk_ctl_s_g0 #\(\.Z_STRIDE\(4\))\)',r'\1, .PORT_REGS(1))',body);assert c==1,c
  body,c=body.replace(' m5 (',' m5 (.tc_faces(codex_tc_faces), .qo_face(codex_qo_face),',1),body.count(' m5 (');assert c==1
  body,c=re.subn(r'assign '+qo+r'\[(\d+)\] = [^;]+;',lambda m:f'assign {qo}[{m[1]}] = codex_qo_face[{m[1]}];',body);assert c==571,c
  body,c=re.subn(r'qkd_astk_fault_join m0 \(', 'qkd_astk_fault_join #(.PORT_REGS(1)) m0 (',body);assert c==1,c
  body='\n    wire [59:0] codex_tc_faces; wire [571:0] codex_qo_face;\n'+body
 # Preserve raw functional corner binding under its published static strap landing convention.
 body=re.sub(r'\bstrap_corner\b','strap_q',body)
 body='\n    (* keep *) reg [1:0] strap_q; always @(posedge ck[0]) strap_q <= strap_corner;\n'+body
 # Preserve canonical leaf hierarchy names used by existing zone/face clock grouping.
 names=['u_g_phys_fault_u_fault']+[f'u_u_strip_u_strip_g_zn_{i}_u_zn' for i in range(4)]+['u_u_strip_u_strip_u_ctl']
 for i,n in enumerate(names):
  body,c=re.subn(r'\bm'+str(i)+r'(?= \()',n,body);assert c==1,(i,c)
 assert set(decl)==base,(set(decl)-base,base-set(decl))
 header='module '+('kv3_astk' if physical else 'kv3_astk_ref')+' (\n'+',\n'.join(f'    {d} wire [{msb}:{lsb}] {n}' for n,(d,msb,lsb) in sorted(decl.items()))+'\n);'
 return header+body,decl

if __name__=='__main__':
 R=Path(sys.argv[1]);P=Path(sys.argv[2]);O=Path(sys.argv[3]);O.mkdir(parents=True,exist_ok=True)
 man=json.load(open(R/'kit_rtl.json'));sources=[Path(f) for f in man['files']]
 src=next(p for p in sources if re.search(r'^module kv3_astk \(',p.read_text(),re.M));raw=src.read_text();pins=json.load(open(P))
 for physical in [False,True]:
  s,decl=emit(raw,pins,physical);(O/('kv3_astk.sv' if physical else 'kv3_astk_ref.sv')).write_text(s)
 # Snapshot every reached parent source; retain exact bytes and omit the replaced raw master.
 files=[]
 for p in sources:
  if p==src:continue
  target=O/'deps'/p.name;target.parent.mkdir(exist_ok=True)
  if target.exists():assert target.read_bytes()==p.read_bytes()
  target.write_bytes(p.read_bytes());files.append(str(target))
 (O/'sources.json').write_text(json.dumps(dict(raw_master=str(src),raw_sha256=hashlib.sha256(raw.encode()).hexdigest(),files=files,canonical_pins=len(pins['pins']),decl=decl,command_cycles_added=0,external_fault_b_cycles_added=1),indent=1)+'\n')
 print('ASTK_CANONICAL_PORTS',len(pins['pins']),len(decl),'PRIVATE_FACE candidate generated; miter required')
