import copy
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('audit', Path(__file__).resolve().parents[1]/'tools/audit_current_asap7_routes.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_current_source_and_retained_route_required(tmp_path):
    source = tmp_path/'rtl/block.sv'; source.parent.mkdir(); source.write_text('module block; endmodule')
    artifacts = {}
    for name in audit.REQUIRED:
        p = tmp_path/name; p.write_text(name)
        artifacts[name] = dict(retained=True, sha256=audit.digest(p))
    check = dict(stage='place_and_route', setup_wns_ns=0.01, hold_wns_ns=0.01)
    for key in ('setup_violations', 'hold_violations', 'drc_errors', 'antenna_violating_nets',
                'antenna_violating_pins', 'max_slew_violations', 'max_cap_violations', 'max_fanout_violations'):
        check[key] = 0
    record = dict(design=dict(top='block', parameters={'WIDTH': 8}, clock_period_ns=1,
        sources=[dict(path='rtl/block.sv', sha256=audit.digest(source))]),
        acceptance=dict(status='pass', checks=[check]), place_and_route=dict(artifact_dir='', artifacts=artifacts))
    assert audit.audit(record, tmp_path)['eligible']
    for field, value in [('max_fanout_violations', 1), ('hold_wns_ns', -0.000001), ('setup_wns_ns', float('nan'))]:
        bad = copy.deepcopy(record); bad['acceptance']['checks'][0][field] = value
        assert not audit.audit(bad, tmp_path)['eligible']
    bad = copy.deepcopy(record); bad['acceptance']['checks'][0]['stage'] = 'static_timing'
    assert not audit.audit(bad, tmp_path)['eligible']
    for period in (0, -1, float('inf'), None):
        bad = copy.deepcopy(record); bad['design']['clock_period_ns'] = period
        assert not audit.audit(bad, tmp_path)['eligible']
    experiment = tmp_path/'results/candidate.sv'; experiment.parent.mkdir(); experiment.write_bytes(source.read_bytes())
    bad = copy.deepcopy(record); bad['design']['sources'][0]['path'] = 'results/candidate.sv'
    assert not audit.audit(bad, tmp_path)['eligible']
    (tmp_path/'6_final.v').write_text('changed')
    assert not audit.audit(record, tmp_path)['eligible']
    (tmp_path/'6_final.v').write_text('6_final.v'); source.write_text('changed RTL')
    assert not audit.audit(record, tmp_path)['eligible']
