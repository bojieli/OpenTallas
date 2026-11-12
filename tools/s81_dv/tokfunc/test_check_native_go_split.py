"""DIE-S81-88 11-12: the gb_split qualification record's X-age basis (check_native_go_split.age_basis).

On the S81-FRAME-FIX-1 LP calendar (2-flop stations) the bench's own dd 0 station path equals the flat link of the bench
station e0 on x, go (seq leg and whole path) and go_tag, so X age 0 = dd 0.  A calendar at other station depths, or one
whose flat is not one uniform shift of the bench path, is refused."""
import json
import shutil
import sys
from pathlib import Path
import pytest
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(HERE.parent)]
import check_native_go_split as C  # noqa: E402
import station_depth as SD  # noqa: E402

LP = C.LP_SCHED.format(m='col_h10')


def cand(tmp, edit=None):
    """a candidate root carrying the station RTL and the col_h10 LP calendar of this tree (optionally edited)"""
    for f in SD.RTL_FILES + [LP]:
        (tmp / f).parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT / f, tmp / f)
    if edit is not None:
        lp = json.loads((tmp / LP).read_text()); edit(lp); (tmp / LP).write_text(json.dumps(lp))
    return tmp.resolve()


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('OT_S81_FRAME_SOURCE_ROOT', str(ROOT))   # age_basis re-points it; restored after each test
    monkeypatch.delenv('OT_S81_STATION_DEPTH_OVERRIDE', raising=False)


def test_fix1_calendar_offset_zero(tmp_path):
    off, basis = C.age_basis(cand(tmp_path), LP, 'col_h10')
    assert off == 0 and basis['x_age_minus_dd'] == 0
    assert basis['bench_base_edges'] == dict(x=5, go=2, go_path=5, go_tag=0) == basis['lp_flat_edges']
    assert basis['station_depth'] == json.loads((ROOT / LP).read_text())['station_depth']


def test_other_master_calendar_refused(tmp_path):
    with pytest.raises(AssertionError, match='field master'):
        C.age_basis(cand(tmp_path), C.LP_SCHED.format(m='col_h9'), 'col_h10')


def test_calendar_at_other_station_depths_refused(tmp_path):
    def legacy(lp):   # the pre-FIX-1 calendar carries no station_depth
        del lp['station_depth']
    with pytest.raises(AssertionError, match='other station depths'):
        C.age_basis(cand(tmp_path, legacy), LP, 'col_h10')


def test_non_uniform_shift_refused(tmp_path):
    def go_tag_late(lp):   # go_tag flat one edge off: x / go agree, go_tag does not
        lp['station_inputs']['e0']['control']['go_tag']['flat_link_edges'] += 1
    with pytest.raises(AssertionError, match='uniform shift'):
        C.age_basis(cand(tmp_path, go_tag_late), LP, 'col_h10')


def test_legacy_age_offset_unchanged():
    assert C.LEGACY_X_AGE_MINUS_DD == 2
