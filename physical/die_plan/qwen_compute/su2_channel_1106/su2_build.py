"""DIE-QC-85 SU2 south-channel form: kit-local overlay onto the Codex SU2 kit (synth reused, RTL unchanged).
usage: su2_build.py KIT T BASE_GEN PATCHED_GEN VARIANT"""
import json, re, subprocess, sys, hashlib
from pathlib import Path
K, T, B, P, V = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]
log = []
# 1. geometry files identical Codex == base gen: take the patched gen file
for f in ["io.tcl", "landing_placement.tcl", "ft_bit_sites.tcl", "ft_stations.txt", "landing_contract.json", "plan_pins.json"]:
    kb = (K/f).read_bytes(); bb = (B/T/f).read_bytes()
    assert kb == bb, f"{f}: Codex kit differs from base gen, refusing overlay"
    (K/f).write_bytes((P/T/f).read_bytes()); log.append(f"overlay {f}")
# 2. budget/freeze: apply base->patched diff
fb, fp, fk = (json.loads((x/"freeze.json").read_text()) for x in (B/T, P/T, K))
for k in fp:
    if fb.get(k) != fp[k]:
        assert fk.get(k) == fb.get(k), ("freeze", k); fk[k] = fp[k]; log.append(f"freeze.json {k}")
(K/"freeze.json").write_text(json.dumps(fk, indent=1) + "\n")
for f in ["budget.json"]:
    d = subprocess.run(["diff", "-u", str(B/T/f), str(P/T/f)], capture_output=True, text=True).stdout
    r = subprocess.run(["patch", "--no-backup-if-mismatch", str(K/f)], input=d, capture_output=True, text=True)
    if r.returncode != 0:
        rej = Path(str(K/f) + ".rej"); rl = [l for l in rej.read_text().splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---"))]
        assert rl and all('"plan_sha256"' in l for l in rl), (f, r.stdout, rej.read_text())
        rej.unlink(); log.append(f"patch {f} (plan_sha256 hunk kept as the Codex kit's own plan identity)")
    else:
        log.append(f"patch {f}")
    json.loads((K/f).read_text())
# 3. macro_place: lane4 +25.92 y; rsn landing to (4.332, 25.932)
mp = (K/"macro_place.tcl").read_text()
n1 = mp.count("{u_bound.u_lane4} -location {17.2920 34.5720}"); n2 = mp.count("{u_bound.u_cland_rsn_i} -location {184.9080 4.3320}")
assert n1 == 1 and n2 == 1, (n1, n2)
mp = mp.replace("{u_bound.u_lane4} -location {17.2920 34.5720}", "{u_bound.u_lane4} -location {17.2920 60.4920}")
mp = mp.replace("{u_bound.u_cland_rsn_i} -location {184.9080 4.3320}", "{u_bound.u_cland_rsn_i} -location {4.3320 25.9320}")
(K/"macro_place.tcl").write_text(mp); log.append("macro_place lane4 y 34.572->60.492, rsn (184.908,4.332)->(4.332,25.932)")
# 4. reset_tree: relays that follow the moved objects (values = patched gen's own tree for the same keys)
rt = (K/"reset_tree.tcl").read_text()
subs = [(r"(rtr_place rst_rl_30 \S+ )107\.972 306\.732", r"\g<1>107.972 336.972"),
        (r"(rtr_place rn_rst_rl_30 \S+ )107\.972 306\.732", r"\g<1>107.972 336.972"),
        (r"(rtr_place rst_n_t1 \S+ )57\.184 17\.312", r"\g<1>57.184 17.248"),
        (r"(rtr_place rst_n_t6 \S+ )56\.864 312\.672", r"\g<1>56.864 342.944"),
        (r"(rtr_place rst_n_t20 \S+ )180\.588 30\.252", r"\g<1>224.472 56.172")]
for a, b in subs:
    rt, n = re.subn(a, b, rt); assert n == 1, (a, n)
(K/"reset_tree.tcl").write_text(rt); log.append("reset_tree rst_rl_30 +30.24, t1 y 17.248, t6 y 342.944, t20 -> (224.472,56.172)")
# 5. bound_native_reset metadata (lane4 rst_n pin + its tap relay)
bn = K/"bound_native_reset.json"; s = bn.read_text()
s2 = re.sub(r'("pin_um": \[\s*224\.472,\s*)34\.668', r'\g<1>60.588', s)
s2 = re.sub(r'("xy": \[\s*)180\.588(,\s*)30\.252', r'\g<1>224.472\g<2>56.172', s2)
json.loads(s2); bn.write_text(s2); log.append("bound_native_reset lane4 rst_n pin/xy")
# 6. variant knobs
if V == "vB":
    c = (K/"config.mk").read_text(); assert c.count("export PLACE_DENSITY = 0.5\n") == 1
    (K/"config.mk").write_text(c.replace("export PLACE_DENSITY = 0.5\n", "export PLACE_DENSITY = 0.40\n")); log.append("vB PLACE_DENSITY 0.5->0.40")
# 7. resume from floorplan, synth reused
rj = json.loads((K/"resume.json").read_text())
rj.update(start="floorplan", reused_steps=["synth"], source={"host": "epyc5", "kit": str(K)})
rj["scope"] = (f"DIE-QC-85 11-06 SU2 south-channel form {V}: lane4 +25.92 um, rsn landing moved W to (4.32,25.92), "
               "monitor_0/ft rsn/reset relays follow; synth + RTL reused unchanged; floorplan->route. " + "; ".join(log))
(K/"resume.json").write_text(json.dumps(rj, indent=1))
print("\n".join(log))
