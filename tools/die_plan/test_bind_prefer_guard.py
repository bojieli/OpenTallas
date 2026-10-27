"""Missing preferred implementations must fail before expensive fallback elaboration."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bind
import manifest_paths as M


def test_prefer_literals_complete_list_and_existing_file(tmp_path):
    (tmp_path/'live.sv').write_text('module live;endmodule\n')
    ab=dict(prefer=['live.sv','missing.sv','more.v','module_preference','rtl/*.sv','rtl/x[0-9].v'])
    errors=M.required_prefer_files(ab,tmp_path)
    assert len(errors)==2 and 'missing.sv' in errors[0] and 'more.v' in errors[1]
    assert M.required_prefer_files(dict(prefer='live.sv'),tmp_path)==[]


def test_absolute_diagnostic_literal_still_required(tmp_path):
    missing=tmp_path/'absent.v'
    assert len(M.required_prefer_files(dict(prefer=[str(missing)]),'/unused'))==1
    missing.write_text('module m;endmodule\n')
    assert M.required_prefer_files(dict(prefer=[str(missing)]),'/unused')==[]


def test_frontdoor_blocks_before_provenance_or_elaboration(tmp_path,monkeypatch):
    plan=tmp_path/'plan.json'
    plan.write_text(json.dumps(dict(asbuilt=dict(base='.',prefer=['nine.sv'],top='top'))))
    monkeypatch.setattr(bind,'_AB_OVERRIDE',{})
    def forbidden(*args,**kwargs):
        raise AssertionError('expensive elaboration/provenance must not be reached')
    monkeypatch.setattr(bind,'_write_provenance',forbidden)
    monkeypatch.setattr(bind.E,'elab',forbidden)
    with pytest.raises(bind.BindError,match='nine.sv'):
        bind.cmd_elab(SimpleNamespace(plan=str(plan)))


def test_complete_prefer_reaches_existing_elaboration(tmp_path,monkeypatch):
    (tmp_path/'impl.sv').write_text('module m;endmodule\n')
    plan=tmp_path/'plan.json';plan.write_text(json.dumps(dict(asbuilt=dict(base='.',prefer=['impl.sv']))))
    monkeypatch.setattr(bind,'_AB_OVERRIDE',{})
    monkeypatch.setattr(bind,'_write_provenance',lambda *args:None)
    calls=[]
    monkeypatch.setattr(bind.E,'elab',lambda *args: calls.append(args) or {})
    assert bind.cmd_elab(SimpleNamespace(plan=str(plan),out='out',mem=1))==0
    assert len(calls)==1 and Path(calls[0][1])==tmp_path
