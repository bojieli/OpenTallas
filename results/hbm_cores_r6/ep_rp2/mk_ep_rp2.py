"""HBM-CORES-R6: views + trial master slice for hfd_ep_static ep_N0 family from QUAD5 planU5e_r (revised E-face pins)."""
import json, hashlib, sys
from pathlib import Path
P = Path("/srv/opentallas-scratch2/claude/codex-hbm-1027/planU5e_r")
U4 = json.load(open("/srv/opentallas-scratch2/claude/hbm-kits-1-1027/views_U4f.json"))
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
pf = "cores/hfd_ep_static__250.56x375.84__NW_io_u_ep_N0.json"
sh = hashlib.sha256((P / pf).read_bytes()).hexdigest()
v = dict(next(x for x in U4["view_list"] if x["pins_file"] == pf))
v.update(view=f"hfd_ep_static@{sh[:12]}", pins_sha256=sh, note="planU5e_r (QUAD5) revised pins: sd_rx/sd_tx/rx_pin_flit/tx_frame E face M4")
views = dict(schema=U4.get("schema"), plan=str(P / "die_plan.json"),
             plan_sha256=hashlib.sha256((P / "die_plan.json").read_bytes()).hexdigest(), view_list=[v])
(out / "views_ep_U5e_r.json").write_text(json.dumps(views, indent=1) + "\n")
CE = json.load(open(P / "clock_entries.json"))
ents = [e for d in CE.values() if isinstance(d, dict) for k, e in d.items() if isinstance(e, dict) and e.get("module") == "hfd_ep_static" and k != "u_host_ep"]
keys = {(tuple(e["xy_um"]), tuple(e["island_um"]), e["port"]) for e in ents}
assert len(ents) == 4 and len(keys) == 1, (len(ents), keys)
xy, isl, port = next(iter(keys)); W, H = v["outline_um"]
sl = {"schema": "opentallas.master_plan_slice.v1", "die": "hbm", "kind": "core", "type": "hfd_ep_static", "module": "hfd_ep_static",
      "instances": [], "master_plan_sha256": "TRIAL-no-frozen-master-plan", "frozen": False, "outline_um": [W, H],
      "latency": {"common_clock_latency_ps": {"TT": 250, "FF": 202.5}, "tol_ps": 20, "early_taps": False},
      "keepouts": [], "bays": [], "entry_pins": [], "hard_cores": [], "corridors": [], "gates": {}, "core_clock_port": port,
      "islands": [{"name": "ck_entry", "rect_um": list(isl), "centre_um": list(xy), "use": "clock_driver",
                   "via_stack": ["M9", "M5"], "clock_pin": {"layer": "M5", "xy_um": list(xy)}}],
      "note": "HBM-CORES-R6 ep rp2 trial slice: planU5e_r clock_entries.json (4 ep_N0-family inst identical)"}
(out / "slices").mkdir(exist_ok=True)
(out / "slices" / "hfd_ep_static.json").write_text(json.dumps(sl, indent=1) + "\n")
print(v["view"], xy, isl, port)
