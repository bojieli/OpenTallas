import os,sys,json,hashlib,ast,copy,importlib.util,re
from pathlib import Path
from types import SimpleNamespace
B=Path(__file__).parent
S=Path('/srv/opentallas-scratch/claude/mu-die-qw/dv2f21g5r7af/src')
os.environ['OT_SPLIT_PHY_TALL']='1'
sys.path[:0]=[str(S/'tools'),str(S/'tools/qwen_split')]
import qwen_rom_fulldie as V
import qwen_rom_fulldie_b3r2 as G
import qwen_split
qwen_split.__path__=[str(B)]+list(qwen_split.__path__)
from qwen_split import native_static_io_bind as N
from qwen_split import fault_emit as F
geo=json.load(open(B/'io_geo.json'))
orient={'io_collective':'R0','io_ucie':'MX','io_serdes':'MX','io_serdes_1':'R0','io_serdes_2':'R0'}
ins=[V.Inst(n,v[0],*v[1:],orient[n]) for n,v in geo.items()]
ports=N.rtl_ports(N.ROOT/N.SOURCE,N.MASTER)
m=dict(insts=ins,buses=[],native_static_io_bind={},dv_io_placed=True,port_join={N.MASTER:N._aliases(ports)})
def masters(*args):
 M={};N.install_master(M,m,V.Master);return M
v=SimpleNamespace(masters=masters,port_widths=V.port_widths,EMIT_SPLIT=False)
# Reuse the exact production named-pin/fragment rectangle adapter, without
# invoking the unrelated full-die builder or changing the pinned source.
pin_source=S/'tools/qwen_kv_die/tp8b_v5.py'
tree=ast.parse(pin_source.read_text())
wrap=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_wrap')
node=next(n for n in wrap.body if isinstance(n,ast.FunctionDef) and n.name=='pin_rects')
ns=dict(base_pr=V.pin_rects,split={},v=v,join_plan=m['port_join'],VIEWS={})
exec(compile(ast.Module(body=[node],type_ignores=[]),str(pin_source),'exec'),ns)
v.pin_rects=ns['pin_rects']
selected=masters()
# Actual dv_case.apply_dv stage: fixed physical masters are selected BEFORE
# fault_emit.pre. Later port_join mutations cannot regenerate these objects.
v.masters=lambda *a:dict(selected)
old=G._pin_pos(v,m)
open_xy=old('io_collective','fault_code')
hard={'io_collective':['fault_code','transport_cdc_fault','transport_abort','transport_fault_cause']}
spec=importlib.util.spec_from_file_location('fault_emit_old',B/'fault_emit_old.py')
oldF=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldF)
old_model=copy.deepcopy(m)
oldv=SimpleNamespace(masters=lambda *a:dict(selected),port_widths=v.port_widths,pin_rects=v.pin_rects)
try:oldF.source_bit_geometry(oldv,old_model,G,hard)
except ValueError as err:
 assert 'fragment missing from master' in str(err)
 print('ORIGINAL_FROZEN_STAGE_FAILURE_REPRODUCED',str(err))
else:raise AssertionError('original fullGEN frozen-stage failure not reproduced')
M,pos,entries=F.source_bit_geometry(v,m,G,hard)
assert 'fault_code' in selected[N.MASTER].ports
assert 'flt_fault_code_0' not in selected[N.MASTER].ports
assert M[N.MASTER] is not selected[N.MASTER]
def canonical(q):
 points={}
 for name,L,r in v.pin_rects(q,1,{p:sp[1] for p,sp in q.ports.items()}):
  z=re.fullmatch(r'(.*?)(?:\[(\d+)\])?',name);p,b=z[1],int(z[2] or 0)
  real,indexes=m['port_join'][N.MASTER].get(p,(p,None))
  key=(real,indexes[b] if indexes is not None else b)
  assert key not in points,key
  points[key]=(L,tuple(r))
 return points
before=canonical(selected[N.MASTER]);after=canonical(M[N.MASTER])
assert before==after,('selected master physical pins changed',len(before),len(after))
print('FROZEN_NATIVE_PIN_RECTANGLES_UNCHANGED',len(before))

assert entries
assert all(e['port'] in M[N.MASTER].ports for e in entries)
assert 'fault_code' not in M[N.MASTER].ports
assert len({tuple(e['xy']) for e in entries})==len(entries)
assert all(abs(e['xy'][0]-1563.72)<.001 for e in entries)
for e in entries:m['buses'].append(('s_'+e['port'],'data',1,[('io_collective',e['port'])]))
# Production post freezes the selected masters before adding source wires.
v.masters=lambda *a:M
end=G._pin_pos(v,m,strict=True)
for e in entries:
 assert tuple(e['xy'])==tuple(end.bits(e['inst'],e['port'],1)[0])
 try:end(e['inst'],e['real'])
 except ValueError:pass
 else:raise AssertionError('partitioned whole port unexpectedly has geometry')
# The previous final audit maps each scalar fragment BACK to this nonexistent
# real port, silently returning the block centre in non-strict mode.
old_final=G._pin_pos(v,m)
reported=[]
for e in entries:
 alias_xy=end.bits(e['inst'],e['port'],1)[0]
 wrong_xy=old_final(e['inst'],e['real'])
 reported.append(dict(**e,old_final_centroid=list(wrong_xy),centroid_error_um=sum(abs(a-b) for a,b in zip(alias_xy,wrong_xy))))
rec=dict(source=str(S),source_sha256=hashlib.sha256((N.ROOT/N.SOURCE).read_bytes()).hexdigest(),master=N.MASTER,geometry='actual native_static_io_bind assigned source pin master, same1563.816x4157.976asr6bGEN; no closed collective view claimed',open_port_old_xy=open_xy,source_bits=len(entries),entries=reported,checks='unique exact emitted scalar bit fragments; whole port removed; strict actual endpoint preserved after buses connected; former audit centroid substitution reproduced')
v.EMIT_SPLIT=True
emitted=G._pin_pos(v,m,strict=True)
for e in entries:
 assert tuple(e['xy'])==F._source_bit_point(emitted,e)
rec['all_selected_collective_pin_rectangles_unchanged']=len(before)
rec['actual_stage']='dv_case fixed master snapshot before fault_emit.pre; original missing-fragment error reproduced, copy projection passes without changing original selected master'
rec['emission_modes']=['scalar alias fragment','real emitted numeric bit']
e=entries[0]
for bad in (SimpleNamespace(bits=lambda *a:None),
            SimpleNamespace(bits=lambda inst,p,w:[(1,2)] if p==e['port'] else [(3,4)])):
 try:F._source_bit_point(bad,e)
 except ValueError:pass
 else:raise AssertionError('missing/conflicting bit geometry accepted')
rec['negative_controls']=['missing actual bit rejected','conflicting alias vs real bit rejected']
rec['source_files_sha256']={str(p.relative_to(S)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
 [S/'tools/qwen_split/native_static_io_bind.py',S/'tools/qwen_kv_die/tp8b_v5.py',S/'tools/qwen_rom_fulldie_b3r2.py',S/'tools/qwen_rom_fulldie.py',S/N.SOURCE]}

v.EMIT_SPLIT=False
(B/'REPRO.json').write_text(json.dumps(rec,indent=2))
print('FAULT_SOURCE_BITS_PASS',len(entries),'oldopenXY',open_xy,'centroiderrors',min(e['centroid_error_um'] for e in reported),max(e['centroid_error_um'] for e in reported))
print(json.dumps(reported[:5],indent=2))
