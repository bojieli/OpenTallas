import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_tree_plan as R


def rows(tmp_path, text):
    f = tmp_path / 'dedup_members.tsv'; f.write_text('die\tmember\towner\towner_job\tcredit_id\tidentity\n' + text)
    return R.dedup_rows(f)


def test_member_credited_via_owner(tmp_path):
    r = rows(tmp_path, 's81\tcol_h9_r1__t2__pvb\tcol_h9_r1__t1__pva\tj1\tddj1-abc\tabcdef0123456789\n')
    st = {'col_h9_r1__t1__pva': ['epyc7:/x/signoff.json SIGNED-NO-TAG']}
    tm = {'col_h9_r1__t1__pva': 'm', 'col_h9_r1__t2__pvb': 'm'}
    assert R.dedup_credit('s81', st, tm, r) == ['col_h9_r1__t2__pvb']
    assert 'via dedup col_h9_r1__t1__pva' in st['col_h9_r1__t2__pvb'][0]


def test_uncounted_owner_wrong_die_or_unplanned_member_credit_nothing(tmp_path):
    r = rows(tmp_path, 's81\tm1\to1\tj\tc\ti\ns81\tm2\to2\tj\tc\ti\nqwen_kvsys\tm3\to2\tj\tc\ti\n')
    st = {'o2': ['ref']}
    assert R.dedup_credit('s81', st, {'o1': 'x', 'o2': 'x', 'm1': 'x'}, r) == []   # m1: owner not counted; m2: not in plan; m3: other die
    assert set(st) == {'o2'}


def test_existing_credit_is_never_replaced(tmp_path):
    r = rows(tmp_path, 's81\tm\to\tj\tc\ti\n')
    st = {'o': ['a'], 'm': ['own record']}
    assert R.dedup_credit('s81', st, {'o': 'x', 'm': 'x'}, r) == [] and st['m'] == ['own record']


def test_plan_hosts_adds_the_marker_gen_hosts(tmp_path):
    import json, release_tree_plan as R
    (tmp_path / "tree_switch_x.json").write_text(json.dumps({"hosts": ["epyc10", "epyc7", "intel1", "epyc11"]}))
    got = R.plan_hosts(tmp_path)
    assert got[:len(R.HOSTS)] == list(R.HOSTS)
    assert {"epyc10", "epyc9", "epyc8", "epyc11"} <= set(got) and len(got) == len(set(got))
