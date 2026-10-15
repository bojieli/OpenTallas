#!/usr/bin/env python3
"""Pin actual released Engram WKV headers and mathematical activation boundary."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAT='25631b8754f4ec295d5d6415ca85e75f38564664'
CON='a9d1fad2835d96e4c0585a150b6a9d484b9791cc'
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(commit,path):return subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)
def run(out):
 catraw=blob(CAT,'results/quality/w16_w17_checkpoint_header_catalogue_20261001/catalogue.json');conraw=blob(CON,'results/quality/w16_dsrom_engram_contract_20261001/contract.json')
 cat=json.loads(catraw);con=json.loads(conraw);records={};cache={}
 for layer in [1,14]:
  for suffix,shape,dtype in [('weight',[25600,6144],'F8_E4M3'),('scale',[800,192],'F8_E8M0')]:
   name=f'layers.{layer}.engram.wkv.{suffix}';rec=con['tensors'][name];shard=rec['shard'];hb=cat['shards'][shard]
   if shard not in cache:
    path=Path(cat['snapshot'])/shard;before=path.stat();fd=os.open(path,os.O_RDONLY)
    try:raw=os.pread(fd,hb['header_bytes'],8)
    finally:os.close(fd)
    after=path.stat();assert (before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns)
    assert sha(raw)==hb['raw_header_sha256'];cache[shard]=json.loads(raw)
   hdr=cache[shard][name];assert hdr['shape']==shape==rec['stored_shape'];assert hdr['dtype']==dtype==rec['dtype'];assert hdr['data_offsets']==rec['data_offsets']
   assert [v+8+hb['header_bytes'] for v in hdr['data_offsets']]==rec['absolute_file_offsets']
   records[name]=dict(shape=shape,dtype=dtype,shard=shard,absolute_file_offsets=rec['absolute_file_offsets'],stored_bytes=rec['stored_bytes'],header_sha256=hb['raw_header_sha256'])
 result=dict(schema='opentallas.hbm.engram.wkv_source_contract.v1',checkpoint_revision=cat['checkpoint_revision'],catalogue_commit=CAT,catalogue_sha256=sha(catraw),contract_commit=CON,contract_sha256=sha(conraw),tensors=records,
  operation=dict(N=25600,K=6144,K_blocks32=192,weight_scale_granularity=[32,32],activation='24 original rows x256 BF16, flattened in original column order; BF16 toFP32 is exact zero-extension',golden='Model.engram_layer calls linear_q(wkv,rows), quant_fp8 per32-wide K block; exact quantized dot rounded once toFP32, scaled, sequential blocks accumulated and outputBF16',expected_native_format='DeepSeek quantized activation/weight route; concrete fmt/NC/home/addresses require actual native compiler binding'),
  native_VM_home=None,native_weight96_partition=None,actual_SM_consumer_module=None,whole_token_programme=None,native_qualified=False,
  scope='Actual released tensor identity/shape/dtype and mathematical boundary only. HistoricalTP4 image views grant no native96 mapping. Header reads do not rehash or qualify full weight payload/physical SRAM/VM placement/throughput.',source_sha256={p:sha((ROOT/p).read_bytes())for p in ['tools/hdc_golden_v41.py','tools/hgi_sim/ds_native.py','tools/hbm_engram_wkv_source_contract.py']})
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();run(a.out)
