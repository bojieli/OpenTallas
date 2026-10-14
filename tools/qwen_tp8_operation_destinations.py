#!/usr/bin/env python3
"""Source-derived complete committed destination catalog; no arithmetic results."""
import argparse,json,hashlib
from pathlib import Path
import hdc_isa as I
import hdc_program as P
import hdc_qwen_fullshape_program_w12 as FP
import hdc_qwen_fullshape_isa_w12 as ISA
from qwen_tp8_payload_fused_lower import lower_image
from qwen_tp8_native_layer_oracle import operation_destinations
class AddressOnly:
    stream=P.Machine.stream
def main():
 p=argparse.ArgumentParser();p.add_argument('--images',type=Path,required=True);p.add_argument('--layer',type=int,default=0);p.add_argument('--position',type=int,required=True);p.add_argument('--token',type=int,default=0);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 result={'scope':'SOURCE_DERIVED_COMPLETE_DESTINATIONS_NOT_RTL','layer':a.layer,'position':a.position,'ranks':{},'source_sha256':{Path(__file__).name:hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'qwen_tp8_native_layer_oracle.py':hashlib.sha256(Path(__file__).with_name('qwen_tp8_native_layer_oracle.py').read_bytes()).hexdigest()}}
 for rank in range(8):
  image=a.images/f'die{rank}';lower=lower_image(image,layer=a.layer);manifest=json.loads((image/f'layer{a.layer}_rom.json').read_text());fields=[ISA.decode_instruction(int(w,16)) for w in (image/'program.hex').read_text().split()]
  lay=FP.LayerZero(None,rank,manifest['matrix_layout']);operations={}
  with FP.program_geometry(FP.vm_map()[0]):
   dynamic=P.dyn_values(lay,token=a.token,pos=a.position)
   for pc,f in enumerate(fields):
    if f['unit']==I.UNIT_END or 11<=pc<15:continue
    target=lower['original_to_candidate_pc'][11 if pc==15 else pc]
    operations[str(target)]=operation_destinations(f,dynamic,AddressOnly(),native=pc==15)
  result['ranks'][str(rank)]={'candidate_program_sha256':lower['candidate_program_sha256'],'actual_image_sha256':manifest['image_sha256'],'operations':operations}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
 print('Source-derived complete destination catalog8ranks/22nonENDops; no RTL verdict')
if __name__=='__main__':main()
