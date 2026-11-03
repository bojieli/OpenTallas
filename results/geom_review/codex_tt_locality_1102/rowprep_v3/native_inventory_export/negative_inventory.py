from pathlib import Path
import sys,json
P=Path(__file__).parent;root=P.parent;sys.path.insert(0,str(root/'tools/die_plan/tt_regional_origin'))
from native_inventory import build,read
L=Path('/home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM')
libs=[L/name for name in ['asap7sc7p5t_AO_RVT_TT_nldm_211120.lib','asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib','asap7sc7p5t_OA_RVT_TT_nldm_211120.lib','asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib','asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib']]
libs+=sorted((root/'macros').glob('*_tt.lib'))
(P/'actual_old_readset.json').write_text(json.dumps(dict(purpose='negative-only actual old TT_C reference; not the regional source event',netlist=str(P/'actual_old_1_2_yosys.v'),sdc=str(root/'frozen_constraint.sdc'),libs=[str(p) for p in libs]),indent=1)+'\n')
try:build(P/'actual_old_reference.tsv',libs,root/'frozen_constraint.sdc',read(P/'intent_PARTIAL_HELD.json.gz'),read(P/'proposal.json.gz'),P/'actual_old_readset.json',P/'actual_old_1_2_yosys.v')
except ValueError as e:
 result=dict(status='ACTUAL_OLD_SOURCE_REJECTED',reason=str(e),inventory_emitted=False)
 (P/'negative_result.json').write_text(json.dumps(result,indent=1)+'\n');print('ACTUAL_OLD_INVENTORY_REJECTED',str(e),flush=True)
 if 'regional source FF' not in str(e):raise
else:raise RuntimeError('Old physical source was falsely admitted as a new regional event')
