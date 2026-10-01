"""Check actual committed templates and reject corrupted encoded operands."""
import copy,gzip,json,pathlib,sys
import pytest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import w17_full_program_crom_binding as B
RECEIPT=ROOT/'results/rtl/w17_connected_token_preparation_20261001/full40_crom_bound_templates_v2.json'
@pytest.fixture(scope='module')
def record():return json.loads(RECEIPT.read_text())
@pytest.mark.parametrize('rank',range(4))
def test_all_encoded_operands_match_actual_manifest(record,rank):
 r=record['ranks'][rank];data=gzip.decompress(RECEIPT.with_name(RECEIPT.stem+f'.rank{rank}.templates.bin.gz').read_bytes())
 assert B.hashlib.sha256(data).hexdigest()==r['encoded_template_sha256']
 words=[int.from_bytes(data[i:i+256],'little') for i in range(0,len(data),256)]
 assert len(words)==r['encoded_instruction_count']==4778
 start=0
 for stage in r['stages']:
  count=stage['instruction_count'];assert B.validate_encoded(words[start:start+count],stage['bindings']);start+=count
 assert B.validate_encoded(words[start:],r['head_bindings'])
 head=next(x for x in r['head_bindings'] if x['kind']=='checkpoint_CROM')
 assert head['tensor']=='norm.weight' and head['actual_address']==503680 and head['extent_words']==5120
 assert r['bound_checkpoint_operands']==729
 assert [x['layer'] for x in r['unbound_generated_operands']]==[1,14]
 assert record['non_CROM_encoded_bits_unchanged'] and not record['full_program_executable']
@pytest.mark.parametrize('fault',['address','unit','extent'])
def test_encoded_mutants_rejected(record,fault):
 r=record['ranks'][0];data=gzip.decompress(RECEIPT.with_name(RECEIPT.stem+'.rank0.templates.bin.gz').read_bytes())
 words=[int.from_bytes(data[i:i+256],'little') for i in range(0,len(data),256)]
 binding=copy.deepcopy(next(x for x in r['stages'][0]['bindings'] if x['kind']=='checkpoint_CROM'))
 i=binding['instruction'];decoded=B.F.I.decode(words[i],full_shape=True)
 if fault=='address':decoded[binding['operand']+'_base']+=1
 elif fault=='unit':decoded['unit']=B.F.I.UNIT_ME
 else:binding['tensor_end']=binding['actual_address']
 words[i]=B.F.I.encode(full_shape=True,**decoded)
 with pytest.raises(ValueError):B.validate_encoded(words,[binding])
@pytest.mark.parametrize('fault',['image','source_manifest'])
def test_stale_archive_rejected(monkeypatch,fault):
 original=B.object_bytes
 def corrupted(path):
  raw=original(path)
  if path==('rank0.crom.bin.gz' if fault=='image' else 'source_manifest.json.gz'):
   data=bytearray(gzip.decompress(raw));data[-1]^=1;return gzip.compress(data,mtime=0)
  return raw
 monkeypatch.setattr(B,'object_bytes',corrupted)
 with pytest.raises(AssertionError):B.intake()
def test_norm_extent_mismatch_rejected():
 manifest,_=B.intake();r=copy.deepcopy(manifest['rank_images'][0]);r['constants']['layers.0.attn_norm.weight']['word_count']=5119
 b=B.BoundBuilder(0,r)
 with pytest.raises(ValueError,match='extent'):b.build_layer()
