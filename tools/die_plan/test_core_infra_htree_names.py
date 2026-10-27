import itertools
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
import core_infra_htree as H


def test_legacy_single_digit_paths_identical():
    assert H.group_name(()) == 'R'
    for depth in range(1, 5):
        for path in itertools.product(range(10), repeat=depth):
            assert H.group_name(path) == 'T' + ''.join(map(str, path))


def test_pending_ep_nb11_paths_are_injective():
    # Actual pending EP planner: four islands, NB 5,5,11,11, leaf_n 4.
    groups = {()}
    for island, nb in enumerate((5, 5, 11, 11)):
        prefix = divmod(island, 2)
        for depth in (1, 2):
            groups.add(prefix[:depth])
        for branch in range(nb):
            groups.add(prefix + (branch,))
            groups.update(prefix + (branch, leaf) for leaf in range(4))
    names = [H.group_name(g) for g in groups]
    assert len(names) == len(set(names))
    assert H.group_name((1, 1, 10)) == 'TX1_1_10'
    assert H.group_name((1, 1, 1, 0)) == 'T1110'
    # Old naming demonstrably aliases this exact actual topology.
    assert len({'T' + ''.join(map(str, g)) for g in groups}) < len(groups)


def test_invalid_tokens_fail_closed():
    for bad in [(-1,), (1.0,), (True,)]:
        with unittest.TestCase().assertRaises(ValueError):
            H.group_name(bad)


def test_stale_duplicate_plan_rejected_before_lookup_or_output():
    for entry in ['model', 'emit_tcl', 'emit_sta']:
        with TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            P = {'nodes': [('T1110',), ('T1110',)], 'wires': []}
            with unittest.TestCase().assertRaisesRegex(ValueError, 'duplicate clock node'):
                if entry == 'model':
                    H.model(P, {}, 0, 0)
                elif entry == 'emit_tcl':
                    H.emit_tcl(P, tmp_path / 'clock.tcl')
                else:
                    H.emit_sta(P, tmp_path / 'sta', 0, 0)
            assert not list(tmp_path.iterdir())


if __name__ == '__main__':
    for test in [test_legacy_single_digit_paths_identical, test_pending_ep_nb11_paths_are_injective,
                 test_invalid_tokens_fail_closed, test_stale_duplicate_plan_rejected_before_lookup_or_output]:
        test()
        print(test.__name__, 'PASS')
