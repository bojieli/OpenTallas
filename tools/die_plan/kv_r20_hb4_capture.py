"""CLOCK-KV-R20: run die_sta_related main (gate args unchanged) and pickle the per-endpoint-path TT/FF records
of each class handed to hold_buffer_model, plus the seam bit map (a, b, pid) -> bits.  Diagnostic, no gate change."""
import sys, pickle
import die_sta_related as R
o = sys.argv.index("--dump"); dump = sys.argv[o + 1]; del sys.argv[o:o + 2]
cap = []
orig = R.hold_buffer_model
def wrap(tt, ff, bits=None, hb=R.HB4):
    cap.append((tt, ff))
    return orig(tt, ff, bits=bits, hb=hb)
R.hold_buffer_model = wrap
R.main(sys.argv[1:])
pickle.dump(dict(classes=["intra", "seam", "seam_nearest_INFO"][:len(cap)], recs=cap), open(dump, "wb"))
print("CAPTURED", len(cap))
