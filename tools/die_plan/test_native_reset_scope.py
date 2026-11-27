"""Selected reset scope retains selected/global native freshness checks."""
import copy
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_topology as K


def fixture(tmp_path):
    raw = dict(partition_types={
        'selected':dict(clock=dict(taps=[dict(x=1,y=2)]), reset=dict(depth=3), buses=[]),
        'other':dict(clock=dict(taps=[dict(x=5,y=6)]), reset=dict(depth=2), buses=[]),
    }, reset=dict(root='r'), lanes=[], ports=[])
    plan=tmp_path/'producer.json'; plan.write_text(json.dumps(raw))
    ab=tmp_path/'asbuilt.json'; ab.write_text('{}')
    out=tmp_path/'bind'; out.mkdir()
    K.write_bind_receipt(raw,out,str(ab),plan_path=plan)
    (out/'provenance_bind.json').write_text(json.dumps(dict(provenance=dict(plan=str(plan)))))
    return raw,plan,ab,out


def test_scope_default_off(tmp_path,monkeypatch):
    raw,plan,ab,out=fixture(tmp_path)
    raw['partition_types']['other']['clock']['taps'][0]['x']=99
    monkeypatch.delenv('OT_NATIVE_RESET_SCOPE',raising=False)
    assert not K.bind_matches(raw,'selected',out,str(ab),plan)
    monkeypatch.setenv('OT_NATIVE_RESET_SCOPE','selected')
    assert K.bind_matches(raw,'selected',out,str(ab),plan)


def test_scope_rejects_selected_global_transport_and_asbuilt_mutants(tmp_path,monkeypatch):
    raw,plan,ab,out=fixture(tmp_path)
    monkeypatch.setenv('OT_NATIVE_RESET_SCOPE','selected')
    raw['partition_types']['other']['clock']['taps'][0]['x']=99
    assert K.bind_matches(raw,'selected',out,str(ab),plan)
    for mutate in (
        lambda r:r['partition_types']['selected']['clock']['taps'][0].update(x=100),
        lambda r:r['partition_types']['selected']['reset'].update(depth=4),
        lambda r:r['reset'].update(root='wrong'),
        lambda r:r['ports'].append(dict(id='new',src='a',dst='b',width=4,kind='data')),
    ):
        mutant=copy.deepcopy(raw); mutate(mutant)
        assert not K.bind_matches(mutant,'selected',out,str(ab),plan)
    ab.write_text('{"changed":1}')
    assert not K.bind_matches(raw,'selected',out,str(ab),plan)


def test_scope_requires_unchanged_producer_context(tmp_path,monkeypatch):
    raw,plan,ab,out=fixture(tmp_path)
    monkeypatch.setenv('OT_NATIVE_RESET_SCOPE','selected')
    raw['partition_types']['other']['clock']['taps'][0]['x']=99
    plan.write_text(json.dumps(raw))
    assert not K.bind_matches(raw,'selected',out,str(ab),plan)
    plan.unlink()
    assert not K.bind_matches(raw,'selected',out,str(ab),plan)


def test_portable_exact_capture_and_full_producer_mutant(tmp_path,monkeypatch):
    raw,plan,ab,out=fixture(tmp_path)
    capture=tmp_path/'captured_producer.json'; capture.write_bytes(plan.read_bytes())
    plan.unlink()
    current=copy.deepcopy(raw); current['partition_types']['other']['clock']['taps'][0]['x']=99
    monkeypatch.setenv('OT_NATIVE_RESET_SCOPE','selected')
    assert not K.bind_matches(current,'selected',out,str(ab),plan)
    monkeypatch.setenv('OT_NATIVE_PRODUCER_CONTEXT',str(capture))
    assert K.bind_matches(current,'selected',out,str(ab),plan)
    mutant=copy.deepcopy(raw)
    mutant['partition_types']['other']['buses'].append(dict(name='wrong',dir='in',width=4,kind='data'))
    capture.write_text(json.dumps(mutant))
    assert not K.bind_matches(current,'selected',out,str(ab),plan)


