"""Native envelope growth must precede placement, without changing tile ABI."""
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dsrom_s81_fulldie as G


def test_all_536_orientations_reserve_the_actual_corner_view():
    views = {'dsfd_rly_536_SN': {'w': 34.56, 'h': 19.44},
             'dsfd_rly_536_SW': {'w': 56.16, 'h': 56.16}}
    with patch.object(G, 'NATIVE_SLOT_ENVELOPES', True), patch.object(G, 'bound_views', return_value=views):
        for horiz in (True, False):
            w,h = G.relay_dims(536,horiz)
            assert w >= 56.16 and h >= 56.16
    with patch.object(G, 'NATIVE_SLOT_ENVELOPES', True), patch.object(G, 'bound_views', return_value={}):
        with pytest.raises(ValueError, match='source-pinned'):
            G.relay_dims(536,True)


def test_native_qbank_growth_preserves_registered_macro_gap_and_ports():
    rq = {'name':'q', 'w':510.84, 'h':221.4}
    views = {'dsfd_qbank_S':{'w':60.48,'h':25.92}, 'dsfd_qbank_N':{'w':60.48,'h':8.64}}
    def face(rq, port, port_map):
        return {'x0':'S','r0':'N'}.get(port)
    with patch.object(G,'NATIVE_SLOT_ENVELOPES',True), patch.object(G,'bound_views',return_value=views), \
         patch.object(G,'Q_X1B',False), patch.object(G,'PIN_ALIGN',False), \
         patch.object(G,'real_ports_r8',return_value={'q':{}}), \
         patch.object(G,'_q_port_face',side_effect=face), patch.object(G,'_q_port_xc',return_value=100):
        banks=G._q_banks(7,100,500,rq,'frame_0')
    south,north=banks
    assert south.master=='dsfd_qbank_S' and north.master=='dsfd_qbank_N'
    assert south.h+G.SHAVE==pytest.approx(25.92)
    assert north.h+G.SHAVE==pytest.approx(8.64)
    assert south.y+25.92<=500-2+1e-6
    assert north.y>=500+rq['h']+1.08-1e-6
    assert G.BANK_PORTS[south.name]==('S',['x0'])
    assert G.BANK_PORTS[north.name]==('N',['r0'])
