"""AUTO-EXPORT-1118: sign-off hook spool, host probe, die inference, INDEX row."""
import hashlib, json, os, subprocess, sys
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
    u['signoff'] = str(Path('/srv/scratch') / Path(u['signoff']).relative_to(tmp_path))
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


def test_pending_late_lec_probe_checks_exact_routed_identity(tmp_path):
    import hashlib

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    kit = tmp_path / 'kit'
    base = kit / 'run' / 'results' / 'asap7' / 'test' / 'base'
    base.mkdir(parents=True)
    gate = base / '6_final.v'
    odb = base / '6_final.odb'
    gate.write_text('module test; endmodule')
    odb.write_bytes(b'original routed DB')
    so = kit / 'signoff.json'
    so.write_text(json.dumps(dict(profile='minimal', verdict='SIGNED', inputs=dict(kit=str(kit)))))
    proof = kit / 'lec_routed_exact' / 'lec.json'
    proof.parent.mkdir()
    row = dict(key='exact', signoff=str(so), record=sha(so), odb=str(odb), odb_sha=sha(odb), gate_sha=sha(gate))
    receipt = dict(netlist='/work/' + str(gate.relative_to(kit)), netlist_sha256=sha(gate), verdict='EQUIVALENT',
                   counts=dict(compare_points=4, proved=4, differs=0, undecided=0))

    def probe(overrides):
        proof.write_text(json.dumps(dict(receipt, **overrides)))
        completed = subprocess.run([sys.executable, '-I', '-', 'late-lec', json.dumps(dict(rows=[row]))],
                                   input=AE.PROBE, text=True, capture_output=True, check=True)
        return [json.loads(line) for line in completed.stdout.splitlines()]

    evidence, = probe({})
    assert evidence['sha'] == sha(proof)
    assert evidence['lec'] == dict(src=str(proof), verdict='EQUIVALENT', counts=receipt['counts'], identity='sha256')
    assert probe(dict(netlist='/work/other/6_final.v')) == []
    assert probe(dict(partition=dict(selected_points=4))) == []
    odb.write_bytes(b'changed routed DB')
    assert probe({}) == []


