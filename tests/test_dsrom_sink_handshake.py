import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_sink_handshake as S


def test_default_off_and_exact_source_selection():
    sources=[ROOT/'rtl/hdc/v41'/n for n in S.NAMES]
    off=S.select(sources)
    assert off['sources']==sources and not off['defines']
    on=S.select(sources,enable=True)
    assert on['sources']==[S.SUCCESSOR/n for n in S.NAMES]
    assert on['defines']==['+define+OT_MTP_SINK_HANDSHAKE=1','+define+OT_MTP_HE_TAG=1']
    assert on['wave2_admitted']
    adapt=ROOT/'rtl/hdc/v41x/ot_hdc_v41x_xu_adapt.sv'
    both=S.select(sources+[adapt],enable=True)
    assert both['sources'][-1]==S.SUCCESSOR/'ot_hdc_v41x_xu_adapt.sv'
    with pytest.raises(ValueError):S.select(sources+[adapt,adapt],enable=True)
    with pytest.raises(ValueError):S.select([sources[0]],enable=True)
    with pytest.raises(ValueError):S.select(sources+[sources[0]],enable=True)


def test_arithmetic_and_core_files_remain_pinned():
    import subprocess
    for name in ('ot_hdc_v41_xu.sv','ot_hdc_sinkhorn_mc.sv','ot_hdc_sinkhorn.sv','ot_hdc_sk_arith.sv'):
        path='rtl/hdc/v41/'+name
        assert (ROOT/path).read_bytes()==subprocess.check_output(['git','show','7a073a767:'+path],cwd=ROOT)
    # canonical core re-pinned at b03898cfe: after 7a073a767 it changed only in the DYN table (ring DYN25/26 enable,
    # 3dea693b1 / aff63db74) and the verbatim move of that table into ot_hdc_v41x_dyn_unit (b03898cfe, 0 cycles;
    # campaign 14 PASS 428,093 / 15 FAIL cycle-identical). Nothing on the sink handshake path moved.
    for path,pin in (('rtl/hdc/v41x/ot_hdc_core_v41x.sv','b03898cfe'),('rtl/hdc/v41x/ot_hdc_v41x_dyn_unit.sv','b03898cfe'),
                     ('rtl/hdc/v41x/dspark/ot_hdc_core_v41x.sv','7a073a767')):
        assert (ROOT/path).read_bytes()==subprocess.check_output(['git','show',pin+':'+path],cwd=ROOT)
