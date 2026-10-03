"""Pins for the actual opt-in manifest/typed-issuer assembled source.

Constructors read the compiled feature probe; no clocks, reset, grants or native
factory enrollment. Physical RF banks retain their own rank/SM identities.
"""
from pathlib import Path
from tools.gpu_sys.canonical_qwen_installed_services import installed_scratch_pins_class
from tools.gpu_sys.canonical_qwen_transport import TransportError
PORTBOOK=Path(__file__).resolve().parents[2]/'rtl/model/qwen_hbm_manifest_factory_20261003/ports.json'

class ManifestEnclosingPins(installed_scratch_pins_class()):
 def __init__(self,reader,writer,*,portbook=PORTBOOK):
  super().__init__(reader,writer,portbook=portbook)
  if self.book.get('manifest_contract',{}).get('owner_module')!='ot_gpu_qwen_manifest_range_owner':
   raise TransportError('actual immutable manifest controller required')
  if self.get('manifest_enabled')!=1:
   raise TransportError('actual compiled manifest opt-in is disabled')
  if self.book['inventory'].get('native_TC_count')!=64:
   raise TransportError('actual existing genuine64 TC source inventory required')