def test_pending_late_lec_refresh_preserves_archive_queue_identity(tmp_path, monkeypatch):
    import fcntl

    monkeypatch.setattr(AE, 'STATE', str(tmp_path))
    u = dict(state='meta', die='s81', unit='dsfd_node_LLd__ax_1234', element='dsfd_node_LLd', kind='c',
             host='epyc7', signoff='/kit/signoff.json', record='r', odb='/kit/base/6_final.odb',
             odb_sha='odb', bytes=25, files=[['/kit/base', '6_final.v']], shas={'6_final.v': 'gate'})
    unrelated = dict(u, record='untouched', state='done')
    AE.save_ledger(dict(units={'exact': u, 'unrelated': unrelated}))
    late = dict(key='exact', size=7, sha='proof',
                lec=dict(src='/kit/lec_routed_exact/lec.json', verdict='EQUIVALENT', counts={'compare_points': 4},
                         identity='sha256'))

    def probe(host, mode, argument, timeout):
        assert (host, mode) == ('epyc7', 'late-lec')
        assert argument['rows'] == [dict(key='exact', signoff=u['signoff'], record='r',
                                         odb=u['odb'], odb_sha='odb', gate_sha='gate')]
        return [late]

    monkeypatch.setattr(AE, 'probe', probe)
    with (tmp_path / 'drain.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        assert AE.refresh_pending_lec(['exact']) == 0
    assert AE.refresh_pending_lec(['exact', 'unrelated']) == 1
    assert AE.refresh_pending_lec(['exact']) == 0
    pending, = json.loads((tmp_path / 'pending_rtx.json').read_text())
    assert pending['key'] == 'exact' and pending['record'] == 'r' and pending['odb_sha'] == 'odb'
    assert pending['files'] == [['/kit/base', '6_final.v'], ['/kit/lec_routed_exact', 'lec.json']]
    assert pending['bytes'] == 32 and pending['shas']['lec.json'] == 'proof'
    assert pending['lec'] == late['lec']
    assert AE.load_ledger()['units']['unrelated'] == unrelated


def test_exact_diagnostic_receipt_stops_scan_and_preflight(tmp_path):
    folder = tmp_path / 'case'
    folder.mkdir()
    odb = folder / '6_final.odb'
    odb.write_bytes(b'0' * (2 << 20))
    signoff = folder / 'signoff.json'
    diagnostic = folder / 'diagnostic_signoff.json'
    ref = folder / 'SIGNOFF-DIAGNOSTIC-REF.json'
    raw = json.dumps(rec(odb=str(odb))).encode()
    signoff.write_bytes(raw)
    record = hashlib.sha256(raw).hexdigest()
    odb_sha = hashlib.sha256(odb.read_bytes()).hexdigest()
    args = dict(signoff=str(signoff), record=record, odb_sha256=odb_sha)

    def run(mode, values):
        completed = subprocess.run([sys.executable, '-I', '-', mode, json.dumps(values)],
                                   input=AE.PROBE, capture_output=True, text=True, check=True)
        return [json.loads(line) for line in completed.stdout.splitlines() if line.startswith('{')]

    assert run('signoff-source', args) == [{'state': 'ready'}]
    diagnostic.write_bytes(raw)
    ref.write_text(json.dumps(dict(schema='opentallas.auto_export.diagnostic_signoff.v1',
                                   record=record, odb_sha256=odb_sha)))
    assert run('signoff-source', args) == [{'state': 'diagnostic'}]
    assert run('scan', dict(hours=1, roots=[str(folder)])) == []
    assert AE.enqueue(str(diagnostic)) is None
    signoff.unlink()
    assert run('signoff-source', args) == [{'state': 'diagnostic'}]
    assert run('signoff-source', dict(args, odb_sha256='f' * 64)) == [{'state': 'missing'}]
    diagnostic.write_bytes(raw + b'\n')
    assert run('signoff-source', args) == [{'state': 'missing'}]
    signoff.write_bytes(raw + b'\n')
    assert run('signoff-source', args) == [{'state': 'changed'}]
    assert run('signoff-source', dict(args, record=hashlib.sha256(raw + b'\n').hexdigest())) == [{'state': 'ready'}]


def test_private_marker_blocks_canonical_report_at_every_export_entry(tmp_path, monkeypatch):
    import signoff as SO
    home = tmp_path / 'home'
    spool = home / AE.SPOOL_REL
    monkeypatch.setenv('OT_AUTO_EXPORT_SPOOL', str(spool))
    monkeypatch.setenv('OT_AUTO_EXPORT', '1')

    odb = tmp_path / '6_final.odb'
    odb.write_bytes(b'0' * (2 << 20))
    payload = rec(odb=str(odb))
    private = tmp_path / 'private'
    public = tmp_path / 'public'
    marked_output = private / 'signoff' / 'signoff.json'
    ordinary_output = public / 'signoff' / 'signoff.json'
    for report in (marked_output, ordinary_output):
        report.parent.mkdir(parents=True)
        report.write_text(json.dumps(payload))

    # A record left by an old bundle must also be excluded by the host probe.
    queued = Path(AE.enqueue(str(marked_output)))
    (private / 'DO_NOT_COUNT').touch()
    assert SO.auto_export_enqueue(marked_output, payload) is None
    assert AE.enqueue(str(marked_output)) is None
    assert list(spool.iterdir()) == [queued]

    def run(mode, values):
        env = dict(os.environ, HOME=str(home))
        completed = subprocess.run([sys.executable, '-I', '-', mode, json.dumps(values)],
                                   input=AE.PROBE, capture_output=True, env=env, text=True, check=True)
        return [json.loads(line) for line in completed.stdout.splitlines()]

    unit, = run('spool', {})
    assert unit['err'] == 'DO_NOT_COUNT sign-off'
    unit, = run('scan', dict(hours=1, roots=[str(tmp_path)]))
    assert unit['signoff'] == str(ordinary_output)
    for report, state in ((marked_output, 'diagnostic'), (ordinary_output, 'ready')):
        assert run('signoff-source', dict(signoff=str(report), record=hashlib.sha256(report.read_bytes()).hexdigest(),
                                         odb_sha256='f' * 64)) == [{'state': state}]


def _late_lec_fixture(tmp_path):
    import hashlib

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    kit = tmp_path / 'kit'
    base = kit / 'run' / 'results' / 'asap7' / 'test' / 'base'
    base.mkdir(parents=True)
    gate, odb = base / '6_final.v', base / '6_final.odb'
    gate.write_text('module test; endmodule')
    odb.write_bytes(b'routed DB')
    so = kit / 'signoff.json'
    so.write_text(json.dumps(dict(profile='minimal', verdict='SIGNED', inputs=dict(kit=str(kit)))))
    proof = kit / 'lec_routed_x' / 'lec.json'
    proof.parent.mkdir()
    row = dict(key='k', signoff=str(so), record=sha(so), odb=str(odb), odb_sha=sha(odb), gate_sha=sha(gate))
    receipt = dict(netlist='/work/' + str(gate.relative_to(kit)), netlist_sha256=sha(gate), verdict='EQUIVALENT',
                   counts=dict(compare_points=4, proved=4, differs=0, undecided=0))

    def probe(overrides=None, drop=(), row_over=None, mtime=None):
        r = dict(receipt, **(overrides or {}))
        for k in drop:
            r.pop(k)
        proof.write_text(json.dumps(r))
        if mtime is not None:
            os.utime(proof, (mtime, mtime))
        completed = subprocess.run([sys.executable, '-I', '-', 'late-lec', json.dumps(dict(rows=[dict(row, **(row_over or {}))]))],
                                   input=AE.PROBE, text=True, capture_output=True, check=True)
        return [json.loads(line) for line in completed.stdout.splitlines()]
    return probe, gate


def test_late_lec_not_attached_on_stale_mtime(tmp_path):
    probe, gate = _late_lec_fixture(tmp_path)
    assert len(probe()) == 1
    assert probe(mtime=os.path.getmtime(gate) - 100) == []


def test_late_lec_not_attached_on_non_equivalent(tmp_path):
    probe, _ = _late_lec_fixture(tmp_path)
    assert probe(dict(verdict='NOT EQUIVALENT')) == []
    assert probe(dict(verdict='UNPROVEN')) == []
    assert probe(dict(counts=dict(compare_points=4, proved=3, differs=1, undecided=0))) == []
    assert probe(dict(counts=dict(compare_points=4, proved=3, differs=0, undecided=1))) == []


def test_late_lec_not_attached_on_record_sha_mismatch(tmp_path):
    probe, _ = _late_lec_fixture(tmp_path)
    assert probe(row_over=dict(record='0' * 64)) == []
    assert probe(row_over=dict(gate_sha='0' * 64)) == []
    assert probe(row_over=dict(odb_sha='0' * 64)) == []


def test_late_lec_requires_recorded_netlist_sha256(tmp_path):
    probe, _ = _late_lec_fixture(tmp_path)
    assert len(probe()) == 1
    assert probe(drop=('netlist_sha256',)) == []
    assert probe(dict(netlist_sha256='0' * 64)) == []
    assert probe(dict(netlist_sha256=None)) == []


def test_rtx_pull_refresh_uses_configurable_hub_tool(tmp_path, monkeypatch):
    import argparse, stat

    home = tmp_path / 'home'
    state = home / '.local/state/ot-auto-export'
    state.mkdir(parents=True)
    pend = state / 'pending_rtx.json'
    unit = dict(key='k1', die='s81', unit='u1', record='r' * 64, mode='host', lec=None)
    pend.write_text(json.dumps([unit]))
    fake_ssh = tmp_path / 'fakessh'
    fake_ssh.write_text('#!/bin/bash\nshift\ncd "$HOME"\nexec bash -c "$1"\n')
    fake_ssh.chmod(fake_ssh.stat().st_mode | stat.S_IEXEC)
    seen = tmp_path / 'seen.json'
    tool = tmp_path / 'fake_tool.py'
    tool.write_text('import sys, json, pathlib\n'
                    'assert sys.argv[1] == "refresh-pending-lec"\n'
                    'pathlib.Path(%r).write_text(sys.stdin.read())\n'
                    'p = pathlib.Path(%r); d = json.loads(p.read_text()); d[0]["lec"] = dict(identity="sha256"); p.write_text(json.dumps(d))\n'
                    'print(1)\n' % (str(seen), str(pend)))
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('OT_AUTO_EXPORT_HUB_TOOL', str(tool))
    monkeypatch.setattr(AE, 'SSH', [str(fake_ssh), '-o', 'x'][:1])
    monkeypatch.setattr(AE, 'RTX_ROOT', str(tmp_path / 'rtx'))
    args = argparse.Namespace(hub='hub', refresh_lec_only=True, record=None)
    assert AE.rtx_pull(args) == 0
    assert json.loads(seen.read_text()) == ['k1']
    assert json.loads(pend.read_text())[0]['lec'] == dict(identity='sha256')
