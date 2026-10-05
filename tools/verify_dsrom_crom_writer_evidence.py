"""Independent integer/struct audit of pinned CROM outputs. No checkpoint access."""
import gzip,hashlib,json,struct,subprocess
from pathlib import Path
EVIDENCE='70f73928f'
BASE='results/uarch/w11_dsrom_crom_writer_20261001/'
OUT=Path('results/quality/w16_dsrom_crom_writer_intake_20261001')
def git(c,p):return subprocess.check_output(['git','show',c+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 fullpin=subprocess.check_output(['git','rev-parse',EVIDENCE],text=True).strip()
 mraw=gzip.decompress(git(EVIDENCE,BASE+'manifest.json.gz'));m=json.loads(mraw)
 smraw=gzip.decompress(git(EVIDENCE,BASE+'source_manifest.json.gz'));sm=json.loads(smraw)
 assert sha(smraw)==m['source_manifest_sha256']=='dd123431a8f908362360d651a676760fcb716001e66d0229d772e93ed6ac340c'
 expected={}
 for k,e in sm['tensors'].items():
  raw=Path(e['path']).read_bytes();assert sha(raw)==e['sha256'] and len(raw)==e['bytes']
  dt=e['dtype'];unit=2 if dt=='BF16' else 4;assert len(raw)%unit==0
  values=list(struct.unpack('<'+('H' if unit==2 else 'I')*(len(raw)//unit),raw))
  expected[k]=[x<<16 for x in values] if dt=='BF16' else values
 old=json.loads(git('18712a57ec5f55cd99bbcbe4cc6b64027d11bd20','results/rtl/hdc_v41x_fullshape_token_selected_rom_layout.json'))['constants']
 checked=0;positives=[];images=[]
 for r in m['rank_images']:
  rank=r['rank'];image=gzip.decompress(git(EVIDENCE,BASE+f'rank{rank}.crom.bin.gz'))
  assert sha(image)==r['image_sha256'] and len(image)==r['image_bytes']==4070400
  assert r['used_words']==508800 and r['capacity_words']==524288
  previous=0
  for k,e in sorted(r['constants'].items(),key=lambda x:x[1]['base_word']):
   assert e['base_word']==previous;previous=e['end_word_exclusive'];values=expected[k]
   if k.endswith(('hc_attn_scale','hc_ffn_scale')):
    assert len(values)==3;values=[values[0]]*4+[values[1]]*4+[values[2]]*16
   if k.endswith('.attn_sink'):values=values[rank*16:(rank+1)*16]
   packed=b''.join(struct.pack('<II',x,0) for x in values)
   assert len(packed)//8==e['word_count'] and sha(packed)==e['output_slice_sha256']
   assert image[e['base_word']*8:e['end_word_exclusive']*8]==packed
   checked+=1
   if rank==0 and k.startswith('layers.0.'):
    matches=[(name,v) for name,v in old.items() if v['output_image_sha256']==sha(packed)]
    assert len(matches)==1;positives.append(dict(tensor=k,existing_name=matches[0][0],sha256=sha(packed)))
  assert previous==508800
  n=r['constants']['norm.weight'];assert n['base_word']==r['finalnorm_base_word']==503680 and n['word_count']==5120
  template=json.loads(gzip.decompress(git(EVIDENCE,BASE+f'rank{rank}.head-norm-bound-templates.json.gz')))
  normops=[x for x in template if x.get('unit')==2 and x.get('c_src')==1]
  assert len(normops)==1 and normops[0]['c_base']==503680 and normops[0]['su_nin']==5120
  images.append(dict(rank=rank,sha256=sha(image),bytes=len(image),used_words=508800,capacity_words=524288,spare_words=15488,headnorm_base=503680))
 assert checked==1636 and len(positives)==10
 result=dict(schema='opentallas.dsrom.actual-CROM-writer.independent-intake.v1',status='PASS_BITWISE_SOURCE_TO_IMAGE_INTAKE',evidence_commit=fullpin,writer_commit=subprocess.check_output(['git','rev-parse','676bdb433'],text=True).strip(),manifest_sha256=sha(mraw),source_manifest_sha256=sha(smraw),generator_sha256=sha(Path(__file__).read_bytes()),checked_tensor_rank_slices=checked,existing_L0_positive_slices=positives,rank_images=images,source_producer_binding=True,actual64bit_CROM_image_binding=True,actual_headnorm_operand_binding=True,checkpoint_reads=0,physical_allocation=False,ISA_execution=False,hardware_admission=False,fullproduct_complete=False,remaining=['RamCROMhome/port/3x64container assignment proof','full40instructionconstantbases+ISAexecution,notjustheadnormtemplates','embedding/headactualfieldimageproducer+allocator','Engramactual8scale codec andphysicalhomes'])
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'receipt.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');(OUT/'SHA256SUMS').write_text(sha((OUT/'receipt.json').read_bytes())+'  receipt.json\n')
 print(json.dumps(dict(status=result['status'],checked_slices=checked,positive_L0=len(positives))))
if __name__=='__main__':main()
