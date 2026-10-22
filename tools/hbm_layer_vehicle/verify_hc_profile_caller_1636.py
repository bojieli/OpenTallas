"""Pure profile/default compatibility and current-contract rejection; no RTL."""
import argparse,json
from pathlib import Path
import numpy as np
from hbm_layer_vehicle import hc_layer_lower_1021 as H,hc_safe2_phase40_1021 as P

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--profile-packet',type=Path,required=True);p.add_argument('--contract',type=Path,required=True)
 a=p.parse_args();packet=json.loads(a.profile_packet.read_text())
 data=[(int(w,16)>>(32*k))&0xffffffff for w in packet['root_table_rows'] for k in range(7)]
 parameters=dict(base=data[:24],scale=data[24:27])
 baseline=H.root_rows(parameters,39)
 assert P.root_rows_for_profile(H.root_rows,parameters,39)==baseline
 safe=P.root_rows_for_profile(H.root_rows,parameters,39,profile=P.SAFE2_P40)
 assert safe[:2]==baseline[:2]
 assert [f'{v:064x}' for v in safe[1]]==packet['root_programme_rows']
 assert safe[2]['gather_calendar_delta_vs_legacy11']==0
 assert safe[2]['source_profile']['quarter_sys_lat0']==101
 assert safe[2]['source_profile']['quarter_sys_lat']==147
 assert safe[2]['source_profile']['ring_RAW0']==179
 try:
  H.lower_mix_post(np.zeros(24,dtype=np.uint32),np.zeros(24,dtype=np.uint32),parameters,dict(resp_phase=39),a_sector=64,o_sector=72,component_allocation=True,source_profile=P.SAFE2_P40,profile_contract=a.contract)
 except ValueError as e:
  assert 'SAFE2 source contract mismatch' in str(e);rejection=str(e)
 else:raise AssertionError('legacy contract incorrectly accepted SAFE2 profile')
 for phase,npos in [(23,1),(39,2)]:
  try:P.root_rows_for_profile(H.root_rows,parameters,phase,profile=P.SAFE2_P40,npos=npos)
  except ValueError:pass
  else:raise AssertionError('unsupported phase/position accepted')
 print(json.dumps(dict(status='PURE_SOURCE_CALLER_CHECKS_PASS',hardware_executed=False,default_root_rows_identical=True,SAFE2_gather_rows_identical=True,quarter_path_model_only=True,current_legacy_contract_refused=rejection,multiposition_refused=True,phase23_refused=True),indent=1))
