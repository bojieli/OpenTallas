"""Exercise actual pin acceptance edges, not RTL arithmetic or timing claims."""
import pytest
from tools.gpu_sys.ds_hbm_sm_engine20 import SMEngine20
from tools.gpu_sys.ds_hbm_sm_engine20_guarded import SMEngine20Guarded
from tools.gpu_sys.test_ds_hbm_sm_engine20 import Pins, cpl


class AcceptingPins(Pins):
    def __init__(self):
        super().__init__()
        self.accepted = []

    def tick(self):
        for i, d in enumerate(self.dies):
            if d['cpl_v'] and self.driven[i]['cpl_rdy']:
                self.accepted.append((i, d['cpl_data']))
                d['cpl_v'] = 0
        super().tick()


def waiting(cls=SMEngine20Guarded):
    pins = AcceptingPins()
    engine = cls(pins, enable=True)
    engine.launch(entry_pc=19, token=128799, position=1048575, job=7, generation=3)
    for d in pins.dies:
        d['db_rdy'] = 1
    for _ in range(3):
        engine.poll()
    assert engine.state == 'WAIT'
    return pins, engine


@pytest.mark.parametrize('bad', [cpl(job=8), cpl(generation=2), cpl(position=9), cpl() ^ (1 << 37)])
def test_foreign_completion_preserves_producer_and_local_debt(bad):
    pins, engine = waiting()
    pins.dies[0].update(cpl_v=1, cpl_data=bad)
    pins.dies[1].update(cpl_v=1, cpl_data=cpl())
    before = pins.edges
    with pytest.raises(RuntimeError, match='identity/status'):
        engine.poll()
    assert pins.edges == before and pins.accepted == []
    assert all(d['cpl_v'] for d in pins.dies)
    assert engine.completed == {} and engine.receipt is None
    assert all(not p['cpl_rdy'] for p in pins.driven.values())


def test_delayed_valid_completions_accept_once_and_join():
    pins, engine = waiting()
    assert engine.poll() is None
    pins.dies[0].update(cpl_v=1, cpl_data=cpl())
    assert engine.poll() is None
    assert len(pins.accepted) == 1
    assert engine.poll() is None and len(pins.accepted) == 1
    pins.dies[1].update(cpl_v=1, cpl_data=cpl())
    receipt = engine.poll()
    assert receipt.cycles_by_die == (123, 123)
    assert len(pins.accepted) == 2
    before = pins.edges
    assert engine.poll() is receipt and pins.edges == before


def test_disagreeing_result_remains_held_after_first_valid_die():
    pins, engine = waiting()
    pins.dies[0].update(cpl_v=1, cpl_data=cpl())
    engine.poll()
    pins.dies[1].update(cpl_v=1, cpl_data=cpl(token=55))
    before = pins.edges
    with pytest.raises(RuntimeError, match='RESULT mismatch'):
        engine.poll()
    assert pins.edges == before and len(pins.accepted) == 1
    assert pins.dies[1]['cpl_v'] and set(engine.completed) == {0}


def test_original_exposes_the_wrong_ack_regression():
    pins, engine = waiting(SMEngine20)
    pins.dies[0].update(cpl_v=1, cpl_data=cpl(generation=2))
    with pytest.raises(RuntimeError, match='identity/status'):
        engine.poll()
    assert len(pins.accepted) == 1  # Negative retained; successor must not do this.


def test_explicit_enable_is_required():
    with pytest.raises(ValueError, match='explicit enable'):
        SMEngine20Guarded(AcceptingPins())
