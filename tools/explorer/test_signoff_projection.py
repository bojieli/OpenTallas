import json

import server


def test_any_plan_display_uses_current_geometry_and_qualified_packs(tmp_path, monkeypatch):
    def item(name, level='type'):
        return dict(name=name, level=level, key=name)

    def node(name, state, level='type', module=None, pack=None, children=()):
        nid = f"s81.{'t' if level == 'type' else 'c'}.{name}"
        return dict(id=nid, name=name, die='s81', level=level, status=dict(state=state),
                    plan=dict(module=module), layout=dict(store=pack), children=list(children))

    core = node('core', 'queued', level='core')
    fresh = node('fresh', 'signed', pack={'id': 'fresh-pack'})
    previous = node('previous', 'building', children=[core['id']])
    lagged = node('lagged', 'queued')
    other = node('other', 'waiting', module='old_only')
    uncredited = node('uncredited', 'signed', pack={'id': 'build-pack'})
    members = [fresh, previous, lagged, other, uncredited, core]
    partitions = [
        [f'p{i}', n['id'], 0, 0, 10, height, 'R0']
        for i, (n, height) in enumerate([(fresh, 1), (previous, 2), (previous, 3),
                                         (lagged, 4), (other, 5), (uncredited, 6)])
    ]
    raw_counts = dict(type={'signed': 2, 'building': 1, 'queued': 1, 'waiting': 1},
                      core={'queued': 1})
    die = dict(id='s81', die='s81', level='die', label='S81', counts=raw_counts,
               children=[n['id'] for n in members if n['level'] == 'type'],
               plan=dict(path='/p/current.json', outline=[100, 100], partitions=partitions))
    idx = dict(schema='test', generated=1, dies=['s81'], states=['signed', 'building', 'queued', 'waiting', 'not built'],
               nodes={n['id']: n for n in [die, *members]})
    census = dict(schema='opentallas.signoff_census.v1', summary={'signed': 6},
                  dies={'s81': dict(summary={'signed': 6}, current=[item('fresh')],
                                    deferred=[item('previous'), item('core', 'core')],
                                    retired=[item('lagged'), item('old_only'), item('missing_pack')])})
    index_file = tmp_path / 'index.json'
    index_file.write_text(json.dumps(idx))
    census_file = tmp_path / 'census.json'
    census_file.write_text(json.dumps(census))
    monkeypatch.setattr(server.design_service, 'INDEX', index_file)
    monkeypatch.setattr(server, 'DS', server.design_service.Service())
    monkeypatch.setattr(server, 'CENSUS', census_file)
    monkeypatch.setattr(server, '_CENSUS', (None, None, {}))
    monkeypatch.setattr(server, 'ARCHIVE_INDEX', tmp_path / 'archive.json')
    monkeypatch.setattr(server, '_REC', dict(key=None, recs={}))
    monkeypatch.setattr(server, 'audit_rows', lambda n: [])
    monkeypatch.setattr(server, 'db_sources', lambda n: {})
    rows = ['die\telement\tkind\tstatus'] + [
        f's81\t{name}\t{kind}\tARCHIVED'
        for name, kind in [('previous', 't'), ('lagged', 't'), ('old_only', 't'), ('missing_pack', 't'), ('core', 'c')]
    ]
    server.ARCHIVE_INDEX.write_text(json.dumps(dict(agidock_index_tsv='\n'.join(rows))))
    old_packs = {'s81.t.previous', 's81.t.old_only'}
    monkeypatch.setattr(server.design_index, 'store_entry', lambda nid: {'id': nid} if nid in old_packs else None)

    overview = server.dies()['dies'][0]
    detail = server.die('s81')
    assert overview['counts'] == detail['die']['counts'] == raw_counts
    assert overview['counts_any_plan'] == detail['die']['counts_any_plan']
    assert overview['counts_any_plan']['type']['signed'] == 3
    assert overview['counts_any_plan']['type']['uncredited'] == 1
    assert overview['counts_any_plan']['core']['signed'] == 1
    assert overview['instances']['by_state'] == dict(signed=2, building=2, queued=1, waiting=1)
    assert overview['instances']['by_state_any_plan'] == dict(signed=4, waiting=1, uncredited=1)
    assert overview['area_um2']['by_state']['signed'] == 70
    assert overview['area_um2']['by_state_any_plan'] == dict(signed=100, waiting=50, uncredited=60)
    assert overview['packs_signed_any_plan'] == dict(type=3, core=0)
    assert overview['packs_unsigned_any_plan'] == dict(type=1, core=0)
    assert detail['nodes'][lagged['id']]['signoff_basis'] == 'retired'
    assert detail['nodes'][other['id']]['signoff_display_state'] == 'waiting'
    assert detail['nodes'][uncredited['id']]['status']['state'] == 'signed'
    assert server.node(previous['id'])['children'][core['id']]['signoff_display_state'] == 'signed'

    census_file.unlink()
    assert server.die('s81')['die']['counts_any_plan']['type']['signed'] == raw_counts['type']['signed']
