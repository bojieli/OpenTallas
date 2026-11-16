import importlib.util
import json
import shutil
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import kit_rtl_closure as C
sys.path.insert(0, str(Path(__file__).parents[1] / 'die_plan'))
import kit_gen_lint as L


def vehicle(tmp_path):
    src, bind, work = [tmp_path / n for n in ('src', 'bind', 'attempt')]
    for p in (src,bind,work/'rtl'):
        p.mkdir(parents=True)
    kd=work/'rtl'
    for p in (src/'leaf.sv',bind/'bind_cells.sv',kd/'wrapper.sv'):
        p.write_text('module '+p.stem+'; endmodule\n')
    files=[kd/'wrapper.sv',bind/'bind_cells.sv',src/'leaf.sv']
    (bind/'bind_report.json').write_text('{"errors":[]}')
    (kd/'kit_rtl.f').write_text('\n'.join(map(str,files))+'\n')
    (kd/'kit_rtl.json').write_text(json.dumps(dict(bind_out=str(bind),files=list(map(str,files)))))
    return src,bind,kd


def receipt(kd):
    meta=json.loads((kd/'kit_rtl.json').read_text())
    (kd/'kit_rtl_paths.json').write_text(json.dumps(dict(src_tree='unused',filelist=str(kd/'kit_rtl.f'),files=(kd/'kit_rtl.f').read_text().splitlines(),input_closure=meta['input_closure'])))


def test_packaged_dependency_survives_source_retirement_and_checks_content(tmp_path):
    src,bind,kd=vehicle(tmp_path)
    C.package(kd,src)
    receipt(kd)
    shutil.rmtree(src); shutil.rmtree(bind)
    assert L.kit_rtl_paths(kd)==([],True)
    meta=json.loads((kd/'kit_rtl.json').read_text())
    assert (Path(meta['bind_out'])/'bind_report.json').is_file()
    leaf=Path((kd/'kit_rtl.f').read_text().splitlines()[-1])
    leaf.write_text('stale mutation')
    assert 'content mismatch' in L.kit_rtl_paths(kd)[0][0]


def test_outside_source_is_rejected_before_packaging(tmp_path):
    src,bind,kd=vehicle(tmp_path)
    outside=tmp_path/'old_tree.sv';outside.write_text('module wrong;endmodule')
    with (kd/'kit_rtl.f').open('a') as f:f.write(str(outside)+'\n')
    with pytest.raises(ValueError,match='invalid source'):C.package(kd,src)
    assert not (kd/'kit_rtl.producer.json').exists()


def test_lexical_attempt_path_survives_changed_scratch_alias(tmp_path):
    src,bind,kd=vehicle(tmp_path)
    alias=tmp_path/'scratch_alias';alias.symlink_to(kd.parent,target_is_directory=True)
    C.package(alias/'rtl',src)
    assert all(str(alias) in x for x in (kd/'kit_rtl.f').read_text().splitlines())
    receipt(alias/'rtl')
    assert L.kit_rtl_paths(alias/'rtl')==([],True)
