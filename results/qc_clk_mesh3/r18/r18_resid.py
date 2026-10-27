"""R18: residual-only HB4 (kit legacy window W already signed into the tiles): per unordered pair D' = max residual
(damage + clock OCV - W, both directions) - 12.28 so that r11 pad = residual; pairs without residual -> 0 cells."""
import io, json, sys, contextlib
sys.path.insert(0, sys.argv[1])
import r11_hb_count as H
plan, sta, out = sys.argv[2], sys.argv[3], sys.argv[4]
o = json.load(open(sta))["corners"]["FF"]["classes"]["seam"]["kit_contract_hold_ocv"]
dem = {}
for r, a, b in o["residual_ps"]:
    k = "|".join(sorted((a, b)))
    dem[k] = max(dem.get(k, -1e9), r - H.LIB_HOLD)
frag = dict(clock=dict(hold_demand=dict(pairs=dem, default_ps=-H.LIB_HOLD)))
json.dump(frag, open(out + ".frag.json", "w"))
with contextlib.redirect_stdout(io.StringIO()):
    H.main(plan, out + ".frag.json", out)
d = json.load(open(out))
print(json.dumps({k: d[k] for k in ("bits", "hb4_cells", "hb4_area_mm2", "cells_per_bit_hist", "hb4_cells_per_instance_D_info", "tt_setup_cost_ps_worst")}),
      "pairs_with_residual", len(dem))
