"""Prepare only true pre-operation operands for native indexed-scalar replay."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/hbm_static'),str(ROOT/'tools/hgi_adapters')]
from hbm_layer_vehicle import layer_images as LI
from hbm_layer_vehicle.su_indexed_gather_2000 import lower
from su_program_inventory import decode
import su_bench as SB

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 src,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
 cases=[];scores=[];plans=[]
 for L in ('L00','L02','L14'):
  folder=src/L
  metadata=json.loads((folder/'records.json').read_text())['records']['0']
  arrays=np.load(folder/'operands.npz')
  records=LI.ds_dispatches_image(folder/'programme.json')
  selected=[(r,d,e)for r,d,e in records if r.tag.startswith('route.gather')]
  assert len(selected)==6
  for r,d,e in selected:
   raw=SB.pack_rec(d);_,_,_,desc=decode(raw)
   fx=next(x for x in metadata if x['tag']==r.tag)
   # Actual earlier input contains the complete pre-bias score window. This
   # window, not the fixture-resolved scalar A address, establishes the bounds.
   producer=[x for x in metadata if x['k']<fx['k'] and x['desc'].get('A',[None,0])[:2]==[desc['A'].base,384]][-1]
   window=dict(base=desc['A'].base,limit=desc['A'].base+384,producer=producer['tag'],
               source_receipt=f'{L}/records.json sha256:{sha(folder/"records.json")}')
   plan=lower(raw,tag=r.tag,source_window=window)
   assert plan['status']=='candidate_requires_binding' and plan['native_gather']['descriptor']['score_base']==desc['A'].base
   arr=np.asarray(arrays[producer['inputs']['A']['array']],np.uint32).reshape(-1)
   assert len(arr)==384 and hashlib.sha256(arr.tobytes()).hexdigest()==producer['inputs']['A']['sha256']
   index=int(arrays[fx['inputs']['I']['array']].reshape(-1)[0])
   actual_a=int(arrays[fx['inputs']['A']['array']].reshape(-1)[0])
   want=int(arrays[fx['outputs']['O']['array']].reshape(-1)[0])
   assert 0<=index<384 and int(arr[index])==actual_a and fx['desc']['A'][0]==desc['A'].base+index,(L,r.tag,index,int(arr[index]),actual_a,fx['desc']['A'][0],desc['A'].base)
   assert hashlib.sha256(np.asarray([index],np.uint32).tobytes()).hexdigest()==fx['inputs']['I']['sha256']
   value=0
   for v,w in [(desc['I'].base,24),(desc['A'].base,24),(window['limit'],24),(desc['O'].base,24),(index,32),(want,32)]:value=(value<<w)|v
   cases.append(f'{value:040x}')
   scores.extend(f'{int(v):08x}'for v in arr)
   plans.append(dict(layer=L,tag=r.tag,raw_dispatch=f'{raw:0550x}',candidate=plan,
       fixture_input_A_sha=fx['inputs']['A']['sha256'],fixture_input_I_sha=fx['inputs']['I']['sha256'],
       score_window_input_sha=producer['inputs']['A']['sha256'],expected_O_sha=fx['outputs']['O']['sha256'],
       programme_sha256=sha(folder/'programme.json'),fixture_metadata_sha256=sha(folder/'records.json')))
 (out/'cases.mem').write_text('\n'.join(cases)+'\n');(out/'scores.mem').write_text('\n'.join(scores)+'\n')
 (out/'plans.json').write_text(json.dumps(dict(scope='MINIMUM SOURCE COMPONENT; current die binding and live producer dates open',cases=plans),indent=2)+'\n')
 print('PREPARED',len(cases),'actual released route gathers; true384-word pre-operation score inputs; no host-resolved address in command')
if __name__=='__main__':main()
