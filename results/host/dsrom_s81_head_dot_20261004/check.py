"""One tiny factoring check; no checkpoint, HEAD run, normalization or winner."""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import hdc_golden as G
import hdc_golden_v41 as V
import dsrom_s81_head_dot as D

# Execute the retained source ME loop, changing only the test row count 32320
# to 129. Full K5120 and chunk/tree remain unchanged; cross one batch boundary.
source=Path('dsrom_s81_l20_sim_only.py')
module=ast.parse(source.read_text())
head=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='head_chain')
loop=next(n for n in ast.walk(head) if isinstance(n,ast.For) and
          isinstance(n.target,ast.Name) and n.target.id=='begin' and
          isinstance(n.iter,ast.Call) and isinstance(n.iter.func,ast.Name) and n.iter.func.id=='range'
          and any(isinstance(call,ast.Attribute) and call.attr=='mul' for call in ast.walk(n)))
class Extent(ast.NodeTransformer):
    def visit_Constant(self,node):
        return ast.copy_location(ast.Constant(129),node) if node.value==32320 else node
loop=Extent().visit(loop)
code=compile(ast.fix_missing_locations(ast.Module(body=[loop],type_ignores=[])),str(source),'exec')
rng=np.random.default_rng(2998737)
w=G.bits(G.to_bf16(rng.standard_normal((129,D.K)).astype(G.F)))>>16
w=w.astype('<u2')
x=G.bits(G.to_bf16(rng.standard_normal(D.K).astype(G.F))).astype('<u4')
x[:8]=[0,0x80000000,0x00010000,0x80010000,0x3f800000,0xbf800000,0x3f808000,0xbf808000]
original=np.empty(129,dtype=G.F)
exec(code,dict(M=SimpleNamespace(G=G,V=V),weights=w,rank=SimpleNamespace(r=0),
               x=x.view('<f4'),logits=original,np=np))
got=D._dot_rows_u32(w,x)
assert np.array_equal(got,G.bits(original))
assert got.dtype==np.dtype('<u4') and got.shape==(129,)
# Rank slicing/ordering alone, without executing any full-rank arithmetic.
rows=np.arange(D.TP*D.ROWS,dtype=np.uint32).astype('<u2')[:,None]
full=np.broadcast_to(rows,(D.TP*D.ROWS,D.K))
for rank in range(4):
    def check_slice(weights,xn):
        assert weights.shape==(D.ROWS,D.K)
        assert int(weights[0,0])==int(rows[rank*D.ROWS,0])
        assert int(weights[-1,0])==int(rows[(rank+1)*D.ROWS-1,0])
        assert xn is x
        return np.zeros(D.ROWS,dtype='<u4')
    with patch.object(D,'_dot_rows_u32',check_slice):
        assert D.head_logits_u32(full,rank,x).shape==(D.ROWS,)
try:D._dot_rows_u32(w,x[:-1])
except ValueError:pass
else:raise AssertionError('short native XN accepted')
record=dict(verdict='PASS_TINY_SOURCE_FACTOR',scope='129 synthetic rows/full K5120 only; no HEAD inference/weights payload/native timing/winner',
            exact_uint32=True,rank_slices_0_to_3=True,short_xn_rejected=True,
            pins={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('.').glob('*.py')})
Path('result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record),flush=True)
