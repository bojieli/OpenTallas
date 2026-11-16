import sys,json,os
from pathlib import Path
R=Path(os.environ.get('QW_REPO','/srv/opentallas-scratch2/claude/tok-verify-2/repo'));sys.path.insert(0,str(R/'tools/qwen_layerbench'));os.chdir(R)
os.environ['DV2_S8DIE']='1';os.environ['DV_LOWER_VFLAGS']='-DOT_QC_SRAM_MIF -DOT_S8_CROM_ALIGN'
os.environ['DV_SU_AGES']=str(R/'results/rtl/qc_mif_native_1116/composed_base_3_1/slice_ages.json');os.environ['DV_VEC_AGES']=str(R/'results/rtl/qc_mif_native_1116/composed_base_3_1/vec_ages.json')
import dv_lower as D,dv_layer as L,dv_lower_xhead as X
assert D.SLICE_RTL=='s8' and D.ST_HOP==4
P=Path(__file__).parent;comp=json.loads((R/'results/rtl/qc_mif_native_1116/native_calendar_fix/mif1.json').read_text());ops=X.me_ops()
meta={}
for op,fam,mode in [('qkv','resid2','resid'),('o','attn','attn'),('gu','resid1','resid'),('down','silu','silu')]:
 lw,_=L.vec_family(mode,comp['ar_order'] if mode=='resid' else 'slice');ex=lw['expected']['x'];_,ea=X.x_edges(ex);f=X.dv_fields(ops[op],ea)
 for sid in range(12):
  rows={};words=[]
  for w in ex:
   owner=w['slice'];e=w['edge_e5']-4*(11-owner)+4*abs(sid-owner)
   words.append((e,w['eaddr']))
  shift=60-min(e for e,a in words);words=[(e+shift,a) for e,a in words];first=min(e for e,a in words);last=max(e for e,a in words)
  # First conservative functional point; runtime variants shift only HR dates.
  arm=first-30;go=last+50;ncy=go+X.read_span(f)+120
  for e,a in words:
   data=sum((0x4000<<16*k) for k in range(64))
   assert not rows.get(e,0)&(1<<453),(op,sid,e)
   rows[e]=rows.get(e,0)|(1<<453)|(a<<454)|(data<<478)
  rows[arm]=rows.get(arm,0)|X.hr_word(xpf72=X.pack_xpf72(f));rows[go]=rows.get(go,0)|X.hr_word(go=1,ib=X.pack_ib(f))
  name=f'{op}_s{sid}';(P/(name+'.hex')).write_text('\n'.join(f'{rows.get(i,0):0376x}' for i in range(ncy))+'\n')
  meta[name]={'op':op,'sid':sid,'first_xt':first,'last_xt':last,'arm':arm,'go':go,'ncy':ncy,'words':len(words),'fields':f}
(P/'packets.json').write_text(json.dumps(meta,indent=2)+'\n')
print('PACKETS',len(meta))
