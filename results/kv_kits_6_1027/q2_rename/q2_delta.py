"""KV-CORES-PV3 D-KV-ECTLK-Q2-SI283 (COORD 10-27 07:38): plan pin rename only, no RTL change, no xy change.
qkd_ectlk_q2 RTL port is si_283[536:283] (ectlk_columns.py quarter cut); plan pins named si[283..536]
-> si_283[283..536]. hm_r26 568fc66e -> hm_r26q2: the 8 kv3_hg* hard_cores[] entries of module qkd_ectlk_q2 point at
cores/qkd_ectlk_q2_pins_r26q2.json (everything else byte-identical)."""
import json, re, sys, hashlib
pd = sys.argv[1]
src = f"{pd}/cores/qkd_ectlk_q2_pins_r25.json"
d = json.load(open(src))
n = 0
for p in d["pins"]:
    m = re.fullmatch(r"si\[(\d+)\]", p["name"])
    if m and int(m.group(1)) >= 283:
        p["name"] = f"si_283[{m.group(1)}]"; n += 1
d["source"] = d["source"] + " | KV-CORES-PV3 10-27 D-KV-ECTLK-Q2-SI283: si[283..536] -> si_283[283..536] (RTL port name; xy/layer unchanged)"
out = f"{pd}/cores/qkd_ectlk_q2_pins_r26q2.json"
open(out, "w").write(json.dumps(d, indent=1) + "\n")
P = json.load(open(f"{pd}/hm_r26.json"))
k = 0
for tn, t in P["partition_types"].items():
    for hc in t.get("hard_cores", []):
        if hc.get("module") == "qkd_ectlk_q2":
            assert hc["pins_file"] == "cores/qkd_ectlk_q2_pins_r25.json", hc["pins_file"]
            hc["pins_file"] = "cores/qkd_ectlk_q2_pins_r26q2.json"; k += 1
open(f"{pd}/hm_r26q2.json", "w").write(json.dumps(P, indent=1) + "\n")
print(f"renamed {n} pins; repointed {k} hard_core entries")
