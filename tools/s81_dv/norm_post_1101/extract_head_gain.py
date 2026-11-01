from pathlib import Path
import json,struct,hashlib
p=Path('/srv/opentallas-scratch2/claude/ref/DeepSeek-V4.1-Flash-dba1be0a-partial');r=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101/head_gain_source_v1');r.mkdir(exist_ok=False)
index=p/'model.safetensors.index.json';idx=json.loads(index.read_text());key='norm.weight';fn=p/idx['weight_map'][key]
with fn.open('rb')as f:
 n=struct.unpack('<Q',f.read(8))[0];header=f.read(n);rec=json.loads(header)[key];assert rec['shape']==[5120]and rec['dtype']=='BF16';lo,hi=rec['data_offsets'];f.seek(8+n+lo);raw=f.read(hi-lo)
assert len(raw)==10240
bits=[v[0]<<16 for v in struct.iter_unpack('<H',raw)];converted=struct.pack('<5120I',*bits);(r/'head_norm_w.f32').write_bytes(converted)
(r/'head_gain_leaf0.memh').write_text(''.join(f'{sum(bits[4*j+w]<<(32*w)for w in range(4)):032x}\n'for j in range(16)))
(r/'source.json').write_text(json.dumps(dict(source='released checkpoint tensor, direct byte-range extraction; no head ROM/image regeneration',checkpoint=str(p),tensor=key,shard=str(fn),dtype=rec['dtype'],shape=rec['shape'],data_offsets=rec['data_offsets'],index_sha256=hashlib.sha256(index.read_bytes()).hexdigest(),header_sha256=hashlib.sha256(header).hexdigest(),BF16_tensor_sha256=hashlib.sha256(raw).hexdigest(),FP32_gain_sha256=hashlib.sha256(converted).hexdigest(),conversion='exact BF16 bits shiftedleft16 intoFP32; no rounding',HEADG_rows=[480,495],boot_residency_qualified=False,final_POST_input_authority=False),indent=1)+'\n');(r/'.keep').write_text('released HEADnorm operand source, preserve\n')
print('RELEASED_HEAD_GAIN',r,len(bits),'FP32words',hashlib.sha256(converted).hexdigest())
