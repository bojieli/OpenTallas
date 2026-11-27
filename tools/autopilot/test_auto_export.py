"""AUTO-EXPORT-1118: sign-off hook spool, host probe, die inference, INDEX row."""
import json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'die_plan'))
import auto_export as AE  # noqa: E402


def rec(verdict='SIGNED', profile='minimal', odb=None, kit=None):
    return dict(name='x', generated='2026-11-18T12:00:00+00:00', host=None, profile=profile, verdict=verdict,
                inputs=dict(odb=odb, kit=kit), checks=dict(setup_tt=dict(wns_ps=-1.0), hold_ff=dict(wns_ps=0.0)))


def test_enqueue_only_r_minimal_pass(tmp_path, monkeypatch):
    monkeypatch.setenv('OT_AUTO_EXPORT_SPOOL', str(tmp_path / 'spool'))
    for i, (v, p) in enumerate((('SIGNED', 'minimal'), ('NOT SIGNED', 'minimal'), ('SIGNED', 'legacy'))):
        so = tmp_path / ('s%d' % i) / 'signoff.json'
        so.parent.mkdir()
        so.write_text(json.dumps(rec(v, p)))
        got = AE.enqueue(str(so), die='s81')
        assert (got is not None) == (i == 0)
    rows = [json.loads(f.read_text()) for f in (tmp_path / 'spool').iterdir()]
    assert len(rows) == 1 and rows[0]['die'] == 's81' and len(rows[0]['record']) == 64


def test_signoff_hook_spools(tmp_path, monkeypatch):
    import signoff as SO
    monkeypatch.setenv('OT_AUTO_EXPORT_SPOOL', str(tmp_path / 'sp'))
    so = tmp_path / 'signoff.json'
    so.write_text('{}')
    assert SO.auto_export_enqueue(so, rec()) is not None
    assert SO.auto_export_enqueue(so, rec('NOT SIGNED')) is None
    monkeypatch.setenv('OT_AUTO_EXPORT', '0')
    assert SO.auto_export_enqueue(so, rec()) is None
    assert len(list((tmp_path / 'sp').iterdir())) == 1


