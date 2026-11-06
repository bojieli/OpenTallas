"""Canonical portable views may retain only the signed receipt's exact path/hash."""
import json
import pytest
import hard_landing as H

@pytest.mark.parametrize('portable', [False, True])
def test_capture_uses_exact_exported_signoff_and_rejects_tamper(tmp_path, portable):
    view=tmp_path/'view';src=tmp_path/'source';view.mkdir();src.mkdir()
    lef=view/'child.lef';lib=view/'child_tt.lib';lef.write_text('LEF');lib.write_text('LIB')
    net=src/'net.v';net.write_text('module child(); endmodule')
    (src/'face_guard.json').write_text(json.dumps(dict(netlist=str(net))))
    (src/'face_guard.py').write_text('# frozen tool')
    (src/'land_slots.json').write_text('{}')
    signoff=(view if portable else src)/'signoff.json';signoff.write_text('{"verdict":"SIGNED"}')
    (view/'provenance.json').write_text(json.dumps(dict(src=str(src),export=dict(signoff=str(signoff),signoff_sha256=H.digest(signoff)))))
    H.capture(lef,lib,'child',4,2,tmp_path/'captured')
    assert (tmp_path/'captured/signoff.json').read_bytes()==signoff.read_bytes()
    signoff.write_text('{"verdict":"FAIL"}')
    with pytest.raises(ValueError,match='differs from the exported receipt'):
        H.capture(lef,lib,'child',4,2,tmp_path/'tampered')
