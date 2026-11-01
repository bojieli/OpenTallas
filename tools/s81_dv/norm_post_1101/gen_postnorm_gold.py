from pathlib import Path
import sys,json,struct,os
import numpy as np
src=Path('/srv/opentallas-scratch2/claude/wt/codex-s81b-1101');sys.path[:0]=[str(src/'tools'),str(src/'tools/s81_suhc')];os.environ['HDC_V41_ARITH']='chunk8'
import hdc_golden_v41 as V
import hc_gate as HG
V.set_arith('chunk8');F=np.float32
r=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101');out=r/'postnorm_gold_v2';out.mkdir(exist_ok=False);fx=Path('/srv/opentallas-scratch2/claude/tok-ds-2/l0prog/fix/L0')
h=np.fromfile(fx/'ops/ffn.hc_post.bin','<f4').reshape(4,5120);pre=np.fromfile(fx/'ops/ffn.hc.pre_post.bin','<f4')[:4];w=np.fromfile(r/'head_gain_source_v1/head_norm_w.f32','<f4');cfg=json.loads((Path('/srv/opentallas-scratch2/claude/ref/DeepSeek-V4.1-Flash-dba1be0a-partial/inference_config.json')).read_text());eps=F(cfg.get('norm_eps',cfg.get('model',{}).get('norm_eps')))
x=V.to_bf16(V.seqsum([V.mul(F(pre[k]),h[k])for k in range(4)]));sq=V.mul(x,x);ss=V.csum(sq);rb=V.rsqrt(V.add(V.div(F(ss),F(5120)),eps));y=HG.g_norm(h,pre,w,eps);assert np.array_equal(y.view('u4'),V.to_bf16(V.mul(w,V.mul(x,F(rb)))).view('u4'))
q=HG.g_quant(y);qword=0
for k in range(2):
 e,codes=q[k];qw=int.from_bytes(bytes(np.asarray(codes,np.uint8)),'little');qword|=qw<<(266*k);qword|=(int(e)&1023)<<(266*k+256)
bword=sum(int(v)>>16<<(16*j)for j,v in enumerate(y[:64].view('u4')));bp=V.csum(sq[:64]);ub=lambda v:int(np.asarray(v,F).view('u4'))
(out/'gold.json').write_text(json.dumps(dict(scope='released L0 FFN POST output plus released HEADnorm gains; local component golden, NOT actual final-layer residency',rstd=f'{ub(rb):08x}',partial=f'{ub(bp):08x}',eps=f'{ub(eps):08x}',Q_payload=f'{qword:0133x}',BF16_payload=f'{bword:0256x}',HEAD_gain_sha='aa8c04c15c0ddbf38955fa17af68fb632229ddc01d25fd76d9d9d222eb9b88d1'),indent=1)+'\n');(out/'.keep').write_text('nativePOSTnorm localgold; no finaltokenauthority\n');print('POSTNORM_GOLD',f'{ub(bp):08x}',f'{ub(rb):08x}')
