"""S81-PLAN-1 11-10: Engram RETURN_AGE comes from the bound RTL (main constant 1536, candidate eng partition 640)."""
import sys
from pathlib import Path
import pytest
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import lower_eng as E  # noqa: E402

INST = '''module s81p_eng__t1(input clk);
    dsdv_eng_rr_e #(.HXL(0), .PCBASE(30'b0), .RETURN_AGE({ra}), .XQ_MUT(0)) u_u_e (
        .clk(clk));
endmodule
'''


def rtl(tmp, *ages, name='s81p_eng__t1.sv'):
    d = tmp / 'rtl'; d.mkdir(exist_ok=True)
    (d / name).write_text(''.join(INST.format(ra=a) for a in ages))
    return d


def test_bound_age_read(tmp_path):
    d = rtl(tmp_path, 640)
    assert E.bound_return_age(d)[0] == 640
    lat = E.lat_for(dict(bound_eng=dict(return_age=640)))
    assert lat['return_age'] == 640 and lat['first_fragment'] == 684 and lat['ii'] == 704


def test_programme_mismatch_fails(tmp_path):
    d = rtl(tmp_path, 640)
    E.check_programme(dict(latency=E.latency(640)), d)
    with pytest.raises(ValueError, match='differs'):
        E.check_programme(dict(latency=E.latency(1536)), d)        # main's constant on the candidate bind
    with pytest.raises(ValueError, match='differs'):
        E.check_programme(dict(latency=E.latency(641)), d)         # +1


def test_refusals(tmp_path):
    with pytest.raises(ValueError, match='no dsdv_eng_rr'):
        E.bound_return_age(tmp_path)
    d = rtl(tmp_path, 640, 1536)
    with pytest.raises(ValueError, match='disagree'):
        E.bound_return_age(d)
    (d / 's81p_eng__t1.sv').write_text("module m; dsdv_eng_rr_e #(.HXL(0)) u (.clk(c)); endmodule\n")
    with pytest.raises(ValueError, match='no explicit RETURN_AGE'):
        E.bound_return_age(d)


def test_env_bind(tmp_path, monkeypatch):
    rtl(tmp_path, 640)
    monkeypatch.setenv('OT_BOUND_DATA', str(tmp_path))
    assert E.lat_for()['return_age'] == 640
    monkeypatch.delenv('OT_BOUND_DATA')
    assert E.lat_for()['return_age'] == E.RETURN_AGE == 1536
