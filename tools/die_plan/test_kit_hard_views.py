import json
from pathlib import Path

import kit_hard_views as H


def test_reused_selected_view_stages_once_and_preserves_soft_sources(tmp_path):
    view, rtl = tmp_path / 'view', tmp_path / 'rtl'
    view.mkdir(); rtl.mkdir()
    lef = view / 'hard.lef'; lef.write_text('MACRO hard\nEND hard\n')
    bb = view / 'hard_bb.v'; bb.write_text('(* blackbox *) module hard(input a); endmodule\n')
    native = rtl / 'native.sv'
    native.write_text('module soft(input a, output y); assign y=a; endmodule\n')
    original = native.read_bytes()
    manifest = rtl / 'kit_rtl.json'
    manifest.write_text(json.dumps(dict(files=[str(native), str(bb)])))
    (rtl / 'kit_rtl.f').write_text('+define+KEEP_SOFT\n' + str(native) + '\n' + str(bb) + '\n')
    macros = [('left', 'hard', str(lef), None, 0, 0, 'R0'),
              ('right', 'hard', str(lef), None, 10, 0, 'R0')]
    staged = H.stage_resolved(rtl, {'hard'}, macros, tmp_path)
    assert len(staged) == 1
    assert (rtl / 'hard_bb.v').read_bytes() == bb.read_bytes()
    assert native.read_bytes() == original
    assert json.loads(manifest.read_text())['files'] == [str(native), str(rtl / 'hard_bb.v')]
    assert (rtl / 'kit_rtl.f').read_text().startswith('+define+KEEP_SOFT\n')
    # A different BB with the same basename must not be silently overwritten,
    # even though the requested physical view itself is otherwise valid.
    (rtl / 'hard_bb.v').write_text('(* blackbox *) module different(input b); endmodule\n')
    try:
        H.stage_resolved(rtl, {'hard'}, macros, tmp_path)
    except ValueError as exc:
        assert 'conflicting fixed-port BB basename' in str(exc)
    else:
        raise AssertionError('conflicting BB was accepted')
    assert native.read_bytes() == original
