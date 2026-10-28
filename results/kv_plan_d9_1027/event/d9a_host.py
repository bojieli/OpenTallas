"""KV-PLAN-DELTA-9a (DIE-KV 10-27): host part of the D9 event, one source for both KV forms.
 (1) KV-HOST-REGEN-1 pins (COORD 19:09 (b)): core_tx drops u_ctrl__cmd_hc[181:39] (143 unloaded outputs);
     phy_pad + phy_adp ck_phy[0] -> ck[0] (same xy; b3 bind = one core clock -> the tap becomes a die-clock core sink);
     cdc_pc drops ck_phy[0] (no tap).
 (2) host_qm FOLD (GEOM-REVIEW-35 / COORD 20:01): qkd_hr_host_qm (194 cells, 17 FF, 10 pins) leaves hub_Wi.hard_cores,
     its logic stays hub_Wi partition glue (as glue:qm_host / glue:fence_host already are); its die tap is removed.
(3) G0C [cells] for the PATH-KV-BIND explicit-split types (kv3_pv_vKn, kv3_hg_v1pK): type.cells = the parent type
     estimate (cells.py on this plan) -- the same basis LAND-KV-1 cells_fix.py used, now in the one source.
usage: d9a_host.py IN.json PLAN_DIR OUT_NAME LEDGER.json TOOLS_DIE_PLAN   (pin files written to PLAN_DIR/cores/*_pins_r26q9.json)"""
import json, re, sys, copy
from pathlib import Path
inp, pdir, outname, ledp, tools = sys.argv[1:6]; sys.path.insert(0, tools); pdir = Path(pdir)
raw = json.load(open(inp)); LED = dict(pins={}, taps={}, fold={}, cells={})
T = raw["partition_types"]["kv3_hub_Wi"]
CMD = re.compile(r"^u_ctrl__cmd_hc\[(\d+)\]$")
def newpins(core, fn):
    src = pdir / "cores" / f"{core}_pins_r26q5.json"; d = json.load(open(src)); n0 = len(d["pins"])
    d["pins"] = fn(d["pins"])
    faces = {}
    for p in d["pins"]:
        pass
    d["source"] += f" | KV-PLAN-DELTA-9 hm_r26q9: KV-HOST-REGEN-1 pin change ({n0} -> {len(d['pins'])} pins)"
    # face pin counts
    w, h = map(float, re.search(r"outline ([\d.]+) x ([\d.]+)", d["frame"]).groups())
    cnt = {}
    for p in d["pins"]:
        f = "N" if abs(p["y"] - h) < 0.2 else "S" if p["y"] < 0.2 else "E" if abs(p["x"] - w) < 0.2 else "W" if p["x"] < 0.2 else None
        if f: cnt[f] = cnt.get(f, 0) + 1
    for f, v in d["faces"].items():
        if f in cnt: v["pins"] = cnt[f]
    dst = pdir / "cores" / f"{core}_pins_r26q9.json"; dst.write_text(json.dumps(d, indent=1) + "\n")
    LED["pins"][core] = dict(before=n0, after=len(d["pins"]), file=dst.name)
    return dst.name
def drop_cmd(pins):
    out = [p for p in pins if not (CMD.match(p["name"]) and 39 <= int(CMD.match(p["name"]).group(1)) <= 181)]
    assert len(pins) - len(out) == 143, len(pins) - len(out)
    return out
def ren_ck(pins):
    assert not any(p["name"] == "ck[0]" for p in pins)
    k = [p for p in pins if p["name"] == "ck_phy[0]"]; assert len(k) == 1
    k[0]["name"] = "ck[0]"; return pins
def drop_ckphy(pins):
    out = [p for p in pins if p["name"] != "ck_phy[0]"]; assert len(out) == len(pins) - 1; return out
pf = {"qkd_hr_core_tx": newpins("qkd_hr_core_tx", drop_cmd), "qkd_hr_phy_pad": newpins("qkd_hr_phy_pad", ren_ck),
      "qkd_hr_phy_adp": newpins("qkd_hr_phy_adp", ren_ck), "qkd_hr_cdc_pc": newpins("qkd_hr_cdc_pc", drop_ckphy)}
keep = []
for c in T["hard_cores"]:
    if c["module"] == "qkd_hr_host_qm":
        LED["fold"] = dict(removed=c, why="GEOM-REVIEW-35 FAIL-IN-PLAN fill 0.004; 194 cells/17 FF/10 pins folded into hub_Wi glue")
        continue
    if c["module"] in pf:
        c["pins_file"] = "cores/" + pf[c["module"]]
        c["note"] += " | KV-PLAN-DELTA-9: KV-HOST-REGEN-1 pin change (b3 bind of record)"
    keep.append(c)
assert len(keep) == len(T["hard_cores"]) - 1
T["hard_cores"] = keep
for ct in T["contents"]:
    if ct["inst"] == "host":
        ct["note"] += " | KV-PLAN-DELTA-9: qkd_hr_host_qm (u_pacer) folded back into the partition (no hard core)"
taps = []
for tp in T["clock"]["taps"]:
    n = tp["name"]
    if n == "host__qkd_hr_host_qm.ck[0]":
        LED["taps"][n] = "removed (fold)"; continue
    if n.endswith(".ck_phy[0]") and ("phy_pad" in n or "phy_adp" in n):
        old = copy.deepcopy(tp)
        tp = dict(name=n.replace(".ck_phy[0]", ".ck[0]"), kind="core", xy=tp["xy"], insertion_ps=250.0,
                  budget_owner=tp["budget_owner"],
                  note="KV-PLAN-DELTA-9: KV-HOST-REGEN-1 b3 bind (single core clock) -> RTL ck[0] at the old ck_phy[0] xy is "
                       "a die-clock core sink (was landed/forwarded ck_phy) | " + tp.get("note", ""))
        LED["taps"][n] = dict(old=old, new=tp)
    elif ".ck_phy[0]" in n:
        raise SystemExit(f"unexpected ck_phy tap {n}")
    taps.append(tp)
T["clock"]["taps"] = taps
import cells as CE
est, _ = CE.estimate(raw, str(pdir), ())
for tn, t in raw["partition_types"].items():
    m = re.match(r"^(kv3_pv_v\d+)n$", tn) or re.match(r"^(kv3_hg_v1)p\d+$", tn)
    if not m or t.get("hard") or est.get(tn, (None,))[0] is not None: continue
    pc = est.get(m.group(1), (None,))[0]
    if pc is None: raise SystemExit(f"no parent estimate for {tn}")
    t["cells"] = int(pc)
    t["note"] = t.get("note", "") + f" | KV-PLAN-DELTA-9: cells = parent {m.group(1)} estimate {int(pc)} (explicit split, same contents modules)"
    LED["cells"][tn] = dict(parent=m.group(1), cells=int(pc))
raw["note"] = "KV plan hm_r26q9 (KV-PLAN-DELTA-9a, DIE-KV 10-27) = hm_r26q5c39 + KV-HOST-REGEN-1 host pins + host_qm fold + split-type cell estimates | " + raw["note"]
(pdir / outname).write_text(json.dumps(raw, indent=1) + "\n")
Path(ledp).write_text(json.dumps(LED, indent=1) + "\n")
print(json.dumps(LED["pins"]), "taps changed", len(LED["taps"]))
