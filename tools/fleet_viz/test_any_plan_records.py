"""any_plan_records: every signed record on any plan is listed, labelled with its plan, and counted per die (EXPLORER-STORE-R1)."""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import any_plan_records as APR  # noqa: E402

HEAD = 'die\telement\tkind\trecord\tdb\trtx_db\tsize\tsha256\tpack\tmeta\tstatus\tsrc'


def row(die, el, kind='t', status='ARCHIVED-BOTH', rtx=True):
    unit = '%s__ax_0123456789' % el
    return '\t'.join([die, el, kind, 'r', '', '/x/%s/%s/6_final.odb' % (die, unit) if rtx else '', '1', 'sha', '', '', status, 'src'])


def nodes():
    def n(nid, level, state, module=None):
        die, _, name = nid.split('.', 2)
        return dict(id=nid, level=level, die=die, name=name, status=dict(state=state), plan=dict(module=module) if module else {})
    N = [n('s81.t.col_a__clx', 'type', 'signed'), n('s81.t.col_b__cly', 'type', 'waiting'), n('s81.c.core_k', 'core', 'signed'),
         n('hbm.t.q_spb1', 'type', 'signed')]
    out = {x['id']: x for x in N}
    out['s81'] = dict(id='s81', level='die', die='s81')
    return out


def test_records_cover_every_plan_with_labels():
    tsv = '\n'.join([HEAD, row('s81', 'col_a__clx'), row('s81', 'col_a__clx__a2_0130', status='RTX-FULL-AGI-META'), row('s81', 'col_b__cly'),
                     row('s81', 'old_svc'), row('s81', 'core_k', kind='c'), row('s81', 'gone', status='NO-DB'), row('audit', 'x')])
    R = APR.build(nodes(), tsv, export_rows=[dict(die='hbm', name='q_spb1', odb='6_final.odb')],
                  store_entry=lambda rid: dict(id='m') if rid in ('s81.t.col_a__clx', 's81.t.old_svc') else None)
    # the re-sign variant folds into its node; NO-DB and non-die rows are not sign-offs of record
    assert set(R) == {'s81.t.col_a__clx', 's81.t.col_b__cly', 's81.t.old_svc', 's81.c.core_k', 'hbm.t.q_spb1'}
    assert R['s81.t.col_a__clx']['plan'] == 'current' and not R['s81.t.col_a__clx']['superseded']
    assert R['s81.t.col_b__cly']['superseded'] and 're-sign pending' in R['s81.t.col_b__cly']['plan_label']   # node exists, not signed now
    assert R['s81.t.old_svc']['superseded'] and 'retired plan' in R['s81.t.old_svc']['plan_label'] and R['s81.t.old_svc']['node'] is None
    assert R['s81.c.core_k']['level'] == 'core'
    assert R['hbm.t.q_spb1']['archive']['rtx'] and R['hbm.t.q_spb1']['archive']['status'] == 'RTX-ONLY'   # rtx-pro copy of a current sign-off without an INDEX row
    assert R['s81.t.col_a__clx']['archive']['units'][0] == 'col_a__clx__ax_0123456789'
    S = APR.summary(R)
    assert S['dies']['s81'] == dict(signed=4, archived=4, viewable=2, current=2, superseded=2, current_viewable=1, superseded_viewable=1)
    assert S['total']['signed'] == 5 and S['total']['viewable'] == 2


def test_current_signoff_without_archive_is_listed_unarchived():
    R = APR.build(nodes(), HEAD)
    assert set(R) == {'s81.t.col_a__clx', 's81.c.core_k', 'hbm.t.q_spb1'}
    assert all(not (r['archive']['agi'] or r['archive']['rtx']) for r in R.values())
    assert APR.summary(R)['total']['archived'] == 0


def test_record_id_scheme():
    assert APR.base_name('sle_fe_v1__cl82__ax_9b18360b43') == 'sle_fe_v1__cl82'
    assert APR.base_name('col__a3_0915') == 'col'
    assert APR.record_id('s81', 'c', 'col_a__clx', nodes()) == 's81.t.col_a__clx'   # only the type is a node: that level
    assert APR.record_id('s81', 'x', 'new') == 's81.t.new'


def test_archive_element_alias_record_id():
    # ARCHIVE-ALIAS-1124: the misnamed hd_tile export lands on the hd_tile record, with its unit listed
    nodes = {"s81_head.t.hd_tile": {"id": "s81_head.t.hd_tile", "die": "s81_head", "level": "type", "name": "hd_tile", "status": {"state": "signed"}}}
    tsv = ("die\telement\tkind\trecord\tdb\trtx_db\tsize\tsha256\tpack\tmeta\tstatus\tsrc\n"
           "s81_head\thd_tile_htr_eco1124\tt\tr\t/a/s81_head/hd_tile_htr_eco1124__ax_417e624cd7/6_final.odb\t\t1\ts\t\t\tRTX-FULL-AGI-META\tx\n")
    out = APR.build(nodes, tsv)
    assert list(out) == ["s81_head.t.hd_tile"]
    assert out["s81_head.t.hd_tile"]["archive"]["units"] == ["hd_tile_htr_eco1124__ax_417e624cd7"]
    assert APR.base_name("hd_tile_htr_eco1124") == "hd_tile_htr_eco1124"   # the alias is per die
