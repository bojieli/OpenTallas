from pathlib import Path
import json,math,hashlib
out=Path(__file__).parent
for h in (9,10):
 p=Path(f'/home/ubuntu/wt/s81-frrst/physical/ref_tile/s81frame_col_h{h}_rf3rl/floorplan.json'); f=json.loads(p.read_text());blocks=f['blocks']; old={r['inst']:dict(r) for r in blocks}; placed=[]
 for r in sorted(blocks,key=lambda r:(r['y'],r['x'],r['inst'])):
  r=dict(r);pred=[]
  for q in placed:
   if min(r['x']+r['w'],q['x']+q['w'])-max(r['x'],q['x']) > -20+1e-7:
    pred.append(q)
  ymin=max([22.16]+[q['y']+q['h']+20 for q in pred]); lat=2.16 if r['master']=='ot_rom_4096x72_m8' else 43.2
  r['y']=round(math.ceil((ymin-1e-7)/lat)*lat,3);r['old_y']=old[r['inst']]['y'];r['y_delta']=round(r['y']-r['old_y'],3);r['binding_predecessor']=max(pred,key=lambda q:q['y']+q['h'])['inst'] if pred else None;placed.append(r)
 height=round(math.ceil((max(r['y']+r['h'] for r in placed)+22.16)/43.2)*43.2,3)
 record=dict(status='MODEL_ONLY_UNROUTED',source=str(p),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),width=f['die'][2],original_height=f['die'][3],proposed_height=height,rule='Fixed actual x/orientation/master/dimensions; original bottom-up order on every x-overlap plus20um channel; earliest lattice y;22.16um outer margin.',rectangles=placed)
 (out/f'h{h}.json').write_text(json.dumps(record,indent=2)+'\n');print(h,'height',height,'saved',f['die'][3]-height,'max_down/up',min(r['y_delta'] for r in placed),max(r['y_delta'] for r in placed))
