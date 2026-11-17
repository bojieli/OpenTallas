import json,argparse
from pathlib import Path

def run(model,sites,out):
 m=json.loads(model.read_text());s=json.loads(sites.read_text());table={r['bus']:r for r in s['rows'] if r['status']=='SITE_CANDIDATE'}
 aliases={'i_ctl':'i_kvs_ctl_o_emb','i_hroot_WS':'i_kvs_hroot_WS_o_emb','i_hroot_WN':'i_kvs_hroot_WN_o_emb','i_hroot_ES':'i_kvs_hroot_ES_o_emb','i_hroot_EN':'i_kvs_hroot_EN_o_emb','rowtx__emb_tx_payload':'o_kvs_emb_rowtx__emb_tx_payload','rowtx__emb_tx_v':'o_kvs_emb_rowtx__emb_tx_v','px_tok':'o_kvs_emb_px_tok','px_tep':'o_kvs_emb_px_tep','o_ctx_svc':'L2416_o'}
 rows=[]
 for direction,ports,stages,usedkey in [('in',m['input_ports'],4,'used_bits'),('out',m['output_ports'],2,'nonconstant_bits')]:
  for pn,r in ports.items():
   loc=table.get(aliases.get(pn,''));banks=(loc or {}).get('banks',[])
   # Geometric paths run boundary->producer; invert their stage order for outgoing data.
   if direction=='out':banks=list(reversed(banks))
   for st in range(stages):
    width=r['declared_bits'];used=r[usedkey];at=banks[st]['xy'] if st<len(banks) else None
    rows.append(dict(branch=f'ctx_{direction}_{pn}_s{st+1}',port=pn,stage=st+1,declared_data_FF=width,observed_used_data_FF_floor=used,epoch_FF_copy=1,TT_CLK_used_floor_fF=used*.474736+.462899,TT_CLK_declared_upper_fF=width*.474736+.462899,xy_um=at,site_qualified=False,clock_qualified=False))
 upper=sum(r['declared_data_FF'] for r in rows);floor=sum(r['observed_used_data_FF_floor'] for r in rows);assert (len(rows),upper,floor)==(44,9500,7522)
 total_area_upper=m['area_accounting']['total_composed_candidate_floor_um2']+(upper-floor)*.2916
 total_clock_upper=m['clock_accounting_TT_fF']['total_composed_candidate']+(upper-floor)*.474736
 o=dict(schema='opentallas.kv-context-transport-clock-candidate.v1',state='ADMISSION_UPPER_AND_COMPONENT_CLOCK_BUDGET_ONLY',total_added_clock_branches=44,geometrically_located_branches=sum(r['xy_um'] is not None for r in rows),unlocated_branches=sum(r['xy_um'] is None for r in rows),transport_data_FF_floor=floor,transport_data_FF_declared_upper=upper,transport_epoch_FF_copies=44,transport_CLK_TT_floor_fF=sum(r['TT_CLK_used_floor_fF'] for r in rows),transport_CLK_TT_declared_upper_fF=sum(r['TT_CLK_declared_upper_fF'] for r in rows),full_composed_FF_declared_upper=5502+upper+44+350,full_composed_area_declared_upper_floor_um2=total_area_upper,full_composed_CLK_TT_declared_upper_fF=total_clock_upper,clock_buffer_wire_hold_PDN_cost_unpriced=True,rows=rows,selection='C context proposal only; do not add these leaves to HG5 or selected production CA without a composed C plan/consumer event')
 out.write_text(json.dumps(o,indent=1)+'\n');print({k:v for k,v in o.items() if k!='rows'})
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--model',type=Path,required=True);a.add_argument('--sites',type=Path,required=True);a.add_argument('--out',type=Path,required=True);p=a.parse_args();run(p.model,p.sites,p.out)
