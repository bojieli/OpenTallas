"""Controlled production-shape service inputs, using the actual numerical golden.
Not a released-model fixture or token pass. Used to calibrate real source dates.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 repo=Path(__file__).resolve().parents[3];sys.path.insert(0,str(repo/'tools'))
 import rtl_hdc_v41x_attn_campaign as C
 V=C.V;V.set_arith('chunk8');r=np.random.default_rng(53712316);f=a.out;f.mkdir(parents=True,exist_ok=False)
 rows=V.to_bf16(r.normal(0,.125,(128,512)).astype(np.float32));q=V.to_bf16(r.normal(0,.03125,(16,512)).astype(np.float32))
 codes,scales=zip(*[C.fp8_row_codes(x)for x in rows]);codes=np.asarray(codes,dtype=np.uint8);scales=np.asarray(scales,dtype=np.uint8)
 job=C.Job(q,np.zeros(128,np.int64),codes.astype(np.int64),scales.astype(np.int64),np.zeros((16,128),np.float32),'controlled service')
 kvm=job.kvm();scale=np.float32(512**-.5);sc=V.mul(V.dots(q,kvm),scale);m=np.max(sc,axis=1)
 e=V.exp(V.add(sc,V.neg(m)[:,None]));pv=V.dots(V.to_bf16(e),kvm.T)
 sinkw=np.zeros(16,np.float32);sink=V.exp(V.add(sinkw,V.neg(m)));den=V.add(V.reduce_rows(e),sink)
 norm=V.to_bf16(V.div(pv,den[:,None]));cfg=json.loads((repo/'compiler/models/deepseek-v4.1-flash/inference_config.json').read_text())
 fr=V.rope_freqs(cfg['rope_head_dim'],0,cfg['rope_theta'],cfg['rope_factor'],cfg['beta_fast'],cfg['beta_slow']);unrope=V.rope_tail(norm,V.rope_cs(fr,128),inverse=True)
 files={};ops={}
 def write(name,data,table,key=None):
  data=np.asarray(data);p=f/name;p.parent.mkdir(parents=True,exist_ok=True);data.tofile(p)
  table[key or name]=dict(dtype=str(data.dtype),shape=list(data.shape),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
 write('state/kv.window.codes.bin',codes[:127],files);write('state/kv.window.scale.bin',scales[:127,::2],files)
 write('weights/attn_sink.bin',sinkw,files);files['weights/attn_sink.bin']['rows']=[0,16]
 for n,v in [('attn.own_row_write',rows[-1]),('attn.q_rope',q),('attn.window_load',kvm),('attn.scores',sc),('attn.exp',e),('attn.pv',pv),('attn.sink',sink),('attn.normalize',norm),('attn.normalize.unrope',unrope)]:write('ops/'+n+'.bin',v,ops,n)
 meta=dict(kind='sliding',rank=0,tp_split={'heads':[[0,16]]},position=128,layer_index=0,attn_scale=float(scale),scope=__doc__,sources={n:hashlib.sha256((repo/n).read_bytes()).hexdigest()for n in ['tools/hdc_golden_v41.py','tools/hdc_golden.py','compiler/models/deepseek-v4.1-flash/inference_config.json']})
 for name,data in [('files',files),('ops',ops),('meta',meta)]:(f/(name+'.json')).write_text(json.dumps(data,indent=1)+'\n')
 print(f)
if __name__=='__main__':main()
