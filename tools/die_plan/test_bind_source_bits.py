"""Exact LSB packing authority for actual compiled-source projections."""
import sys
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bind


def test_noncontiguous_source_bits_and_forwarded_position_are_preserved():
    F=NS(cells=[NS(path="die.real_producer")])
    L={"items": [("leaf",0,"payload",3),("leaf",0,"payload",0),
                 ("fwd",{"lane":"host_to_cw","iname":"old_i"},17),
                 ("leaf",0,"payload",7),("leaf",0,"valid",0)]}
    assert bind._source_bits(L,F) == [["leaf","die.real_producer","payload",3],
        ["leaf","die.real_producer","payload",0],["forward","host_to_cw",17],
        ["leaf","die.real_producer","payload",7],["leaf","die.real_producer","valid",0]]
