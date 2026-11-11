#!/usr/bin/env python3
"""HBM-CHANNELS 11-11 counter overlay (DO_NOT_COUNT by itself), part of event hbm-channels-1111.
COORD (relayed by DIE-HBM-97 11-11): the counted HBM plan follows the wave build plan for two items.
 (1) NOT-IN-PLAN ot_hbm_su_pg_lane_full_x_core (vb3b8cc8e09a3, q_su00/q_su10 + __physical_v1, u_su_Q*_lane_exp0__l):
     the counted entry is replaced by the wave plan's entry for the same instance (ot_hbm_su_pg_lane_exp_x_core
     319.68 x 207.36, pins cores/..__d44v_split__oneclk.json = main plan_of_record/d44v/cores, byte-identical).
 (2) CONDITIONAL --sfs: ot_smh_static_front (u_sm_front_nf, q_sm0..3) -> SF-SPLIT halves u_sm_front_nfw/_nfe
     (ot_smh_static_front_w / _e 907.2 x 233.28, pins physical/die_plan/hbm/sf_split_1110/*.json), exactly the
     transformation of main physical/die_plan/hbm/sf_split_1110/apply_event.py.  TRIGGER: both halves signed off.
 (3) kv_line (DIE-HBM-98 11-11 ruling): u_sm_front_kv ot_hbm_sm_kv_line 734.4x233.28 -> 734.4x388.8 (south only, origin
     y 2004.48 -> 1848.96), pins cores/ot_hbm_sm_kv_line__734.4x388.8__kvs1111.json from the channel plan dir (KV_PLAN_DIR).
usage: mk_count_chan.py COUNT_PLAN_GZ WAVE_PLAN_JSON OUT_DIR REPO_REF [--sfs]   env KV_PLAN_DIR = channel plan dir   (run in a repo checkout with REPO_REF)"""
import copy, gzip, hashlib, json, os, subprocess, sys
CP, WP, OUT, REF = sys.argv[1:5]
SFS = "--sfs" in sys.argv[5:]
EXPECT = "4873c1b449fdae0b7d6a9d0f568290e1997cce11d1a8a245b9a9914ff3a80cb8"
raw = open(CP, "rb").read()
assert hashlib.sha256(raw).hexdigest() == EXPECT, "counted plan gz is not n4x 4873c1b449fd"
P = json.loads(gzip.decompress(raw))
B = json.loads(gzip.decompress(raw))
Wv = json.load(open(WP))
POR = "physical/die_plan/hbm/plan_of_record/"
CHAIN = ["d44v_gqi_cp1109_q3vm_smk_n4x", "d44v_gqi_cp1109_q3vm_smk", "d44v_gqi_cp1109_q3vm_opsb", "d44v_gqi_cp1109_q3vm",
         "d44v_gqi_cp1109", "d44v_gqi", "d44v_epm", "d44v", "d35c", "d35b", "d35a"]


