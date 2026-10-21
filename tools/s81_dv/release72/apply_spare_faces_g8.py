#!/usr/bin/env python3
"""Declare unused fanout faces for the selected72 direct-to-frame topology.

Frame xo/xok forwards the incoming X word and clock to another frame; no arithmetic
result uses these ports. This plan feeds X chains from slices; the final frame in each
chain has no consumer for its forwarded copy. Intermediate frames remain wired. Slice xc is four identical registered xw4 copies;
only physically built branches are consumed. Never exempt a linked output.
"""
import hashlib, json, re, subprocess, sys
from pathlib import Path
p=Path(sys.argv[1]); t=json.loads(p.read_text()); plan=json.loads(Path(sys.argv[2]).read_text())
root=Path(__file__).resolve().parents[3]
sl=(root/'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv').read_text()
assert re.search(r'for \(c = 0; c < 4; c = c \+ 1\)',sl)
assert '.d(xw4), .q(xc[1104 * c +: 1104])' in sl
# The index-query wrapper alters only bo/iq; its entire xc vector is the
# existing base slice output. Keep this check exact before applying the same
# unused registered-fanout-face declaration to this one additional master.
iq=(root/'rtl/dsrom_sys/s81_dv/idx/dsdv_idx_bsplit.sv').read_text()
iq_body=iq.split('module ot_s81sl_slice_iq #(',1)[1].split('endmodule',1)[0]
assert iq_body.count('ot_s81sl_slice #(')==1
assert iq_body.count('.xc(xc)')==1
assert not re.search(r'\bassign\s+xc\b|\.xc\s*\((?!xc\))',iq_body)
assert 'output wire [4*1104-1:0] xc' in iq_body
frames={b['name']:b for b in plan['blocks'] if b['master'] in ('col_h9','col_h9_MX','col_h10')}
assert len(frames)==72
incoming={}
for l in plan['links']:
 a,pa=l['e'][0][:2]; b,pb=l['e'][1][:2]
 an,bn=plan['blocks'][a]['name'],plan['blocks'][b]['name']
 if bn in frames and pb=='x':
  lane=int(re.search(r'_l([0-3])$',l['i']).group(1))
  assert (bn,lane) not in incoming, (bn,lane)
  am=t['masters'][plan['blocks'][a]['master']]
  mapped=am['ports'].get(pa+'.o',{}).get('port')
  assert (an.startswith('s_') and mapped=='xc') or (an in frames and mapped=='xo'), l['i']
  incoming[bn,lane]=an
for frame in frames:
 for lane in range(4):
  cur=frame; seen=set()
  while cur in frames:
   assert cur not in seen, ('frame X cycle',frame,lane)
   seen.add(cur);cur=incoming[cur,lane]
  assert cur.startswith('s_'), (frame,lane,cur)
ref=t['frame_lp_binding']['source_ref']; proofs=[]
for h in (9,10):
 path=f'rtl/dsrom_sys/s81_dv/frame_lp/col_h{h}_l4_lp_rf3r.sv'
 src=subprocess.check_output(['git','show',f'{ref}:{path}'],text=True)
 for k in range(4):
  line=next(x for x in src.splitlines() if f' u_xo{k} ' in x)
  assert f'.ck(xk[{k}])' in line and f'.ck_o(xok[{k}])' in line
  assert re.findall(r'x\[(\d+)\]',line)==[str(i) for i in range(276*(k+1)-1,276*k-1,-1)]
  assert re.findall(r'xo\[(\d+)\]',line)==[str(i) for i in range(276*(k+1)-1,276*k-1,-1)]
 proofs.append(dict(path=path,ref=ref,sha256=hashlib.sha256(src.encode()).hexdigest()))
for key,m in t['masters'].items():
 if key in ('col_h9','col_h9_MX','col_h10'):
  ports=('xo','xok'); reason='selected72 frame X-chain end: only unlinked forwarded-copy bits have no downstream frame; source-checked u_xo0..3'
 elif m.get('module') in ('ot_s81sl_slice', 'ot_s81sl_slice_iq'):
  ports=('xc',); reason='slice xc g_xc: four identical registered xw4 copies; only built fanout faces consumed'
 else: continue
 for port in ports:
  assert port in t['rtl_widths'][m['module']], (key,port)
  m.setdefault('mode_unused',[]).append(dict(when='unlinked_out_bits',port=port,reason=reason))
t['selected72_spare_faces_g8']=dict(frame_instances=sorted(frames),frame_source_proofs=proofs,
 slice_source_sha256=hashlib.sha256(sl.encode()).hexdigest(),
 iq_wrapper_source_sha256=hashlib.sha256(iq.encode()).hexdigest(),policy='Only unlinked output bit ranges; no functional-input ties or unread waiver')
t['prune_unused_reset_leaves']=True
p.write_text(json.dumps(t,indent=1)+'\n')
print('SPARE_FACES_G8 source-checked frame-chain-end copies and slice fanout; actual linked bits remain strict')
