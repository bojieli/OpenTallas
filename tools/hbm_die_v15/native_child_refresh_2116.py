import json,hashlib,re
from pathlib import Path
R=Path(__file__).resolve().parents[2]; p=R/'results/arch/hier_contract_1015/hbm_v15.json';g=json.loads(p.read_text());S={s['name']:s for s in g['slots']}
def binding(view,master,source):
 d=R/view
 files=[master+'.lef',master+'_tt.lib',master+'_ff.lib','insertion.json']
 return dict(view=view,cell=master,source=source,source_sha256=hashlib.sha256((R/source).read_bytes()).hexdigest(),view_files_sha256={n:hashlib.sha256((d/n).read_bytes()).hexdigest() for n in files},qualified_scope='native-qualified child only; parent incident paths, clocks and die timing remain OPEN')
ck=S['hb_ckgen']; ck['children']=[dict(inst='u_pll',cell='ot_hbm_pll_bb',view='physical/hbm_pll_views/ot_hbm_pll_bb',at=[43.2,23.76],outline=dict(w=172.8,h=172.8),qualification='allowed analog PHY/PLL abstract'),dict(inst='u_rel',at=[0,23.76],outline=dict(w=21.6,h=21.6),**binding('physical/ref_tile/hbm_ckgen_rel4/views/hfd_ckgen_rel4','hfd_ckgen_rel4','rtl/hbm_accel/control/hfd_ckgen.sv'))]
ck['child_binding_refresh_2116']='Actual hfd_ckgen u_rel is ONE hfd_ckgen_rel4, replacing stale u_rel0..3 grant. Leaf west of PLL W-edge pins with 21.6 um gap; existing parent outline and ports unchanged.'
ck['parent_qualified']=False
for q in ('SW','SE','NW','NE'):
 s=S['hb_dbk_'+q]
 for b in range(8):
  c=s['children'][b];c['inst']=f'L[{b}].u_bank';c['outline']=dict(w=140.4,h=87.48);c.update(binding('physical/ref_tile/hv15_dbk_bank/views/ot_hgi_dma_back_landing_bank','ot_hgi_dma_back_landing_bank','rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp_banks.sv'))
 s['controller_binding_status']='STK0 routed controller only; registered stk strap is still absent from actual RTL. No inherited STK1..3 view qualification.'
 s['children'][-1]['dedupe']='Registered stk strap remains requested; actual parent still specializes STK/QID. No new per-stack routes.'
 s['parent_qualified']=False
 s['child_binding_refresh_2116']='Eight actual L[b].u_bank instances use geo1 CLOSED/native PASS 140.4x87.48 view. Parent size/child homes/ports preserved; parent packing and seams remain OPEN.'
g['native_child_refresh_2116']=dict(owner='Codex HBM takeover',date='2026-10-15',outline_changes=False,production_latency_changes=False,source_rule='Source paths and all LEF/TT/FF/insertion identities pinned; child qualification does not qualify parent.',changes=['hb_ckgen actual one release child and west-pin adjacency','32 DMA bank child identities/outline and actual generated hierarchy names','Controller strap implementation gap explicit'])
p.write_text(json.dumps(g,indent=1)+'\n')
