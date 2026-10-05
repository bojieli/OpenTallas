import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('baseline',ROOT/'tools/w17_window_connected_baseline.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
BENCH=(ROOT/gate.BENCH).read_text()

def receipt():
    pcs='\n'.join(f'PC_DRAIN pc={p} reads=68 q=0 r=0 refreshes=1000 activations=68' for p in range(32))
    return pcs+'\nCONNECTED_WINDOW_PASS start=12300 staged=136669 done=136800 refill=124368 reads=2176 replies=2176 beats=32 max_inflight=1\n'

def test_fixed_geometry():
    assert gate.validate_fixture(BENCH)==dict(LENW=4,BEATW=4,packed_length_bits=128,packed_beat_bits=128)

@pytest.mark.parametrize('bad',[
    BENCH.replace('.LENW(4),',''),BENCH.replace('.LENW(4)','.LENW(5)'),
    BENCH.replace('.BEATW(4),',''),BENCH.replace('[127:0] hl,rb','[159:0] hl,rb'),
    BENCH.replace('k_len(ml[8+:4])','k_len(ml[8+:5])'),
    BENCH.replace('.TAGW(17)','.TAGW(16)'),BENCH.replace('.NPC(32)','.NPC(16)'),
    BENCH.replace('.TAGW(16)) arb','.TAGW(16),.LENW(5)) arb'),
])
def test_reject_bad_fixture_before_build(bad):
    with pytest.raises(ValueError):gate.validate_fixture(bad)

def test_complete_receipt():
    metrics,pcs=gate.validate_receipt(receipt())
    assert metrics['reads']==2176 and len(pcs)==32 and pcs[31]['r']==0

@pytest.mark.parametrize('bad',[
    receipt().replace('pc=31 reads=68','pc=30 reads=68'),
    receipt().replace('PC_DRAIN pc=31 reads=68 q=0 r=0 refreshes=1000 activations=68\n',''),
    receipt().replace('pc=31 reads=68','pc=32 reads=68'),
    receipt().replace('pc=31 reads=68','pc=31 reads=67'),
    receipt().replace('pc=31 reads=68 q=0','pc=31 reads=68 q=1'),
    receipt().replace('pc=31 reads=68 q=0 r=0','pc=31 reads=68 q=0 r=1'),
    receipt().replace('replies=2176','replies=2175'),
    receipt().replace('max_inflight=1','max_inflight=2'),
    receipt().replace('beats=32','beats=31'),
    receipt().replace('staged=136669','staged=12300'),
    receipt().replace('done=136800','done=200001'),
    receipt()+'CONNECTED_WINDOW_PASS garbage\n',
    receipt()+'PC_DRAIN pc=0 reads=68 q=0 r=0 refreshes=1 activations=1\n',
    receipt()+'%Fatal: assertion failed\n',
])
def test_reject_incomplete_or_corrupt_receipt(bad):
    with pytest.raises(ValueError):gate.validate_receipt(bad)

def test_prebuild_width_failure_has_no_side_effects(monkeypatch,tmp_path):
    root=tmp_path/'root';(root/gate.BENCH).parent.mkdir(parents=True)
    (root/gate.BENCH).write_text(BENCH.replace('.LENW(4),',''))
    monkeypatch.setattr(gate,'ROOT',root)
    monkeypatch.setattr(gate.subprocess,'check_output',lambda *a,**k:pytest.fail('source fetch/build before width guard'))
    out=tmp_path/'attempt'
    with pytest.raises(ValueError,match='LENW'):gate.run(out,0)
    assert not out.exists()
