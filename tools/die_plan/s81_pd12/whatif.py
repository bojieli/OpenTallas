"""PATH-S81-PD12 (C) what-if: main kv_r18/mesh_mc18 (gap-fold branch copy) on the S81 me1 rec with a stronger mesh:
strap width w (RC_R6 extended: r = r4w * 4/w, c = c4w * cf(w)/1.3 * 1.13 with cf = 0.9 + 0.0875 w, which fits the
2w..16w NDR table) and driver strength k (thev mult x k = k x more BUFx24 per driver site).  Model only, UNCHECKED.
usage: whatif.py REC NDR K CORNER SAMPLES OUT.json ROUTED_MESH.json QCDIR MC18 THEV"""
import json, runpy, sys
rec, ndr, k, C, ns, out, routed, qc, mc18, thev = sys.argv[1:11]
sys.path.insert(0, qc)
import qc_clk_mesh2 as Q
b = Q.RC_R6["4w"]
for w in (32, 64, 128, 256):
    cf = 0.9 + 0.0875 * w
    Q.RC_R6.setdefault(f"{w}w", {L: (b[L][0] * 4 / w, b[L][1] * cf / 1.3 * 1.13) for L in ("M8", "M9")})
    Q.NDR.setdefault(f"{w}w", (0.25 * 4 / w, cf))
    Q.NDR_W_UM.setdefault(f"{w}w", 0.04 * w)
R = json.load(open(rec)); R["ndr"] = ndr
json.dump(R, open(out + ".rec.json", "w"))
T = json.load(open(thev))
for c_ in T:
    T[c_]["mult"] = T[c_].get("mult", 1) * int(k)
json.dump(T, open(out + ".thev.json", "w"))
sys.argv = [mc18, out + ".rec.json", "--thev", out + ".thev.json", "--corner", C, "--samples", ns, "--routed", routed,
            "--out", out, "--qc", qc]
runpy.run_path(mc18, run_name="__main__")
