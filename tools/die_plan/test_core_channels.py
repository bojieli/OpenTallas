"""Demand-aware channel gate and retained geometric diagnostics."""
import json
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check


def cm(channels=None, seams=None, **audit):
    return dict(status='KNOWN', outline_um=[100, 100],
                macros=[dict(name='a', rect_um=[10, 5, 90, 45]),
                        dict(name='b', rect_um=[10, 45, 90, 85])],
                channels=channels or [],
                channel_audit=dict(status='COMPLETE', pin_escape_ok=True,
                                   internal_seams=seams or [], **audit))


def test_abutted_no_crossings_with_escape_passes_despite_width_diagnostic():
    c=cm(seams=[dict(name='ab', required_crossings=0, external_pin_escape_ok=True)])
    assert any(not x['ok'] for x in check.core_channel_findings(c))
    f, complete=check.core_channel_demand_findings(c)
    assert complete and all(x['ok'] for x in f)


def test_abutted_crossing_without_channel_fails():
    f,_=check.core_channel_demand_findings(cm(seams=[dict(name='ab', required_crossings=1)]))
    assert any(not x['ok'] for x in f)


def test_zero_width_positive_demand_fails():
    f,_=check.core_channel_demand_findings(cm([dict(name='ab',dir='H',span_um=[45,45],demand_nets=1)]))
    assert not f[0]['ok'] and math.isinf(f[0]['use'])


def test_pin_escape_fails_even_without_crossings():
    c=cm(seams=[dict(name='ab',required_crossings=0,external_pin_escape_ok=False)])
    c['channel_audit']['pin_escape_ok']=False
    f,complete=check.core_channel_demand_findings(c)
    assert not complete and sum(not x['ok'] for x in f)==2


def test_actual_channel_use_and_seam_coverage():
    channel=dict(name='mid',dir='H',span_um=[40,42],demand_nets=10)
    seam=dict(name='ab',required_crossings=10,channel='mid')
    f,complete=check.core_channel_demand_findings(cm([channel],[seam]))
    assert complete and all(x['ok'] for x in f)
    channel['demand_nets']=1000
    f,_=check.core_channel_demand_findings(cm([channel],[seam]))
    assert not f[0]['ok'] and not f[1]['ok']
    channel['demand_nets']=9
    f,_=check.core_channel_demand_findings(cm([channel],[seam]))
    assert f[0]['ok'] and not f[1]['ok']


def test_missing_audit_unknown():
    c=cm();c.pop('channel_audit')
    assert check.core_channel_demand_findings(c)==([],False)


def test_invalid_records_do_not_bypass():
    for ch in [dict(name='x',dir='H',span_um=[0,2],demand_nets=-1),
               dict(name='x',dir='H',span_um=[0,float('nan')],demand_nets=1),
               dict(name='x',dir='H',span_um=[0,2],demand_nets=1.5),
               dict(name='x',dir='X',span_um=[0,2],demand_nets=1)]:
        f,_=check.core_channel_demand_findings(cm([ch]))
        assert not f[0]['ok']


def test_report_integration_geometry_warning_actual_demand_error(tmp_path):
    class Plan:
        types={'t':dict(hard_cores=[dict(module='m')])}
    c=cm([dict(name='hot',dir='H',span_um=[0,0],demand_nets=1)])
    (tmp_path/'core_macros.json').write_text(json.dumps(dict(cores=dict(m=c))))
    r=check.Report(True); result=check.check_core_channels(Plan(),r,tmp_path)
    assert result['failing_modules']==['m'] and len(r.errors())==1
    assert any('fixed-width' in x['msg'] and x['level']=='WARN' for x in r.items)
    c=cm(seams=[dict(name='ab', required_crossings=0, external_pin_escape_ok=True)])
    (tmp_path/'core_macros.json').write_text(json.dumps(dict(cores=dict(m=c))))
    r=check.Report(True);result=check.check_core_channels(Plan(),r,tmp_path)
    assert not r.errors() and result['demand_complete']==1
