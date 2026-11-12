"""row_gather_rows --issue-cadence: off byte-identical to base; on (ISS2E) stage edges re-derived from rows + pad parity."""
import hashlib, os, subprocess, sys, tempfile
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import row_gather_rows as R  # noqa: E402
import iss2e_pad as I  # noqa: E402
import argmax_rows as A  # noqa: E402


@pytest.mark.parametrize('vm_rt,wire', [(81, 453), (3, 453), (74, 453)])
def test_c2_stage_edges_equal_v8_edges(vm_rt, wire):
    rows, par, e = R.stages_rows(3, wire, vm_rt)
    ref = e['REQV']
    for k in e:
        # edge of stage k at cadence 2 = 2 * row + pad parity; relative to the VM request it must equal the v8 edge gap
        assert (2 * rows[k] + par[k]) - (2 * rows['REQV'] + par['REQV']) == e[k] - ref, k
    assert par['REQV'] == 0


def test_c2_odd_wire_flips_rx_parities_and_conflicts_or_not_deterministically():
    # wire 454 flips every RX-side parity; the union with the ARGMAX variant is then re-checked (conflict is a hard error)
    R.ARG_VARIANT = (True, True)
    try:
        R.pad_mask(3, 454, 81)
    except ValueError as ex:
        assert 'conflict' in str(ex)
    R.ARG_VARIANT = (False, False)


def test_base_argmax_conflicts_with_gather_pr_and_startreg_variant_agree():
    R.ARG_VARIANT = (False, False)
    with pytest.raises(ValueError, match='conflict at uop bit 13'):
        R.pad_mask(3, 453, 81)
    for v in ((True, True), (False, True)):
        R.ARG_VARIANT = v
        u, par = R.pad_mask(3, 453, 81)
        assert u[13] == 0 and u[705 if not v[0] else 706] in (0, 1)
    R.ARG_VARIANT = (False, False)


def test_c2_mask_is_the_union_and_same_for_argmax_manifest():
    R.ARG_VARIANT = (True, True)
    u, _ = R.pad_mask(3, 453, 81)
    A.START_O = -1; A.set_arg_pr_source(True)
    ma = I.arg_bit_parity(A.field_parity(81))
    A.START_O = 0; A.set_arg_pr_source(False)
    assert all(u[b] == p for b, p in ma.items())
    R.ARG_VARIANT = (False, False)


def test_c1_off_identical_to_base():
    rev = os.environ.get('ARGMAX_BASE_REV')
    if not rev:
        pytest.skip('set ARGMAX_BASE_REV=<rev before the change>')
    old = subprocess.run(['git', '-C', str(HERE), 'show', f'{rev}:tools/hbm_coll_static/row_gather_rows.py'], capture_output=True, check=True)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); (d / 'tools/hbm_coll_static').mkdir(parents=True)
        (d / 'tools/hbm_coll_static/row_gather_rows.py').write_bytes(old.stdout)
        (d / 'rtl').symlink_to(R.ROOT / 'rtl')
        for P, vm_rt, extra in ((1, 0, []), (6, 81, []), (3, 74, ['--mutant', 'row_stride']), (2, 81, ['--mutant', 'link_step'])):
            outs = []
            for tag, tool in (('old', d / 'tools/hbm_coll_static/row_gather_rows.py'), ('new', HERE / 'row_gather_rows.py')):
                o = d / f'{tag}_{P}_{vm_rt}_{len(extra)}'
                subprocess.run([sys.executable, '-I', str(tool), str(o), '--P', str(P), '--vm-rt', str(vm_rt)] + extra, check=True,
                               capture_output=True, cwd=str(HERE))
                outs.append({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(o.iterdir())})
            assert outs[0] == outs[1], (P, vm_rt, extra)
