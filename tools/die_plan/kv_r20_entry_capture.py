"""CLOCK-KV-R20: run master_plan main unchanged; capture EVERY clock_entry fail row (gate keeps only 40 examples)."""
import sys, json
import master_plan as MP
o = sys.argv.index("--dump"); dump = sys.argv[o + 1]; del sys.argv[o:o + 2]
rows = []
orig = MP.core_clock_entry_check
def wrap(P, h, taps, proposed, tolerance=0.5):
    r = orig(P, h, taps, proposed, tolerance)
    rows.append(dict(r, entry_xy=list(proposed), hard_inst=h.get("inst"), hard_module=h.get("module"),
                     outline_um=h.get("outline_um"), at=h.get("at_um") or h.get("xy_um") or h.get("origin_um")))
    return r
MP.core_clock_entry_check = wrap
try:
    MP.main(sys.argv[1:])
finally:
    json.dump(rows, open(dump, "w"))
    print("CAPTURED", len(rows), "fails", sum(1 for r in rows if r["verdict"] != "PASS"))
