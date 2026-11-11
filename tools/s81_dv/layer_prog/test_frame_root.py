"""frame_root.py: a ROOT-relative copy of a manifest with absolute / external paths that slice_source and the frame tie accept."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import pytest
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import frame_root as FR  # noqa: E402
import slice_source  # noqa: E402
import dv_layer_compile as C  # noqa: E402


def _tree(tmp):
    base = tmp / 'src'; (base / 'rtl').mkdir(parents=True)
    (base / 'rtl/a.sv').write_text('module a; endmodule\n')
    ext = tmp / 'other/romq'; ext.mkdir(parents=True)
    (ext / 'q.sv').write_text('module q; endmodule\n')
    (ext / 'q.hard_params.json').write_text('{"masters": {}}\n')
    m = tmp / 'cand/asbuilt.json'; m.parent.mkdir()
    m.write_text(json.dumps(dict(base=str(base), top='a', defines=[], netlist=[str(base / 'rtl/a.sv')],
                                 files=['rtl/a.sv', str(ext / 'q.sv')], prefer=[str(base / 'rtl/a.sv')],
                                 hard_params=[str(ext / 'q.hard_params.json')], stage_hash_roots={'x': str(tmp / 'other')})))
    root = tmp / 'root'
    subprocess.run(['cp', '-al', str(base), str(root)], check=True)
    return m, base, root


def test_build_and_select(tmp_path, monkeypatch):
    monkeypatch.delenv('OT_S81_SELECTED_DEFINES', raising=False)
    m, base, root = _tree(tmp_path)
    r = FR.build(m, root, 'bind/frame.json', extractor=False)
    assert r['files_mapped'] == 4 and len(r['external']) == 2
    out = json.loads((root / 'bind/frame.json').read_text())
    assert out['base'] == '..' and all(not Path(f).is_absolute() for f in out['files'] + out['prefer'])
    assert out['stage_hash_roots'] == {'x': str(tmp_path / 'other')}
    slice_source.manifest_selection(root, 'bind/frame.json')     # the slice lookup accepts it
    with pytest.raises(ValueError):
        slice_source.manifest_selection(base, str(m))           # the original is refused (outside root)
    a, b = C.manifest_content(m), C.manifest_content(root / 'bind/frame.json')
    assert a == b


def test_refuses_changed_copy(tmp_path):
    m, base, root = _tree(tmp_path)
    (root / 'rtl/a.sv').unlink(); (root / 'rtl/a.sv').write_text('module a; wire w; endmodule\n')
    with pytest.raises(ValueError, match='differs'):
        FR.build(m, root, 'bind/frame.json', extractor=False)


def test_refuses_base_itself(tmp_path):
    m, base, root = _tree(tmp_path)
    with pytest.raises(ValueError, match='copy'):
        FR.build(m, base, 'bind/frame.json', extractor=False)
