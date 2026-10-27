import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_island_ports as K


def test_track_on_lattice_and_pg_clear():
    for x in (101.064, 104.904, 122.28, 127.944, 267.0, 270.84):
        assert K.pg_ok(x)
        assert abs((x - 0.024) / 0.048 - round((x - 0.024) / 0.048)) < 1e-6
    # a track inside the PG stripe pair is skipped
    t = K.track(2.2, +1)
    assert K.pg_ok(t) and t > 2.2


def test_groups_merge_abutting_rects():
    g = K.groups_of([[109.08, 138.24, 110.7, 138.51], [107.46, 138.24, 109.08, 138.51], [268.11, 43.2, 269.73, 43.47]])
    assert g == [(268.11, 43.2, 269.73, 43.47), (107.46, 138.24, 110.7, 138.51)]
