"""Control-format roundtrip and real selector capacity counterexamples."""
import copy,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w11_dsrom_crom_control_catalog as C

def test_all_selector_indices_and_destination_groups_roundtrip():
 for s in range(135):
  for operand in (0,1):
   for group in (0,63):
    selectors=[s]*16;w=C.encode_fill(selectors,65535,operand,group)
    assert w<2**151 and w.to_bytes(35,'little')[-1]==0
    assert C.decode_fill(w)==dict(selectors=selectors,mask=65535,operand=operand,group=group)


def test_actual_first_gamma_burst_complete_nonaliased():
 uses=[(0,lane,1808+lane) for lane in range(1024)]
 waves=C.compile_burst(uses);assert C.verify_waves(waves,uses)
 assert max(len(w['landing']) for w in waves)==135
 seen=set()
 for wave in waves:
  for word in wave['fills']:
   f=C.decode_fill(word)
   for lane,s in enumerate(f['selectors']):
    if f['mask']>>lane&1 and s>=128:seen.add(s)
 assert seen==set(range(128,135))


@pytest.mark.parametrize('index',range(128,135))
def test_7bit_mutant_alias_detected(index):
 uses=[(0,lane,1941+lane) for lane in range(135)]
 waves=C.compile_burst(uses);bad=copy.deepcopy(waves)
 changed=False
 for wave in bad:
  for wi,word in enumerate(wave['fills']):
   f=C.decode_fill(word)
   for lane,s in enumerate(f['selectors']):
    if f['mask']>>lane&1 and s==index:
     f['selectors'][lane]=s&127;wave['fills'][wi]=C.encode_fill(**f);changed=True
 assert changed
 with pytest.raises(ValueError,match='aliased'):C.verify_waves(bad,uses)


def test_both_operand_destinations_share_source_without_lost_mask():
 uses=[(op,lane,900+lane%7) for op in (0,1) for lane in range(31)]
 waves=C.compile_burst(uses);assert C.verify_waves(waves,uses)
 assert {C.decode_fill(w)['operand'] for wave in waves for w in wave['fills']}=={0,1}
 bad=copy.deepcopy(waves);bad[0]['fills'].pop()
 with pytest.raises(ValueError,match='missing'):C.verify_waves(bad,uses)


def test_request_masks_rows_padding_and_duplicate_bank_rejected():
 addresses=[0,1,2,44*3,44*3+2,(45*4072+1)*3]
 assert C.decode_requests(C.encode_requests(addresses))==sorted(addresses)
 with pytest.raises(ValueError,match='two rows'):C.encode_requests([0,45*3])
 with pytest.raises(ValueError,match='padding'):C.decode_requests([0,0,1<<273])
 with pytest.raises(ValueError):C.decode_fill(1<<151)
 with pytest.raises(ValueError):C.decode_fill(255 | 1<<128)


@pytest.fixture(scope='module')
def actual_catalog():
 import gzip,json
 pin='3c99ce15f';prefix='results/uarch/w11_crom_control_catalog_20261001/compiled_v2/'
 m=json.loads(gzip.decompress(C.git_bytes(pin,prefix+'catalog.json.gz')))
 r=gzip.decompress(C.git_bytes(pin,prefix+'request-controls.bin.gz'))
 f=gzip.decompress(C.git_bytes(pin,prefix+'fill-controls.bin.gz'))
 return m,r,f


def test_original_immutable_catalog_passes_corrected_guard(actual_catalog):
 m,r,f=actual_catalog
 assert C.verify_serialized(m,r,f)==549760


@pytest.mark.parametrize('mutation',['pred','empty','drop','duplicate','reorder','pc','layer',
 'base','inner_stride','outer_stride','half','logical_uses','operand_axis','tensor',
 'counts','model_pin','model_sha','audit_sha','rank_sha','image_sha','rank_order','burst','wave_offset','wave_count','format'])
def test_mutable_metadata_cannot_define_expected_source(actual_catalog,mutation):
 m,r,f=actual_catalog;m=copy.deepcopy(m)
 command=m['commands'][0];operand=command['operands'][0]
 if mutation=='pred':command['pred']^=1
 elif mutation=='empty':m['commands']=[];m['counts']['coefficient_uses_per_rank']=0
 elif mutation=='drop':m['commands'].pop()
 elif mutation=='duplicate':m['commands'][-1]=copy.deepcopy(command)
 elif mutation=='reorder':m['commands'][0],m['commands'][1]=m['commands'][1],m['commands'][0]
 elif mutation=='pc':command['pc']+=1
 elif mutation=='layer':command['layer']=1
 elif mutation=='base':operand['base']+=1
 elif mutation=='inner_stride':operand['inner_stride']+=1
 elif mutation=='outer_stride':operand['outer_stride']+=1
 elif mutation=='half':operand['half_inner']=not operand['half_inner']
 elif mutation=='logical_uses':operand['logical_uses']=0
 elif mutation=='operand_axis':operand['operand']='d'
 elif mutation=='tensor':operand['tensor']='norm.weight'
 elif mutation=='counts':m['counts']['bank_waves']-=1
 elif mutation=='model_pin':m['model_source']['commit']='bc1ec8b8f'
 elif mutation=='model_sha':m['model_source']['sha256']='0'*64
 elif mutation=='audit_sha':m['encoded_program_source']['sha256']='0'*64
 elif mutation=='rank_sha':m['rank_program_image_bindings'][0]['encoded_template_sha256']='0'*64
 elif mutation=='image_sha':m['rank_program_image_bindings'][0]['CROM_image_sha256']='0'*64
 elif mutation=='rank_order':m['rank_program_image_bindings'].reverse()
 elif mutation=='burst':command['bursts'][0]['burst']=1
 elif mutation=='wave_offset':command['bursts'][0]['waves'][0]['fill_start_word']=1
 elif mutation=='wave_count':command['bursts'][0]['waves'].pop()
 elif mutation=='format':m['format']['fill_fields']='16x7bitselectors'
 with pytest.raises(ValueError,match='source binding'):C.verify_serialized(m,r,f)
