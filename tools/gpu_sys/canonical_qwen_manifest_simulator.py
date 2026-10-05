"""Pins for the actual opt-in manifest/typed-issuer assembled source.

Constructors read the compiled feature probe; no clocks, reset, grants or native
factory enrollment. Physical RF banks retain their own rank/SM identities.
"""
from pathlib import Path
from tools.gpu_sys.canonical_qwen_installed_services import installed_scratch_pins_class
from tools.gpu_sys.canonical_qwen_transport import TransportError
PORTBOOK=Path(__file__).resolve().parents[2]/'rtl/model/qwen_hbm_manifest_factory_20261003/ports.json'

def validate_manifest_book(book):
 contract=book.get('manifest_contract',{})
 owner=contract.get('owner_module')
 if owner not in ('ot_gpu_qwen_manifest_range_owner','ot_gpu_qwen_banked_manifest_range_owner','ot_gpu_qwen_native_aperture_range_owner') or contract.get('issuer_module')!='ot_gpu_qwen_full_issuer_r3':
  raise TransportError('actual manifest owner/typed issuer namespace')
 if owner in ('ot_gpu_qwen_banked_manifest_range_owner','ot_gpu_qwen_native_aperture_range_owner'):
  for name in ('required_bank_mask64','required_input_bank_mask64','required_output_bank_mask64'):
   p=book.get('pins',{}).get('source_owner_'+name,{})
   if not (p.get('direction')=='output' and p.get('leaf_bits')==64 and p.get('count')==64 and p.get('bits')==4096 and p.get('block')=='source_owner' and p.get('leaf')==name):
    raise TransportError('actual banked manifest mask64 port '+name)
 return owner

class ManifestEnclosingPins(installed_scratch_pins_class()):
 def __init__(self,reader,writer,*,portbook=PORTBOOK):
  super().__init__(reader,writer,portbook=portbook)
  validate_manifest_book(self.book)
  if self.get('manifest_enabled')!=1:
   raise TransportError('actual compiled manifest opt-in is disabled')
  if self.book['inventory'].get('native_TC_count')!=64:
   raise TransportError('actual existing genuine64 TC source inventory required')
