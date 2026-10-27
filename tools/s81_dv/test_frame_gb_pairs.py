"""Actual frame source keeps its QX/BF pair map after the explicit GB ABI lowering.

Pair classification describes ROM/image ownership only; it never qualifies a GO calendar.
"""
from pathlib import Path
from unittest.mock import patch
import frame_bench as F
import qxpq_go_boundary as G


def test_actual_frames_preserve_pair_map_after_gb_lowering():
    root = Path(__file__).resolve().parents[2]
    for master, nbf in [('col_h10_l4_lp', 4), ('col_h9_l4_lp', 3)]:
        path = root / 'rtl/dsrom_sys/s81_dv/frame_lp' / (master + '.sv')
        text = path.read_text()
        with patch.object(F, 'frame_module_source', return_value=(path, text)):
            legacy = F.frame_pairs(master)
        gb, rec = G.lower_frame_text(text)
        assert len(rec['instances']) == 12
        with patch.object(F, 'frame_module_source', return_value=(path, gb)):
            current = F.frame_pairs(master + '_gb')
        assert current == legacy and len(current[0]) == 12 and len(current[1]) == nbf


def test_similarly_named_unqualified_module_is_not_a_qx_pair():
    assert not F._Q_RE.search('ot_v41_rom_elem_q_qxpq_w10_gb_wrong u_e0 (');
