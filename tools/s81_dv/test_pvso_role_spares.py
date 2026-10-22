import json
from pathlib import Path
from dv_spare_out import declare

def test_pvso_keeps_role_inactive_faces_spare_but_never_waives_active_faces(tmp_path):
    base=tmp_path/'results/arch/s81_dv_1016/svc_rs';base.mkdir(parents=True)
    (base/'tree.json').write_text(json.dumps({'slices':{'5':{'children':1,'parent':0}}}))
    (base/'embed.json').write_text(json.dumps({'roles':{'5':{'go':[0]*4,'so':[0]*4}}}))
    sl=tmp_path/'rtl/dsrom_sys/s81_dv/slice';sl.mkdir(parents=True)
    (sl/'ot_s81sl_slice.sv').write_text('')
    lines=['  dsdv_svc_rs_pvso_entry u_rsv_05 (.ck(clk));']
    pads={};report=declare(lines,pads,tmp_path)
    assert len(report['gaps'])==1
    assert report['gaps'][0]['port']=='dn_o' and report['gaps'][0]['face']=='N'
    assert [0,804] not in pads['u_rsv_05']['ports']['dn_o']
    assert pads['u_rsv_05']['ports']['ro']==[[0,513],[514,1027],[1028,1541],[1542,2055]]
