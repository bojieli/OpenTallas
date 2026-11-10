"""S81-PLAN-1 D: lower_xs admits a GB frame only through a PASS, sha-bound provider qualification record, per station."""
import hashlib
import json
import sys
from pathlib import Path
import pytest
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import lower_xs as X  # noqa: E402

EL = 'rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb_split.sv'


def h(b):
    return hashlib.sha256(b).hexdigest()


def setup(tmp, ages=(2, 4), qualified=(2, 4), verdict='PASS'):
    root = tmp / 'root'; (root / 'rtl/v41rom').mkdir(parents=True)
    (root / EL).write_bytes(b'module split; endmodule\n')
    (root / 'rtl/xs4.sv').write_bytes(b'module xs4; endmodule\n')
    st = {f'e{i}': dict(added_edges=[a], all_x_inputs_equal_added_edges=True, go_boundary_edges=1,
                        required_go_issue_advance_edges=1, native_provider_qualified=False) for i, a in enumerate(ages)}
    sched = dict(source_sha256={EL: h((root / EL).read_bytes())}, station_inputs=st)
    rec = dict(schema='opentallas.s81.gb_provider_qualification.v1', verdict=verdict, qualified_x_ages=list(qualified),
               required_go_issue_advance_edges=1, element=dict(source=EL, sha256=h((root / EL).read_bytes())),
               provider_source_sha256={EL: h((root / EL).read_bytes()), 'rtl/xs4.sv': h((root / 'rtl/xs4.sv').read_bytes())})
    d = tmp / 'sched'; d.mkdir()
    (d / X.GB_QUAL).write_text(json.dumps(rec))
    return root, sched, d


def test_no_record_refused(tmp_path, monkeypatch):
    monkeypatch.delenv('OT_XS_GB_PROVIDER_UNDER_TEST', raising=False)
    root, sched, d = setup(tmp_path)
    (d / X.GB_QUAL).unlink()
    with pytest.raises(ValueError, match='qualified one-edge-early'):
        X.qualify_frame_source(sched, 'm', root, record_dir=d)


def test_record_admits_qualified_ages(tmp_path):
    root, sched, d = setup(tmp_path)
    assert X.qualify_frame_source(sched, 'm', root, record_dir=d) == h((d / X.GB_QUAL).read_bytes())


def test_unqualified_age_refused(tmp_path):
    root, sched, d = setup(tmp_path, ages=(2, 18), qualified=(2, 4))
    with pytest.raises(ValueError, match=r'station e1 X age \[18\]'):
        X.qualify_frame_source(sched, 'm', root, record_dir=d)


def test_other_bytes_refused(tmp_path):
    root, sched, d = setup(tmp_path)
    (root / 'rtl/xs4.sv').write_bytes(b'module xs4; wire w; endmodule\n')
    with pytest.raises(ValueError, match='other bytes'):
        X.qualify_frame_source(sched, 'm', root, record_dir=d)


def test_element_not_schedules_refused(tmp_path):
    root, sched, d = setup(tmp_path)
    rec = json.loads((d / X.GB_QUAL).read_text()); rec['element']['sha256'] = '0' * 64
    (d / X.GB_QUAL).write_text(json.dumps(rec))
    with pytest.raises(ValueError, match="not the schedule"):
        X.qualify_frame_source(sched, 'm', root, record_dir=d)


def test_fail_record_refused(tmp_path):
    root, sched, d = setup(tmp_path, verdict='FAIL')
    with pytest.raises(ValueError, match='not a PASS'):
        X.qualify_frame_source(sched, 'm', root, record_dir=d)


def test_advance_must_be_one(tmp_path):
    root, sched, d = setup(tmp_path)
    sched['station_inputs']['e0']['required_go_issue_advance_edges'] = 2
    with pytest.raises(ValueError, match='qualified one-edge-early'):
        X.qualify_frame_source(sched, 'm', root, record_dir=d)
