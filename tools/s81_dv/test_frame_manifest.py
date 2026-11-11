"""S81-PLAN-1 11-10: frame schedules bind the bind's own manifest (OT_S81_FRAME_*), separate from the slice selection;
a repo-relative copy of a manifest is accepted only when it selects the same file contents."""
import json
import os
import sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/s81_dv/layer_prog'), str(ROOT / 'tools/s81_dv')]
import lower_xs as X  # noqa: E402
import dv_layer_compile as C  # noqa: E402


def test_frame_manifest_precedence(monkeypatch):
    for k in ('OT_S81_FRAME_ASBUILT_MANIFEST', 'OT_S81_FRAME_SOURCE_ROOT', 'OT_S81_SELECTED_ASBUILT_MANIFEST',
              'OT_S81_SELECTED_SOURCE_ROOT'):
        monkeypatch.delenv(k, raising=False)
    assert X.frame_manifest()[1] == 'physical/die_plan/s81/bind/asbuilt_b178_coll.json'
    monkeypatch.setenv('OT_S81_SELECTED_ASBUILT_MANIFEST', 'slices.json')
    assert X.frame_manifest()[1] == 'slices.json'
    monkeypatch.setenv('OT_S81_FRAME_ASBUILT_MANIFEST', 'frames.json')
    monkeypatch.setenv('OT_S81_FRAME_SOURCE_ROOT', '/x')
    assert X.frame_manifest() == (Path('/x'), 'frames.json')


def _man(d, files, base, defines=('A',)):
    p = d / 'm.json'
    p.write_text(json.dumps(dict(base=base, top='t', defines=list(defines), netlist=files[0], files=files)))
    return p


def test_manifest_content(tmp_path):
    src = tmp_path / 'src'
    (src / 'rtl').mkdir(parents=True)
    (src / 'rtl/a.sv').write_text('module a; endmodule\n')
    (src / 'rtl/b.sv').write_text('module b; endmodule\n')
    absd = tmp_path / 'abs'; absd.mkdir()
    a = _man(absd, [str(src / 'rtl/a.sv'), str(src / 'rtl/b.sv')], str(src))
    reld = src / 'cp'; reld.mkdir()
    r = _man(reld, ['rtl/a.sv', 'rtl/b.sv'], '..')
    assert C.manifest_content(a) == C.manifest_content(r)
    (src / 'rtl/c.sv').write_text('module b; wire x; endmodule\n')
    other = tmp_path / 'o'; other.mkdir()
    o = _man(other, [str(src / 'rtl/a.sv'), str(src / 'rtl/c.sv')], str(src))
    assert C.manifest_content(a) != C.manifest_content(o)
    d = tmp_path / 'd'; d.mkdir()
    assert C.manifest_content(a) != C.manifest_content(_man(d, [str(src / 'rtl/a.sv'), str(src / 'rtl/b.sv')], str(src), ('B',)))
    m = tmp_path / 'x'; m.mkdir()
    assert C.manifest_content(_man(m, ['rtl/missing.sv'], str(src)))['files'] == ['rtl/missing.sv']


def test_manifest_content_options(tmp_path):
    src = tmp_path / 'src'; (src / 'rtl').mkdir(parents=True)
    (src / 'rtl/a.sv').write_text('module a; endmodule\n')
    d1 = tmp_path / 'd1'; d1.mkdir(); d2 = tmp_path / 'd2'; d2.mkdir()
    p1 = d1 / 'm.json'; p1.write_text(json.dumps(dict(base=str(src), files=[str(src / 'rtl/a.sv')], prefer=['x'])))
    p2 = d2 / 'm.json'; p2.write_text(json.dumps(dict(base=str(src), files=['rtl/a.sv'], prefer=['y'])))
    assert C.manifest_content(p1) != C.manifest_content(p2)
