"""TOK-HBM-1: four_role_calendar.py -> fused_job217_emit.py round trip (fake ISA decoder; real emitter checks)."""
import json, subprocess, sys, types
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import four_role_calendar as FRC

FAKE_IR = '''
import types
class D:
    def __init__(s, base, n): s.base=base; s.n=n; s.m=1; s.stride=0; s.istride=1; s.fmt='fp32'
def decode_one(raw, off):
    op = 'HC_POST' if raw[off] else 'HC_PRE'; nm = raw[off+1]
    sz = dict(zip('ABCO', [5120,20480,20,20480] if op=='HC_POST' else [20480,5120,4,5120]))
    desc = {k: D(8*(i+1)*(off+1), sz[k]) for i,k in enumerate('ABCO')}
    r = types.SimpleNamespace(unit='FUSED', op=op, imm_a=0x3727c5ac, desc=desc)
    rx = types.SimpleNamespace(n=nm, rsel=0, emask=0, slot0=0, rgap=0, rs={}) if nm>1 else None
    return r, rx, off+2
'''
FAKE_FC = "FUSED_OPS={'HC_PRE','HC_POST'}\ndef check_fused(r,rx): return None\n"


def setup(tmp):
    ct = tmp / 'ct'; (ct / 'hbm_next').mkdir(parents=True)
    (ct / 'isa_rows.py').write_text(FAKE_IR); (ct / 'hbm_next' / 'fused_phase_check.py').write_text(FAKE_FC)
    img = tmp / 'img.bin'; img.write_bytes(bytes([0, 1, 1, 6, 0, 2]))
    return ct, img


def bound():
    legs = dict(reset_SW=9, reset_SE=11, reset_NW=7, reset_NE=8, reset_root=2, host_to_provider=5, provider_to_root=6,
                root_to_provider=6, down_NW=14, down_NE=12, up_NW=15, up_NE=13)
    return dict(source_plan_commit='a' * 40, plan_sha256='x',
                legs={k: dict(cycles=v, source='test') for k, v in legs.items()},
                rtl={k: dict(value=v, source='test') for k, v in dict(rr=10, reset_release_edges=66,
                                                                      reset_sync_stages=3, host_write_interval=1).items()})


SERVICE = dict(source='test', cycles={'HC_PRE/1': 300, 'HC_POST/6': 5760, 'HC_PRE/2': 420})


def emit(emitter, ct, img, out, cal=None):
    cmd = [sys.executable, str(emitter), '--image', str(img), '--compiler-tools', str(ct), '--out', str(out)]
    if cal: cmd += ['--calendar', str(cal)]
    return subprocess.run(cmd, capture_output=True, text=True)


EMITTER = Path(__import__('os').environ.get('EMITTER', HERE / 'fused_job217_emit.py'))


def test_round_trip_compiles(tmp_path):
    ct, img = setup(tmp_path)
    r = emit(EMITTER, ct, img, tmp_path / 'p1'); assert r.returncode == 2
    jobs = json.loads((tmp_path / 'p1' / 'jobs.json').read_text()); assert len(jobs['jobs']) == 3
    cal, miss = FRC.compile_calendar(jobs, bound(), SERVICE); assert not miss, miss
    assert cal['root_config'] == dict(wsc=(14 + 15) + 10 + 8, pk5=(14 + 15) - (12 + 13), pb5=1)
    assert cal['boot_release_offsets'] == dict(SW=78, SE=80, NW=76, NE=77, root=71)
    (tmp_path / 'cal.json').write_text(json.dumps(cal))
    r = emit(EMITTER, ct, img, tmp_path / 'p2', tmp_path / 'cal.json'); assert r.returncode == 0, r.stdout + r.stderr
    rc = json.loads((tmp_path / 'p2' / 'jobs.json').read_text())
    assert rc['status'] == 'COMPILED_OPT_IN' and rc['entries'] == 3
    assert len((tmp_path / 'p2' / 'programme.mem').read_text().split()) == 3


@pytest.mark.parametrize('mut', ['no_leg', 'no_service', 'bad_sha', 'early_start', 'wrong_pad', 'swap_roles'])
def test_mutants_fail_closed(tmp_path, mut):
    ct, img = setup(tmp_path)
    emit(EMITTER, ct, img, tmp_path / 'p1'); jobs = json.loads((tmp_path / 'p1' / 'jobs.json').read_text())
    b = bound(); svc = json.loads(json.dumps(SERVICE))
    if mut == 'no_leg':
        del b['legs']['up_NE']; cal, miss = FRC.compile_calendar(jobs, b, svc); assert cal is None and miss; return
    if mut == 'no_service':
        del svc['cycles']['HC_POST/6']; cal, miss = FRC.compile_calendar(jobs, b, svc); assert cal is None and miss; return
    if mut == 'bad_sha':
        b['source_plan_commit'] = 'HEAD'; cal, miss = FRC.compile_calendar(jobs, b, svc); assert cal is None and miss; return
    cal, miss = FRC.compile_calendar(jobs, b, svc); assert not miss
    if mut == 'early_start': cal['provider_start_cycle'] -= 40                     # START before resets + warm
    if mut == 'wrong_pad': cal['records'][1]['root_capture_cycle'] += 1             # off-by-one ingress accounting
    if mut == 'swap_roles': cal['roles'] = dict(NWq0='NW', NEq0='NE', NWq1='SW', NEq1='SE')
    (tmp_path / 'cal.json').write_text(json.dumps(cal))
    r = emit(EMITTER, ct, img, tmp_path / 'p2', tmp_path / 'cal.json'); assert r.returncode == 2
    assert not (tmp_path / 'p2' / 'programme.mem').exists()


def test_hub_tree_pads_rule():
    def st(c, n): return dict(conn='mu_tree:' + c, regs_um=[[0, 0]] * n)
    # n4 children n3a (leaf-like, no kids) and n3b; down/up legs give round trips 2+3=5 and 4+4=8
    stations = [st('n3a.uo|n4', 3), st('n4.da|n3a', 2), st('n3b.uo|n4', 4), st('n4.db|n3b', 4)]
    plan = dict(partition_types=dict(h=dict(internal_stations=stations)))
    r = FRC.hub_tree_pads(plan, hubs=(('h', 'NW'),), top='n4')['NW']
    assert r['round_trip_regs'] == 8 and r['pads'] == {'n4': [3, 0]}   # child a earlier -> pad a by 3
