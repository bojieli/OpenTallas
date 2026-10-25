#!/usr/bin/env python3
"""Prepare actual P8191 QKV inputs and all768 physical ROM masks; no simulation verdict."""
import argparse, contextlib, hashlib, json, sys
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[3]
FIX_SHA='1eacb299857342e340347bb0c28781e24e3d6103e1d7c1d436244ecedf011969'
IMAGE_SHA='8f48f3f41c02b861fba7ea5a1632b760c29b9f98bcaa4f1b757903f6070aba32'
def prepare(img,fx,out,src_root=REPO):
    fixture=fx/'L0_mat_qkv.npz'
    if hashlib.sha256(fixture.read_bytes()).hexdigest()!=FIX_SHA:raise ValueError('wrong real P8191 fixture')
    out.mkdir(parents=True,exist_ok=False);(out/'masks').mkdir()
    sys.path.insert(0,str(src_root/'rtl/test/qwen_dv/xhead'));import xt1_prep as X
    words,source=X.load_words(img)
    if source['sha256']!=IMAGE_SHA:raise ValueError('wrong TP8 pinned image')
    X.load_words=lambda path:(words,source)
    real_fixture=X.fixture(fx,'qkv');X.fixture=lambda path,name:real_fixture
    original=X.B.l6_parts;cache={}
    def parts(w,x,split):
        key=(w.shape,split)
        if key not in cache:cache[key]=original(w,x,split)
        return cache[key]
    X.B.l6_parts=parts;X.OPS={'qkv':X.OPS['qkv']}
    coverage=[];argv=sys.argv
    try:
        with (out/'prepare.log').open('w') as log,contextlib.redirect_stdout(log):
            for cid in range(48):
                p=out/f'cid{cid}';p.mkdir();(p/'masks').symlink_to('../masks',target_is_directory=True)
                sys.argv=['xt1_prep.py','--img',str(img),'--fx',str(fx),'--cid',str(cid),'--out',str(p)];X.main()
                g=json.loads((p/'gold.json').read_text())['qkv']
                if g['layout_mismatch_bytes']:raise ValueError(f'ROM layout mismatch cid{cid}')
                coverage.extend((w['block'],g['cluster_chunk_block'],w['j']) for w in g['words'])
    finally:sys.argv=argv
    if set(coverage)!={(b,c,j) for b in range(6) for c in range(8) for j in range(8)}:raise ValueError('incomplete QKV row/chunk coverage')
    z=np.load(fixture)
    for key,name in [('x','x_fp32'),('gold_y','gold_post_pc1'),('s','row_scales_fp32')]:
        (out/(name+'.hex')).write_text(''.join(f'{int(v):08x}\n' for v in z[key].astype(np.float32).view(np.uint32)))
    r=dict(schema='opentallas.qwen.native_projection_inputs.v1',fixture=str(fixture),fixture_sha256=FIX_SHA,image=str(img),image_sha256=IMAGE_SHA,clusters=48,tiles=768,qkv_rows=768,input_words=4096,row_chunk_words=len(coverage),mask_files=len(list((out/'masks').glob('*.hex'))),activation='actual PC0 X L0/P8191/token24; BF16 input beats in cid gold.json',expected='post-PC1 gold only; cluster partial sums require final row scale',scope='Input preparation and ROM layout only; actual projection/token simulation still required')
    (out/'inputs.json').write_text(json.dumps(r,indent=1)+'\n');return r
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--img',type=Path,required=True);p.add_argument('--fx',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--src-root',type=Path,default=REPO);a=p.parse_args();print(json.dumps(prepare(a.img.resolve(),a.fx.resolve(),a.out.resolve(),a.src_root.resolve())))
