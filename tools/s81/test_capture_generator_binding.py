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
