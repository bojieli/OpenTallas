"""Source-derived cold prefix CANDIDATE; epoch origin stays unbound until GI/face/die join.
No RTL or production image is selected by this model.
"""
import argparse,json,re,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"qwen_split"))
import d2d_link_calendar as L
CALS=("C_tx","C_rx","K_tx","K_rx")

def unpack_admission(text,name):
 v=int(re.search(r"OVL_"+name+r"_IMG = 1024'h([0-9a-f]+)",text).group(1),16)
 words=[]
 for a in range(16,32):
  x=(v>>(32*a))&0xffffffff;words.append(x)
  if x&(1<<17):return words
 raise ValueError('unterminated admission')
def events(words):
 t=0;out=[]
 for x in words:
  t+=x>>18
  for i in range((x&31)+1):out.append((t+i,(x>>14)&7,(x>>10)&15,((x>>5)&31)+i))
  t+=x&31
 return out

def build(root,out):
 text=(root/'rtl/qwen_sys/d2d_static_20261015/ovl_release/ovl_release_img.svh').read_text()
 old={c:unpack_admission(text,c.upper()) for c in CALS}
 txd={'C':[8,3,1,10],'K':[22,4,3,3]}
 msgs=[dict(src=c[0],cyc=t,tx_port=p,rx_port=p,kind=k,beat=b) for c in ['C_tx','K_tx'] for t,p,k,b in events(old[c])]
 imgs,tab=L.compile_seg(msgs,6,7,0,txd)
 assert imgs==old,('source admission decode mismatch',imgs,old)
 context_send=max(max(x['rx_out'],x['cyc']) for x in tab)+4
 msgs.append(dict(src='K',cyc=context_send,tx_port=1,rx_port=1,kind=12,beat=0))
 imgs,tab=L.compile_seg(msgs,6,7,0,txd)
 assert all(len(v)<=16 for v in imgs.values())
 adm_len=max(max(x['rx_out'],x['cyc']) for x in tab)+4
 headmsgs=[dict(src='K',cyc=2,tx_port=1,rx_port=1,kind=12,beat=1),dict(src='K',cyc=3,tx_port=1,rx_port=1,kind=12,beat=0),dict(src='K',cyc=191,tx_port=2,rx_port=2,kind=8,beat=0)]
 headmsgs += [dict(src='K',cyc=192+i,tx_port=2,rx_port=2,kind=6+i//32,beat=i%32)for i in range(64)]
 _,htab=L.compile_seg(headmsgs,6,7,0,txd)
 heads={}
 for c in ['K_tx','C_rx']:
  ev=[(x['cyc'] if c=='K_tx' else x['arrive'],x['tx_port'] if c=='K_tx' else x['rx_port'],x['kind'],x['beat'])for x in htab]
  ev.sort();start=ev[0][0]-1
  heads[c]=dict(start=start,occ=(start,ev[-1][0]+1),events=len(ev),img=L.image([(t-start,p,k,b)for t,p,k,b in ev]))
 prefix={c:{'start_relative_GI_raw_INIT':63+d['start'],'last_relative_GI_raw_INIT':63+d['occ'][1]-1,'events':d['events'],'image':d['img']}for c,d in heads.items()}
 result=dict(schema='opentallas.qwen.cold-prefix-candidate.v1',production_bound=False,
 blockers=['FACE-to-GI raw DH transport/clock age unbound','actual embedding row producer/provider/consumer join pending','final programme store ABI/image capacity pending','absolute epoch origin unbound'],
 source_sha256=hashlib.sha256(text.encode()).hexdigest(),old_admission=old,new_admission=imgs,admission_table=tab,
 admission_ofs=72,new_admission_len=adm_len,min_same_reference_prefix_start=72+adm_len+4,
 measured_GI_relative={'INIT':0,'cal_accept':1,'emb_start':63,'first_L0_raw_pin':334},cold_head_prefix=prefix,
 context_policy='explicit user0 CONTEXT after existing WITNESS receive+4; actualhostreceiver stillvalidates fullidentity',
 steady_period=8053632,steady_runtime_delta_edges=0,wrap_policy='constant per-list WRAP_BASE skips prefix, halt/reload rewinds0',
 structural_cost='same2x4096x72 listROM,<=1extra listword/direction; +constantwrap mux; newctx129output; resetfamilies<=32 planned')
 out.mkdir(parents=True,exist_ok=True);(out/'candidate.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.root,a.out)
