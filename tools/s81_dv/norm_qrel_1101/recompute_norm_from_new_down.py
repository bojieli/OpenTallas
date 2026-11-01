from pathlib import Path
import sys,json,hashlib,os
import numpy as np
src=Path('/srv/opentallas-scratch2/claude/wt/codex-s81b-1101');sys.path[:0]=[str(src/'tools'),str(src/'tools/s81_suhc')];os.environ['HDC_V41_ARITH']='chunk8'
import hdc_golden_v41 as V
import hc_gate as HG
V.set_arith('chunk8');F=np.float32
r=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101');inp=r/'new_down_norm_inputs';out=r/'new_down_norm_arith_v1';out.mkdir(exist_ok=False);(out/'.keep').write_text('freshactualnewdownsource arithmetic partials; no nativearrivalauthority\n')
check=json.loads((inp/'check.json').read_text());assert check['status']=='PASS_SOURCE_INPUT_ARITHMETIC'
fx=Path('/srv/opentallas-scratch2/claude/tok-ds-2/l0prog/fix/L0');meta=json.loads((fx/'meta.json').read_text());ids=[int(e)for e in meta['experts']];labels=['exp'+str(e)for e in ids]+['shared'];assert [x['expert']for x in check['cases']if x['rank']==0]==labels
raw=np.fromfile(inp/'down_source_bf16_in_fp32.u32','<u4').reshape(7,5120);assert not np.any(raw&65535)
assembled=np.zeros((7,80,64),np.uint32);seen=np.zeros_like(assembled,np.bool_);records=[]
for line in (r/'norm_assignment_104_56/word_map.jsonl').read_text().splitlines():
 m=json.loads(line);e,n=m['expert'],m['global_element'];pos=4*(m['row']-320-16*e)+m['word'];beat=5*m['sid']+m['leaf'];assert not seen[e,beat,pos];seen[e,beat,pos]=True;assembled[e,beat,pos]=raw[e,n];records.append(m)
assert seen.all()and np.array_equal(assembled.reshape(7,5120),raw)
y=np.zeros((80,64),F)
for e in range(6):y=V.add(y,assembled[e].view(F))
y=V.to_bf16(V.add(y,assembled[6].view(F))).reshape(5120)
gold_y=np.fromfile(fx/'ops/ffn.combine_allreduce.bin','<f4');assert np.array_equal(y.view('u4'),gold_y.view('u4'))
h=np.fromfile(fx/'ops/attn.hc_post.bin','<f4').reshape(4,5120);coef=np.fromfile(fx/'ops/ffn.hc.pre_post.bin','<f4');comb=np.fromfile(fx/'ops/ffn.hc.sinkhorn.bin','<f4').reshape(4,4)
post=HG.g_post(h,y,comb,coef[4:]);post_gold=np.fromfile(fx/'ops/ffn.hc_post.bin','<f4').reshape(4,5120);assert np.array_equal(post.view('u4'),post_gold.view('u4'))
x=V.to_bf16(V.seqsum([V.mul(coef[k],post[k])for k in range(4)]));sq=V.mul(x,x);partial=np.array([V.csum(sq[64*b:64*(b+1)])for b in range(80)],F)
# Exact native128-leaf add/pass tree over the freshly generated80partials.
leaf=[F(v)for v in partial]+[None]*48
while len(leaf)>1:leaf=[b if a is None else a if b is None else V.add(a,b)for a,b in zip(leaf[0::2],leaf[1::2])]
ss=F(leaf[0]);assert np.asarray(ss).view('u4')==np.asarray(V.csum(sq)).view('u4')
ck=Path('/srv/opentallas-scratch2/claude/ref/DeepSeek-V4.1-Flash-dba1be0a-partial/inference_config.json');eps=F(json.loads(ck.read_text())['norm_eps']);rb=V.rsqrt(V.add(V.div(ss,F(5120)),eps));w=np.fromfile(r/'head_gain_source_v1/head_norm_w.f32','<f4');norm=V.to_bf16(V.mul(w,V.mul(x,F(rb))))
(out/'partial80.hex').write_text(''.join(f'{int(v):08x}\n'for v in partial.view('u4')));y.view('u4').tofile(out/'combined_y.u32');post.view('u4').tofile(out/'post_h.u32');norm.view('u4').tofile(out/'norm_y.u32')
u=lambda z:f'{int(np.asarray(z,F).view("u4")):08x}'
result=dict(status='PASS_FRESH_NEW_SOURCE_ASSIGNMENT_NORM_ARITHMETIC_ONLY',source_cases=28,source_expert_rows=35840,logical_ranks=4,expert_order=labels,canonical64_groups=80,source_mapping_words=len(records),partial0=u(partial[0]),RSTD=u(rb),sum80_native_tree=u(ss),combined_matches_checkpoint=True,POST_matches_checkpoint=True,
 fresh_partial_source='new actualreleased FMat5Ksegment recomputation → actual104/56candidatewordmap → routedIDorderVS13→nativePOSTmath→canonicalVN64groups→native80partialtree',
 source_values_sha256=hashlib.sha256((inp/'down_source_bf16_in_fp32.u32').read_bytes()).hexdigest(),map_sha256=hashlib.sha256((r/'norm_assignment_104_56/word_map.jsonl').read_bytes()).hexdigest(),partial_sha256=hashlib.sha256((out/'partial80.hex').read_bytes()).hexdigest(),
 old_partial_payloads_read=False,actual_new_images_qualified=False,actual_native_CAP_RD_residency=False,actual_global_VN_epochs=False,actual_final_layer_HEAD_input=False,HOST_START_authority=False,canonical_adopted=False)
(out/'result.json').write_text(json.dumps(result,indent=1)+'\n');print(result['status'],'partial0',u(partial[0]),'RSTD',u(rb),'35840freshsourcevalues')
