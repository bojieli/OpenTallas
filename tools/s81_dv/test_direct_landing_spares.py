import json,tempfile
from pathlib import Path
import pytest
import dv_spare_out as S

def run(expr,lo=237):
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);base=root/'results/arch/s81_dv_1016/svc_rs';base.mkdir(parents=True)
  (base/'tree.json').write_text(json.dumps({'slices':{}}));(base/'embed.json').write_text(json.dumps({'roles':{}}))
  sl=root/'rtl/dsrom_sys/s81_dv/slice';sl.mkdir(parents=True);(sl/'ot_s81sl_slice.sv').write_text('')
  lines=['wire [275:0] w_iq_l1_src;', 'wire [275:0] w_iq_l1_lnd;',
   'dsfd_dvland_276 ld_iq_l1 (.i('+expr+'), .o(w_iq_l1_lnd));']
  pads={'ld_iq_l1':{'master':'dsfd_dvland_276','reason':'lane quantisation:237b payload','ports':{'i':[[lo,275]]}}}
  rec=S.declare(lines,pads,root)
  return rec,pads

def test_exact_direct_zero_spare_range_is_carried_to_output():
 rec,pads=run("{39'd0, w_iq_l1_src[236:0]}")
 assert not rec['gaps'];assert rec['summary']['B_lane_quantisation']['bits']==39
 assert pads['ld_iq_l1']['ports']['o']==[[237,275]]

@pytest.mark.parametrize('expr,lo',[("{39'd1, w_iq_l1_src[236:0]}",237),("{39'd0, w_iq_l1_src[236:0]}",200),('w_iq_l1_src',237)])
def test_live_or_nonzero_payload_cannot_be_declared_spare(expr,lo):
 rec,pads=run(expr,lo)
 assert rec['gaps'];assert rec['summary']['B_lane_quantisation']['bits']==0
 assert 'o' not in pads['ld_iq_l1']['ports']
