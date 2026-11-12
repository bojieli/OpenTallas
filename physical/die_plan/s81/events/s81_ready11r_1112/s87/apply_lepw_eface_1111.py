"""DIE-S81-87 (DO_NOT_COUNT): LEPW-EFACE-1111 applied by slot identity from the lane's report (epyc7 die-s81-85/lepwface/out/report.json,
plan c3d22064f68c on 99f40d35071d). usage: IN OUT REPORT. Asserts every old window equals the plan's before moving it."""
import json, sys
inp, out, rep = sys.argv[1:4]
P = json.load(open(inp))
BUS = {("dsdv_slice_lepw_mus_LP__t2", "lepk_i0"): ([6.144, 246.108], [596.16, 836.124]),
       ("dsdv_slice_lepw_mus_LP__t2", "lepk_o0"): ([247.296, 487.26], [837.312, 1077.276]),
       ("dsdv_slice_lepw_mus_C__t1", "lepk_o0"): ([6.144, 246.108], [596.16, 836.124]),
       ("dsdv_slice_lepw_mus_C__t1", "lepk_i0"): ([247.296, 487.26], [837.312, 1077.276])}
PORT = {"kd_s_0S__0": ([10616.064, 10856.028], [11206.08, 11446.044]),
        "ku_s_0S__0": ([10857.216, 11097.18], [11447.232, 11687.196])}
done = []
for (t, b), (old, new) in BUS.items():
    x = [x for x in P["partition_types"][t]["buses"] if x["name"] == b]
    assert len(x) == 1 and x[0]["window_um"] == old, (t, b, x and x[0]["window_um"])
    x[0]["window_um"] = new; done.append([t, b])
for p in P["ports"]:
    if p["id"] in PORT:
        old, new = PORT[p["id"]]
        assert p["window_um"] == old, (p["id"], p["window_um"])
        p["window_um"] = new; done.append(p["id"])
assert len(done) == 6
json.dump(P, open(out, "w"), indent=1)
json.dump(dict(event="LEPW-EFACE-1111", changed=done), open(rep, "w"))
