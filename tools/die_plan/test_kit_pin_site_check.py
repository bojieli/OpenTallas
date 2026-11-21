import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_pin_site_check as C  # noqa: E402

RS = """set rs_rects {}
odb::dbObstruction_create $rs_b [[ord::get_db_tech] findLayer M4] [expr {round(1276.992*$rs_u)}] [expr {round(517.86*$rs_u)}] [expr {round(1278.72*$rs_u)}] [expr {round(518.94*$rs_u)}]
odb::dbObstruction_create $rs_b [[ord::get_db_tech] findLayer M6] [expr {round(1276.992*$rs_u)}] [expr {round(517.86*$rs_u)}] [expr {round(1278.72*$rs_u)}] [expr {round(518.94*$rs_u)}]
"""
IO = """place_pin -pin_name {ft11_i[0]} -layer M4 -location {1278.6240 517.7040} -pin_size {0.1920 0.0240}
place_pin -pin_name {ft11_i[2]} -layer M4 -location {1278.6240 518.0400} -pin_size {0.1920 0.0240}
place_pin -pin_name {ft11_i[3]} -layer M6 -location {1278.6240 518.0480} -pin_size {0.1920 0.0320}
place_pin -pin_name {ft11_i[9]} -layer M5 -location {1278.6240 518.3000} -pin_size {0.1920 0.0240}
place_pin -pin_name {strap_x[0]} -layer M4 -location {1277.5 518.2} -pin_size {0.0320 0.0240}   ;# interior: ID strap
"""


def test_face_pins_inside_site_obstruction(tmp_path):
    (tmp_path / "reserved_sites.tcl").write_text(RS)
    (tmp_path / "io.tcl").write_text(IO)
    # ft11_i[0] is below the site, ft11_i[9] is on M5 (no M5 obstruction here), the strap is interior
    assert [h[0] for h in C.scan(tmp_path)] == ["ft11_i[2]", "ft11_i[3]"]
    assert C.main([str(tmp_path)]) == 1
