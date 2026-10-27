"""R18 what-if: HB4 count vs declared sender guarantee G (kit out_min): pad = D + 12.28 + 12.5 - G (G = 12.5 today)."""
import io, json, sys, contextlib
sys.path.insert(0, sys.argv[1])
import r11_hb_count as H
plan, frag = sys.argv[2], sys.argv[3]
for G in (12.5, 30.0, 40.0, 45.0):
    H.LIB_HOLD = 12.28 + 12.5 - G
    with contextlib.redirect_stdout(io.StringIO()):
        H.main(plan, frag, "/tmp/r18_hbg.json")
    d = json.load(open("/tmp/r18_hbg.json"))
    # cells/bit hist from ceil((D+LIB_HOLD)/d_ff) may be <= 0 -> zero cells
    print(f"G={G:5.1f} hb4_cells {d['hb4_cells']:>9d} area {d['hb4_area_mm2']:.4f} mm2 hist {d['cells_per_bit_hist']}")