def test_probe_scan_spool_hash(tmp_path):
    home = tmp_path / 'home'
    base = tmp_path / 'claude' / 'fable-fix-s81-x' / 'work' / 'base'
    base.mkdir(parents=True)
    (base / '6_final.odb').write_bytes(b'\0' * (2 << 20))
    (base / '6_final.v').write_text('module m; endmodule\n')
    (base / 'm.lef').write_text('MACRO m\n')
    (base / 'render.png').write_bytes(b'png')
    kit = tmp_path / 'claude' / 'fable-fix-s81-x' / 'work'
    (kit / 'config.mk').write_text('export DESIGN_NAME = ot_top_m\n')
    sod = tmp_path / 'claude' / 'fable-fix-s81-x' / 'signoff'
    sod.mkdir()
    (sod / 'signoff.json').write_text(json.dumps(rec(odb=str(base / '6_final.odb'), kit=str(kit))))
    (sod / 'lec.json').write_text('{}')
    env = dict(os.environ, HOME=str(home))

    def run(mode, arg):
        r = subprocess.run([sys.executable, '-I', '-', mode, json.dumps(arg)], input=AE.PROBE, text=True,
                           capture_output=True, env=env, check=True)
        return [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{')]
    u, = run('scan', dict(hours=1, roots=[str(tmp_path / 'claude')]))
    assert u['top'] == 'ot_top_m' and [f for _, f in u['files']] == ['6_final.odb', '6_final.v', 'lec.json', 'signoff.json']
    assert sorted(os.path.basename(f) for _, f in u['display']) == ['m.lef', 'render.png']
    assert [f for _, f in AE.meta_files(u)] == ['lec.json', 'signoff.json']     # AGIdock never gets the 6_final.* DB files
    # VIEW-FF-1125: the sign-off timing models travel with the full record and the view pack, above the 50 MB render cap
    with open(sod / 'ot_top_m_ff.lib', 'wb') as f:
        f.truncate(60 << 20)
    (sod / 'ot_top_m_tt.lib').write_text('library (ot_top_m_tt) {}\n')
    with open(base / 'huge_render.png', 'wb') as f:
        f.truncate(60 << 20)
    u, = run('scan', dict(hours=1, roots=[str(tmp_path / 'claude')]))
    assert [f for _, f in u['files']] == ['6_final.odb', '6_final.v', 'lec.json', 'ot_top_m_ff.lib', 'ot_top_m_tt.lib', 'signoff.json']
    assert sorted(os.path.basename(f) for _, f in u['display']) == ['m.lef', 'ot_top_m_ff.lib', 'ot_top_m_tt.lib', 'render.png']
    assert [f for _, f in AE.meta_files(u)] == ['lec.json', 'ot_top_m_ff.lib', 'ot_top_m_tt.lib', 'signoff.json']
    (sod / 'ot_top_m_ff.lib').unlink(); (sod / 'ot_top_m_tt.lib').unlink(); (base / 'huge_render.png').unlink()
    h, = run('hash', dict(paths=[str(base / '6_final.odb')]))
    assert h[str(base / '6_final.odb')][1] == 2 << 20
    os.environ['OT_AUTO_EXPORT_SPOOL'] = str(home / AE.SPOOL_REL)
    try:
        AE.enqueue(str(sod / 'signoff.json'))
    finally:
        del os.environ['OT_AUTO_EXPORT_SPOOL']
    s, = run('spool', {})
    assert s['odb'] == str(base / '6_final.odb') and s['spool'].endswith('.json')
    u['host'], u['hint'] = 'epyc7', {}
    die, el, kind, how = AE.infer(u, [])
    assert (die, el, how) == ('s81', 'ot_top_m', 'lane dir')


def test_infer_order_and_row():
    rows = [['s81_head', 'hd_serdes', 't', 'r', 'db', 'rdb', '1', 'sha', '', 'm', 'ARCHIVED-BOTH', 'x']]
    u = dict(signoff='/srv/s/claude/kv-lane/a/signoff.json', top='hd_serdes', hint={})
    assert AE.infer(u, rows)[0] == 's81_head'          # INDEX element beats the lane dir
    u = dict(signoff='/srv/s/claude/w/runs/qwen_kvsys/kit-wave/qwen_kvsys/e/items/i/attempt_1/signoff/signoff.json', top='m', hint={})
    assert AE.infer(u, rows)[:2] == ('qwen_kvsys', 'i')
    u = dict(signoff='/srv/s/claude/autopilot/closed/s81_head/hd_st_str__8569788b03/kit/signoff/signoff.json', top='ot_s81hd_st_str', hint={})
    assert AE.infer(u, rows)[:2] == ('s81_head', 'hd_st_str')
    u = dict(signoff='/srv/s/claude/zz/signoff.json', top='zz_m', hint={'die': 'hbm', 'kind': 'c'})
    assert AE.infer(u, rows) == ('hbm', 'zz_m', 'c', 'hint')
    u = dict(die='s81', unit='m__ax_0123456789', element='m', kind='t', record='r' * 64, odb_size=5, odb_sha='a' * 64, src='s')
    c = AE.index_row(u).rstrip('\n').split('\t')
    assert len(c) == 12 and c[4] == '/archive/opentallas-signed-1114/s81/m__ax_0123456789/6_final.odb' and c[10] == 'ARCHIVED-BOTH'
    c = AE.index_row(dict(u, state='meta', display=[('d', 'm.lef')])).rstrip('\n').split('\t')
    assert c[4] == '' and c[5].startswith('/home/ubuntu/signed-export-1114/s81/') and c[8] == 's81/m__ax_0123456789/display'
    assert c[10] == 'RTX-FULL-AGI-META'


def test_unit_carries_landing_evidence_and_view_pack(tmp_path):
    base = tmp_path / 'claude' / 'k' / 'work' / 'base'
    base.mkdir(parents=True)
    (base / '6_final.odb').write_bytes(b'\0' * (2 << 20))
    kit = tmp_path / 'claude' / 'k' / 'work'
    (kit / 'config.mk').write_text('export DESIGN_NAME = ot_top_m\n')
    (kit / 'land_slots.json').write_text('{}')
    (kit / 'face_guard.json').write_text('{}')
    (kit / 'results').mkdir()
    (kit / 'results' / '1_synth.v').write_text('module m; endmodule\n')
    sod = tmp_path / 'claude' / 'k' / 'signoff'
    (sod / 'views' / 'm').mkdir(parents=True)
    (sod / 'views' / 'm' / 'gates.json').write_text('{}')
    (sod / 'signoff.json').write_text(json.dumps(rec(odb=str(base / '6_final.odb'), kit=str(kit))))
    env = dict(os.environ, HOME=str(tmp_path / 'home'))
    r = subprocess.run([sys.executable, '-I', '-', 'scan', json.dumps(dict(hours=1, roots=[str(tmp_path / 'claude')]))], input=AE.PROBE, text=True, capture_output=True, env=env, check=True)
    u = [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{')][0]
    names = {f for _, f in u['files']}
    assert {'land_slots.json', 'face_guard.json', '1_synth.v', 'views/m/gates.json'} <= names
    got = {f for _, f in AE.meta_files(dict(files=[tuple(x) for x in u['files']]))}
    assert '1_synth.v' not in got and 'views/m/gates.json' not in got and 'land_slots.json' in got   # big evidence stays rtx-pro only


def test_legacy_record_shas_cover_empty_record_rows(tmp_path):
    """FLEET-OPS 11-25: an INDEX row with an empty record column still exports the signoff.json stored next to its DB"""
    import hashlib
    u = tmp_path / "qwen_compute" / "sta_x"
    u.mkdir(parents=True)
    (u / "signoff.json").write_text("{\"verdict\": \"SIGNED\"}")
    (u / "6_final.odb").write_bytes(b"x")
    rows = ["qwen_compute\tsta_x\tc\t\t/archive/a/6_final.odb\t%s\t1\t%s\tp\tm\tARCHIVED-BOTH\ts" % (u / "6_final.odb", "a" * 64),
            "qwen_compute\tsta_y\tc\t%s\t\t%s\t1\t%s\tp\tm\tARCHIVED-BOTH\ts" % ("b" * 64, u / "6_final.odb", "c" * 64)]
    (tmp_path / "INDEX.tsv").write_text("\n".join(rows) + "\n")
    got = AE.legacy_record_shas(str(tmp_path), str(tmp_path / "cache.json"))
    assert got == [hashlib.sha256(b"{\"verdict\": \"SIGNED\"}").hexdigest()]


def test_unit_carries_kit_routed_lec_and_sidecar_row(tmp_path, monkeypatch):
    """LEC-R2 11-26: a kit's lec_routed*/lec.json (EQUIVALENT, not older than 6_final.v) travels as lec.json; INDEX-LEC.tsv row carries its sha"""
    import hashlib, time
    base = tmp_path / 'claude' / 'k' / 'work' / 'base'
    base.mkdir(parents=True)
    (base / '6_final.odb').write_bytes(b'\0' * (2 << 20))
    (base / '6_final.v').write_text('module m; endmodule\n')
    kit = tmp_path / 'claude' / 'k' / 'work'
    (kit / 'config.mk').write_text('export DESIGN_NAME = ot_top_m\n')
    nlk = kit / 'run' / 'results' / 'asap7' / 'm' / 'base'
    nlk.mkdir(parents=True)
    (nlk / '6_final.v').write_text('module m; endmodule\n')
    sod = tmp_path / 'claude' / 'k' / 'signoff'
    sod.mkdir()
    (sod / 'signoff.json').write_text(json.dumps(rec(odb=str(base / '6_final.odb'), kit=str(kit))))
    env = dict(os.environ, HOME=str(tmp_path / 'home'))

    def scan():
        r = subprocess.run([sys.executable, '-I', '-', 'scan', json.dumps(dict(hours=1, roots=[str(tmp_path / 'claude')]))], input=AE.PROBE, text=True, capture_output=True, env=env, check=True)
        return [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{')][0]
    time.sleep(0.05)
    (kit / 'lec_routed_relec1122').mkdir()
    bad = kit / 'lec_routed_relec1122' / 'lec.json'
    bad.write_text(json.dumps(dict(verdict='NOT EQUIVALENT')))
    assert scan()['lec'] is None and 'lec.json' not in {f for _, f in scan()['files']}        # only EQUIVALENT travels
    body = json.dumps(dict(verdict='EQUIVALENT', counts=dict(compare_points=7, proved=7)))
    bad.write_text(body)
    u = scan()
    assert ('lec.json' in {f for _, f in u['files']}) and u['lec']['identity'] == 'size' and u['lec']['counts']['compare_points'] == 7
    u['shas'] = {'lec.json': hashlib.sha256(body.encode()).hexdigest()}
    u['odb_sha'] = 'a' * 64
    # Exercise the hub-to-RTX queue boundary used by the real drain.
    monkeypatch.setattr(AE, 'STATE', str(tmp_path))
    AE.save_ledger({'units': {'new': dict(u, state='meta'),
                              'legacy': {'state': 'agi', 'record': 'legacy'}}})
    pending, legacy = json.loads((tmp_path / 'pending_rtx.json').read_text())
    assert pending['lec'] == u['lec']
    assert AE.lec_index_row(legacy) == ''
    c = AE.lec_index_row(pending).rstrip('\n').split('\t')
    assert c[0] == u['record'] and c[1] == u['odb_sha'] and c[2] == u['shas']['lec.json'] and c[3] == 'EQUIVALENT' and c[4] == '7' and c[5] == 'size'
    assert AE.lec_index_row(dict(u, lec=None)) == ''
    os.utime(bad, (1, 1))                                                                       # older than 6_final.v: not picked up
    assert scan()['lec'] is None
