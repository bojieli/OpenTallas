#!/usr/bin/env python3
"""FAM-KV-HUB-R2 hroot rows (private, D27d base; same rows go to KV-PLAN-R4 for D28).  0 added cycles.
 h1 relay_sites re-spacing (resite_delta.json from resite2.py on the D25d CTS geometry): per bit, equal Manhattan hops
    from the landing-select flop (ring band, fixed) to the face-out register (fixed) for
      i_kvpc_Q_N_o_next  dsel -> u_bin -> u_rly.r_c -> u_rly.r -> u_bout_o_emb         max hop 737.7 -> 390.4 um
      i_kvs_ctl (fan)    dsel -> u_bin -> u_rly.fan_c -> u_rly.fan -> u_bout_o_chN/cN/kg 556.4 -> 272.5
      i_slg_Q_N_o_ctl    dsel -> u_bin -> u_rly.g_c -> u_rly.g -> u_ist_o_ctl_0 -> u_bout  652.8 -> 320.8
      i_kvs_ctl (esh)    dsel -> u_bin -> u_esh.h_c -> u_esh.u_st.d -> u_bout_o_pc        437.5 -> 317.4
    (u_esh.h_c keys are new relay_sites keys; u_st.d spread W over x 1600-1900 off the E-face ring strip)
 h2 internal_stations o_kvs_hroot_Q_o_ctl: regs_um -> the slg cluster point, from_um -> centroid of the new u_rly.g sites
 h3 clock.ring_hold.sender_ps_types.kv3_hroot = -50 (port-in ring hold placeholder -385 -> the io_cor / sys_SD_v1 value)
usage: h1_hroot_rows.py PLAN_C.json RESITE_DELTA.json REPORT.json"""
import json, sys, hashlib, os, tempfile, statistics
p, dpath, rpath = sys.argv[1:4]
raw = json.load(open(p)); d = json.load(open(dpath))
t = raw["partition_types"]["kv3_hroot"]; rs = t["relay_sites"]
rec = dict(changed=0, added=0)
for k, v in d["relay_sites"].items():
    if k in rs: rec["changed"] += 1
    else: rec["added"] += 1
    rs[k] = v
q = d["slg_ist_o_ctl_point"]
g = [v for k, v in rs.items() if k.startswith("u_kvs_hroot.u_rly.g[")]
e = [x for x in t["internal_stations"] if x.get("conn") == "bus:o_kvs_hroot_Q_o_ctl"]
assert len(e) == 1 and len(e[0]["regs_um"]) == 1, e
old = (e[0]["from_um"], e[0]["regs_um"])
e[0]["from_um"] = [round(statistics.mean(a[0] for a in g), 3), round(statistics.mean(a[1] for a in g), 3)]
e[0]["regs_um"] = [[float(q[0]), float(q[1])]]
e[0]["note"] = (e[0].get("note", "") + " | FAM-KV-HUB-R2 11-21: station re-sited %s -> %s with the slg relay re-spacing (hops <= 321 um)" % (old[1][0], q)).strip(" |")
rh = raw["clock"]["ring_hold"]
rh.setdefault("sender_ps_types", {})["kv3_hroot"] = -50.0
rec.update(ist_o_ctl=dict(old=old, new=[e[0]["from_um"], e[0]["regs_um"]]), ring_hold=rh, summary=d["summary"])
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix=".fkh2.")
with os.fdopen(fd, "w") as f: json.dump(raw, f, indent=1)
os.chmod(tmp, 0o644); os.replace(tmp, p)
rec["plan_sha12"] = hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]
json.dump(rec, open(rpath, "w"), indent=1)
print("H1_HROOT_ROWS relay_sites changed %d added %d; ist_o_ctl -> %s; sender_ps_types.kv3_hroot -50; plan %s" % (rec["changed"], rec["added"], q, rec["plan_sha12"]))
