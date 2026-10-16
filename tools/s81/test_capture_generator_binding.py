"""The flattened capture graph must consume the exact native views in GEN."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dsrom_s81_fulldie as G
from s81.capture_import import expand, DEFAULT_PACKET
import test_capture_import as fixture_module


def test_generator_binds_all_actual_capture_leaf_ports(tmp_path, monkeypatch):
    fixture_module.CaptureImport.setUpClass()
    fixture = fixture_module.CaptureImport()
    model = fixture.model()
    # Peers are outside this component; actual leaf direction/width evidence
    # comes from the full source graph and all native LEF contacts.
    model['glue'] = {}
    receipt = expand(model, packet=fixture.packet, inst_ctor=G.Inst)
    base = tmp_path / 'empty.json'
    base.write_text(json.dumps(dict(schema=G.VIEW_BINDING_SCHEMA,bound={})))
    monkeypatch.setenv('OT_S81_DIAGNOSTIC_CLOSED_VIEWS', '1')
    monkeypatch.delenv('OT_S81_VIEW_BINDING_SKIP_MISFIT', raising=False)
    monkeypatch.setattr(G, 'VIEW_BINDING', str(base))
    monkeypatch.setattr(G, 'CAPTURE_SOURCE_PACKET', DEFAULT_PACKET)
    monkeypatch.setattr(G, '_BOUND', {})
    monkeypatch.setattr(G, 'RTL_BIND', False)
    monkeypatch.setattr(G, 'ALIGN_JOGS', False)
    monkeypatch.setattr(G, 'SSTN_SPLIT_MAP', None)
    monkeypatch.setattr(G, 'RLY_FACE_PINS', False)
    monkeypatch.setattr(G, 'REAL_FILES', {})
    ports = G.finalize_r8(model)
    assert len(model['bound_views']) == 17
    assert sum(v['instances'] for v in model['bound_views'].values()) == 70
    for leaf in model['insts']:
        master = G.Q.Master(leaf.master, leaf.w, leaf.h, 3, 'actual capture leaf')
        G._LAY_K[0] = 1
        G._faces_r8(model, master, leaf, ports[leaf.master])
        G._require_physical_source_ports(master, ports[leaf.master])
        assert set(master.ports) == set(ports[leaf.master])
    assert G.die_master_params(model)['dsfd_capt_cd']['PINREG'] == 1
    assert len(receipt['clock_entries']) == 86


def test_generic_hop_repair_does_not_retime_fixed_capture_join(monkeypatch):
    a=G.Inst('a','native_a',0,0,10,10,kind='capture_leaf')
    b=G.Inst('b','native_b',1000,0,10,10,kind='capture_leaf')
    m=dict(insts=[a,b],buses=[('fixed','capture_internal',1,[('a','q'),('b','d')])])
    monkeypatch.setattr(G,'HOP_PLAN',{('a','q','b','d'):(1000,(5,5),(1005,5),None)})
    monkeypatch.setattr(G,'_corridors',lambda _: {})
    G._hop_fix(m,G.Placer(m))
    assert len(m['insts'])==2
    assert m['buses']==[('fixed','capture_internal',1,[('a','q'),('b','d')])]
    assert m['capture_internal_retime_protection']==[dict(bus='fixed',planned_loads=1)]
