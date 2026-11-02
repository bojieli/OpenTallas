import json
from pathlib import Path
import pytest
import forwarded_export_loader as L


def kit(tmp_path):
    k=tmp_path/'kit';k.mkdir()
    (k/'config.mk').write_text('export OT_VCLK_TT = 250\nexport OT_VCLK_FF = 202.5\n')
    (k/'constraint.sdc').write_text('create_clock -name clk -period 833 [get_ports {rootA rootB}]\ncreate_generated_clock -name fclk_out_data -master_clock clk -source [get_ports rootA] -divide_by 1 [get_ports fclk_out_data]\n')
    (k/'setRC_rcx.tcl').write_text('# actual RC fixture\n')
    n=k/'run/results/asap7/dp_slice_station__t41/base';n.mkdir(parents=True)
    (n/'1_2_yosys.v').write_text('module s81p_slice_station__t41(); output [2:0] data; endmodule\n')
    return k


def test_off_and_exact_corner_original_state_order(tmp_path):
    k=kit(tmp_path);off=tmp_path/'off';L.prepare(k,off)
    assert 'read_db' not in (off/'tt/session.tcl').read_text()
    out=tmp_path/'on';r=L.prepare(k,out,True)
    assert r['query_limit']==6 and r['status']=='PREP_ONLY_NO_EDA'
    for corner in ['tt','ff']:
        t=(out/corner/'session.tcl').read_text()
        assert t.index('read_db /base/4_cts.odb')<t.index('read_sdc /work/constraint.sdc')<t.index('estimate_parasitics -placement')<t.index('proc fx_run')
        assert 'ot_ps_zero_unc\n' not in t[t.index('# Optional observer only.'): ] and 'delete_clock' not in t[t.index('# Optional observer only.'): ]
        assert 'POST_CTS_PLACEMENT_ESTIMATE_NOT_ROUTED_OR_EXTRACTED' in t
        assert 'selected T41 input changed' in t
    assert 'set_clock_latency -source 202.5' in (out/'ff/session.tcl').read_text()
    assert 'set_clock_latency -source 202.5' not in (out/'tt/session.tcl').read_text()


def test_reject_ambiguous_corner_reference_and_checkpoint(tmp_path):
    k=kit(tmp_path)
    with pytest.raises(ValueError):L.prepare(k,tmp_path/'bad',True,odb='../4_cts.odb')
    with (k/'config.mk').open('a') as f:f.write('export OT_VCLK_FF = 199\n')
    with pytest.raises(ValueError,match='ambiguous'):L.prepare(k,tmp_path/'ambiguous',True)