def show(path):
    r = subprocess.run(["git", "show", f"{REF}:{path}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


rep = dict(full_x=[], sfs=None, files={})
# (1) full_x -> the wave entry
for tn, t in P["partition_types"].items():
    for i, h in enumerate(t.get("hard_cores") or []):
        if h.get("module") != "ot_hbm_su_pg_lane_full_x_core":
            continue
        w = [x for x in Wv["partition_types"][tn]["hard_cores"] if x["inst"] == h["inst"]]
        assert len(w) == 1 and w[0]["module"] == "ot_hbm_su_pg_lane_exp_x_core", (tn, h["inst"])
        g = copy.deepcopy(w[0])
        g["note"] = (g.get("note", "") + " | HBM-CHANNELS hbm-channels-1111 (COORD 11-11 NOT-IN-PLAN): counted entry follows the "
                     "wave build plan (was ot_hbm_su_pg_lane_full_x_core 354.24x207.36 d44v_p42, 4 failed forms)")
        if "parent_id_straps" in h and "parent_id_straps" not in g:
            g["parent_id_straps"] = h["parent_id_straps"]
        t["hard_cores"][i] = g
        rep["full_x"].append(dict(type=tn, inst=h["inst"], old=[h["module"], h["outline_um"], h.get("pins_file")],
                                  new=[g["module"], g["outline_um"], g.get("pins_file")]))
assert len(rep["full_x"]) == 4, rep["full_x"]
pf = rep["full_x"][0]["new"][2]
main_b = show(POR + "d44v/" + pf)
wave_b = open(os.path.join(os.path.dirname(WP), pf), "rb").read()
assert main_b is not None and main_b == wave_b, "oneclk pins differ from main d44v/cores"
rep["files"][pf] = dict(source=POR + "d44v/" + pf, sha256=hashlib.sha256(main_b).hexdigest(), byte_identical_wave=True)
# (3) kv_line south grow, same as the channel event (C)
KVP = "cores/ot_hbm_sm_kv_line__734.4x388.8__kvs1111.json"
kvb = open(os.path.join(os.environ["KV_PLAN_DIR"], KVP), "rb").read()
rep["kv_line"] = []
for T in ("q_sm0", "q_sm1", "q_sm2", "q_sm3"):
    h = [x for x in P["partition_types"][T]["hard_cores"] if x["inst"] == "u_sm_front_kv"]
    assert len(h) == 1 and h[0]["outline_um"] == [734.4, 233.28] and h[0]["origin_um"][1] == 2004.48, T
    h = h[0]; h["origin_um"] = [h["origin_um"][0], 1848.96]; h["outline_um"] = [734.4, 388.8]; h["pins_file"] = KVP
    h["note"] = h.get("note", "") + " | DIE-HBM-98 11-11 kvline ruling (counter, hbm-channels-1111): south grow to 734.4x388.8"
    rep["kv_line"].append(T)
rep["files"][KVP] = dict(source="channel plan dir " + KVP, sha256=hashlib.sha256(kvb).hexdigest())
# (4) q_mcb split (DIE-HBM-98 11-11 ruling, same as channel event (D)): single-instance types q_mcb_ne / q_mcb_nw
Tq = P["partition_types"]; qm = Tq.pop("q_mcb"); assert qm["module"] == "hbm_arch_q_mcb" and not qm.get("hard_cores")
for tn in ("q_mcb_ne", "q_mcb_nw"):
    assert tn not in Tq; Tq[tn] = copy.deepcopy(qm); Tq[tn]["module"] = "hbm_arch_" + tn
for x in P["partitions"]:
    if x["type"] == "q_mcb": x["type"] = "q_mcb_ne" if x["name"] == "NE_mcb" else "q_mcb_nw"
rep["mcb_split"] = dict(types_before=len(Tq) - 1, types_after=len(Tq), new={"q_mcb_ne": "NE_mcb", "q_mcb_nw": "NW_mcb"})
# (2) conditional SF-SPLIT (sf_split_1110/apply_event.py transformation on the counted plan)
SF = "physical/die_plan/hbm/sf_split_1110/"
MOD = {"W": "ot_smh_static_front_w", "E": "ot_smh_static_front_e"}; XC = 907.2
if SFS:
    for T in ("q_sm0", "q_sm1", "q_sm2", "q_sm3"):
        t = P["partition_types"][T]
        i = [k for k, h in enumerate(t["hard_cores"]) if h["inst"] == "u_sm_front_nf"]; assert len(i) == 1; i = i[0]
        h = t["hard_cores"][i]; assert h["outline_um"] == [1814.4, 233.28]
        new = []
        for H in "WE":
            g = copy.deepcopy(h); g["inst"] = "u_sm_front_nf" + H.lower(); g["module"] = MOD[H]; g["physical_master"] = MOD[H]
            g["origin_um"] = [round(h["origin_um"][0] + (0 if H == "W" else XC), 4), h["origin_um"][1]]; g["outline_um"] = [907.2, 233.28]
            g["pins_file"] = "cores/%s__907.2x233.28__sfs1110.json" % MOD[H]; g["physical_inst"] = h["physical_inst"] + ".u_" + H.lower()
            g["note"] = "SF-SPLIT 11-10 (counter, HBM-CHANNELS hbm-channels-1111 --sfs): %s half of ot_smh_static_front, cut x 907.2" % H
            if H == "E":
                g["reset_from_master"] = {"kind": "internal", "content": "u_sm", "source": "SF-SPLIT: the E half has no rst_n port"}
            new.append(g)
        t["hard_cores"][i:i + 1] = new
        taps = t["clock"]["taps"]; j = [k for k, x in enumerate(taps) if x["name"] == "u_sm_front_nf"]; assert len(j) == 1; j = j[0]; tp = taps[j]
        nt = []
        for H, g in zip("WE", new):
            x = copy.deepcopy(tp); x["name"] = g["inst"]; x["budget_owner"] = MOD[H]; x["xy"] = [round(g["origin_um"][0] + 453.6, 4), tp["xy"][1]]
            nt.append(x)
        taps[j:j + 1] = nt
    for H in "WE":
        f = "%s__907.2x233.28__sfs1110.json" % MOD[H]
        b = show(SF + f); assert b is not None
        rep["files"]["cores/" + f] = dict(source=SF + f, sha256=hashlib.sha256(b).hexdigest())
    rep["sfs"] = "applied"
else:
    rep["sfs"] = "NOT applied (trigger: ot_smh_static_front_w AND ot_smh_static_front_e signed off; rerun with --sfs)"
P["note"] = P.get("note", "") + (" | HBM-CHANNELS hbm-channels-1111 counter overlay: full_x NOT-IN-PLAN -> wave entry"
                                 + ("; SF-SPLIT E/W" if SFS else ""))
os.makedirs(OUT + "/cores", exist_ok=True)
txt = json.dumps(P, separators=(",", ":")).encode()
gz = gzip.compress(txt, mtime=0)
open(OUT + "/die_plan.json.gz", "wb").write(gz)
for f, v in rep["files"].items():
    open(os.path.join(OUT, f), "wb").write(kvb if f == KVP else show(v["source"]))


# design count (release_tree_plan.plan_designs; pins resolved through the overlay chain on REF)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
spec = importlib.util.spec_from_file_location("rtp", os.path.join(os.path.dirname(os.path.abspath(__file__)), "release_tree_plan_coord.py"))
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)


def reader(extra):
    def rd(f):
        if f in extra:
            return json.loads(extra[f])
        for d in CHAIN:
            b = show(POR + d + "/" + f)
            if b is not None:
                return json.loads(gzip.decompress(b) if f.endswith(".gz") else b)
        b = show("physical/die_plan/hbm/cores/" + os.path.basename(f))
        if b is not None:
            return json.loads(b)
        raise FileNotFoundError(f)
    return rd


extra = {f: open(os.path.join(OUT, f), "rb").read() for f in rep["files"]}
d0, _ = R.plan_designs(B, POR + CHAIN[0], read=reader({}))
d1, _ = R.plan_designs(P, OUT, read=reader(extra))
rep["designs_before"] = len(d0); rep["designs_after"] = len(d1)
rep["dropped"] = sorted(set(d0) - set(d1)); rep["added"] = sorted(set(d1) - set(d0))
rep["base_sha256_gz"] = EXPECT; rep["new_sha256_gz"] = hashlib.sha256(gz).hexdigest()
rep["new_sha256_json"] = hashlib.sha256(txt).hexdigest()
json.dump(rep, open(OUT + "/count_overlay_report.json", "w"), indent=1)
print(json.dumps({k: rep[k] for k in ("designs_before", "designs_after", "dropped", "added", "sfs", "new_sha256_gz")}, indent=1))
