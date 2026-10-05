"""Compare retained one-pair native trace with the same released raw words/QR."""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--base', type=Path, required=True)
p.add_argument('--diagnostic', type=Path, required=True)
a = p.parse_args()
sys.path[:0] = [str(a.base/'source/tools'), str(a.base/'source')]
import hdc_golden_v41 as V
import v41_rom_ksplit_bankmap as S

d = a.diagnostic
qr = a.base/'qnorm-r2/runtime/native_L20_I13_rank0.u32'
xq, xe = V.quant_fp8(np.fromfile(qr, dtype='<f4'))
raw = {}
for line in (d/'pair15-words.txt').read_text().splitlines():
    v = list(map(int, line.split()))
    raw[v[0], v[1]] = v[2:]
fixed = {}
for line in (d/'pair15-words-fixed.txt').read_text().splitlines():
    v = list(map(int, line.split()))
    fixed[v[0], v[1]] = v[2:]
order = S.segment_order('fp8', 0, 1280)
weight = np.zeros((6, 1280), dtype=np.float64)
we = np.zeros((6, 40), dtype=np.int32)
for (bank, address), words in raw.items():
    index, j = divmod(address-160, 3)
    u,b,h = order[index]
    k = 512*u+256*h+32*b
    codes = np.frombuffer(b''.join(v.to_bytes(4,'little') for v in words[:8]), dtype=np.uint8)
    weight[2*j+bank,k:k+32] = V.E4M3[codes]
    we[2*j+bank,k//32] = words[8]-127
products = (weight*xq[None,:]).astype(np.float32).reshape(6,40,32)
blocks = V.csum(products)*np.exp2(we+xe[None,:]).astype(np.float32)
golden = V.csum(blocks.astype(np.float32)).view(np.uint32)
trace = (d/'pair15-fixed.trace.txt').read_text().splitlines()
terms = [line.split() for line in trace if line.startswith('TERM ')]
bad = []
for i,t in enumerate(terms):
    # TERM cycle tag xe we X [8 words] W [8 words]; macro0 retained p0.
    seg = (int(t[2],16)>>6)&7
    # Actual segment/half issue order comes from existing element_order.
    ps = [dict(fmt='fp8',e0=0,elems=1280,row=j*128,tensor='layers.20.attn.wq_b.weight') for j in range(3)]
    j,u,b,h = S.element_order(ps)[i]
    k = 512*u+256*h+32*b
    xs = b''.join(int(v,16).to_bytes(4,'little') for v in t[6:14])
    actual_x = V.E4M3[np.frombuffer(xs,dtype=np.uint8)]
    expected_w = fixed[0,160+i]
    if seg != j or not np.array_equal(actual_x,xq[k:k+32]) or int(t[3]) != int(xe[k//32])%1024 or int(t[4]) != (expected_w[8]-127)%1024 or [int(v,16) for v in t[15:23]] != expected_w[:8]:
        bad.append(dict(term=i,cycle=int(t[1]),segment=seg,expected_segment=j,k=k))
partials = []
for line in trace:
    if not line.startswith('PARTIAL '): continue
    t = line.split(); bank,row = int(t[2]),int(t[3]); j=row//256
    actual = int(t[6],16); expected = int(golden[2*j+bank])
    partials.append(dict(row=row,actual=f'{actual:08x}',golden=f'{expected:08x}',exact=actual==expected))
assert len(terms)==120 and len(partials)==6
record = dict(scope='one unchanged native pair15, stage37 phase20, same QR/released raw codes; no full I14/VM publication claim',
              terms=len(terms),association_mismatches=len(bad),first=bad[:1],partials=partials,
              exact=not bad and all(v['exact'] for v in partials),
              hardware_change=dict(ports=0,registers=0,words=0,edges=0),
              files={str(v):hashlib.sha256(v.read_bytes()).hexdigest() for v in [qr,d/'pair15-words.txt',d/'pair15-words-fixed.txt',d/'pair15-fixed.trace.txt',d/'pair15',d/'fixed_bridge.py']})
(d/'fixed-comparison.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
raise SystemExit(0 if record['exact'] else 1)
