import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('idx_row_pitch_price', HERE / 'idx_row_pitch_price.py')
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
C = P.load_compiler()


def pitches(rt, vp=1):
    _, meta, occ = P.frame(C, rt, vp)
    return (P.min_pitch(occ, 6, None, meta), P.min_pitch(occ, 6, 0, meta), P.min_pitch(occ, 6, rt - 2, meta))


def test_donor_reader_drain_not_binding():
    cls, at_launch, delayed = pitches(2)
    assert cls == at_launch == delayed == 328


def test_actual_reader_clear_at_launch_costs_pitch():
    cls, at_launch, delayed = pitches(173)
    assert (cls, at_launch, delayed) == (328, 383, 328)


def test_actual_reader_vm_period2():
    cls, at_launch, delayed = pitches(171, 2)
    assert (cls, at_launch, delayed) == (346, 510, 346)


def test_clear_too_late_is_illegal():
    _, meta, occ = P.frame(C, 173, 1)
    ok, why = P.legal(occ, 328, 6, 10_000, meta)
    assert not ok and 'first block' in why
