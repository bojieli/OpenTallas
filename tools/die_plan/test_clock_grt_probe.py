import json
from pathlib import Path
import clock_grt_probe as probe


def test_combined_probe_keeps_signal_and_clock_identity(tmp_path):
    kit, ck, out = (tmp_path/x for x in ['kit','clock','out'])
    (kit/'grt').mkdir(parents=True); ck.mkdir()
    (kit/'grt/route.v').write_text('module signal (rst_n);\ninput rst_n;\nendmodule\n')
    (kit/'grt/grt.tcl').write_text('read_verilog /work/grt/route.v\nlink_design signal\nsource /work/grt/obs.tcl\n')
    (ck/'ctree.v').write_text('// generator header\nmodule die_ctree (root, t_a);\ninput root; output t_a; wire w;\nBUFx24_ASAP7_75t_R n0 (.A(root), .Y(w));\nBUFx24_ASAP7_75t_R leaf (.A(w), .Y(t_a));\nendmodule\n')
    (ck/'tree.json').write_text(json.dumps(dict(meta=dict(root_um=[0,0]),taps=[dict(port='t_a',xy=[1,2])])) )
    (ck/'place.json').write_text(json.dumps(dict(n0=dict(x=0,y=0,kind='node',level=0),leaf=dict(x=1,y=2,kind='chain',level=10))))
    (ck/'nets.json').write_text(json.dumps(dict(nets=[dict(name='root',drv='port:root'),dict(name='w',drv='n0'),dict(name='t_a',drv='leaf')])))
    info=probe.build(kit,ck,out)
    v=(out/'combo.v').read_text(); t=(out/'combo.tcl').read_text()
    assert 'input rst_n' in v and 'BUFx24_ASAP7_75t_R ck_n0 (.A(root), .Y(ck_w))' in v
    assert 'BUFx24_ASAP7_75t_R ck_leaf (.A(ck_w), .Y(t_a))' in v
    assert info['ndr_nets']=={4:1,8:2}
    assert '[$blk findNet ck_w] setNonDefaultRule $n8' in t
    assert '[$blk findNet t_a] setNonDefaultRule $n4' in t
    assert '-period 833.000' in t
    assert 'arrival_min_rise' in t  # common-prefix credit must have measured early + late.