def test_scope_ignores_kit_prep_soft_cs_banks(tmp_path,monkeypatch):
    """SOFTCS-STAMP-1122: soft_reg_banks is KIT-prep only; other selected clock keys stay freshness inputs."""
    raw,plan,ab,out=fixture(tmp_path)
    monkeypatch.setenv('OT_NATIVE_RESET_SCOPE','selected')
    raw['partition_types']['other']['clock']['taps'][0]['x']=99
    assert K.bind_matches(raw,'selected',out,str(ab),plan)
    cur=copy.deepcopy(raw)
    cur['partition_types']['selected']['clock']['soft_reg_banks']=[dict(id='b',source='nativeRTL:abc#b')]
    assert K.bind_matches(cur,'selected',out,str(ab),plan)
    cur['partition_types']['selected']['clock']['taps'][0]['x']=100
    assert not K.bind_matches(cur,'selected',out,str(ab),plan)


def _collector_fixture(tmp_path):
    before, plan, asbuilt, out = fixture(tmp_path)
    table = tmp_path / "landing.json"
    table.write_text("{}")
    asbuilt.write_text(json.dumps({"base": str(tmp_path), "clock_landing_table": table.name}))
    settled = {"rect_um": [30, 4, 70, 16], "instance": "u_cland_landing", "width": 9,
               "ring_width": 16, "clock_roles": {"local_read_flops": 16}}
    stale = dict(settled, rect_um=[80, 4, 120, 16])
    source = {"name": "landing", "node": "rst_n_t1", "band": stale}
    contract = {"bands": {"landing": settled}, "collector_local_sources": [source]}
    before["partition_types"]["selected"]["clock"]["landing_contract"] = contract
    plan.write_text(json.dumps(before))
    K.write_bind_receipt(before, out, asbuilt, plan_path=plan)
    provenance = {"step": "bind", "plan": str(plan),
                  "plan_sha256": hashlib.sha256(plan.read_bytes()).hexdigest()}
    (out / "provenance_bind.json").write_text(json.dumps({"provenance": provenance}))
    current = copy.deepcopy(before)
    _collector_contract(current)["collector_local_sources"][0]["band"] = copy.deepcopy(settled)
    assert K.native_contract(before, asbuilt, plan)["types"] != K.native_contract(current, asbuilt, plan)["types"]
    return current, plan, asbuilt, out


def _collector_contract(plan):
    return plan["partition_types"]["selected"]["clock"]["landing_contract"]


def test_collector_alias_exact_refresh_reuses_completed_bind(tmp_path):
    current, producer, asbuilt, out = _collector_fixture(tmp_path)
    receipt = out / "native_topology.json"
    old_bytes = receipt.read_bytes()
    current_path = tmp_path / "candidate.json"
    current_path.write_text(json.dumps(current))
    assert K.bind_matches(current, "selected", out, asbuilt, current_path)
    assert receipt.read_bytes() == old_bytes
    assert K.bind_matches(json.loads(producer.read_bytes()), "selected", out, asbuilt, producer)


def test_collector_alias_refuses_changes_to_active_source(tmp_path):
    current, plan, asbuilt, out = _collector_fixture(tmp_path)
    for location, field, value in (
        ("alias", "rect_um", [30, 5, 70, 16]),
        ("source", "node", "rst_n_t2"),
        ("source", "xy_um", [2, 3]),
        ("canonical", "rect_um", [30, 5, 70, 16]),
        ("canonical", "width", 8),
    ):
        mutant = copy.deepcopy(current)
        contract = _collector_contract(mutant)
        source = contract["collector_local_sources"][0]
        if location == "alias":
            source["band"][field] = value
        elif location == "source":
            source[field] = value
        else:
            contract["bands"]["landing"][field] = value
            source["band"][field] = value
        assert not K.bind_matches(mutant, "selected", out, asbuilt, plan)
    current["partition_types"]["other"]["buses"].append({"name": "unrelated", "dir": "in", "width": 1})
    assert not K.bind_matches(current, "selected", out, asbuilt, plan)


def test_collector_alias_requires_exact_producer_and_native_receipt(tmp_path):
    current, plan, asbuilt, out = _collector_fixture(tmp_path)
    producer_bytes = plan.read_bytes()
    plan.write_bytes(producer_bytes + b"\n")
    assert not K.bind_matches(current, "selected", out, asbuilt, plan)
    plan.write_bytes(producer_bytes)
    path = out / "native_topology.json"
    receipt = json.loads(path.read_bytes())
    receipt["types"]["other"] = "different"
    path.write_text(json.dumps(receipt))
    assert not K.bind_matches(current, "selected", out, asbuilt, plan)
