import json, hashlib, sys
from pathlib import Path
src = {"qfd_dv_s8x_vmr": "SIGNED vmr f4kfinal 77013e5059 autopilot closed kit/views ETM (06:28; final ECO 09:54)",
       "qfd_dv_s8_crh_rp1": "SIGNED crh_rp1 f4g 5ed4500430 autopilot closed kit/views ETM",
       "qfd_dv_s8x_prog": "SIGNED prog s8b 6aa7f1fc4d autopilot closed base/_tc/_bc ETM (15:15 after 6_final 15:12)",
       "qfd_dv_s5_su8_rst3": "SIGNED rst3 K0 hold_b (intel1 qccores1-1027/rst3_k0); ETM = base/views 04:43 PRE hold-ECO (hold buffers only add data delay -> conservative)",
       "qfd_dv_s8x_crh": "SIGNED s8x_crh qc/closed (re-verify VALID, LEC EQ 3697) kit/views ETM"}
sys.path.insert(0, sys.argv[1])
import die_sta_related as R
for m, s in src.items():
    d = Path(m); b = (d / "pins.json").read_bytes(); pj = json.loads(b)
    ol = None
    (d / "provenance.json").write_text(json.dumps({"verdict": "SIGNED", "source": s, "kit": {"pins_sha256": hashlib.sha256(b).hexdigest(), "pins_file": "pins.json", "outline_um": ol}}, indent=1))
    for c in ("tt", "ff"):
        e = R.parse_etm(d / f"{m}_{c}.lib", 1.2)
        print(m, c, "outline", ol, "clk_tree", e["clock_tree_path_ps"], "out_min", e["out_min_ps"], e["out_min_pin"], "out_max", e["out_max_ps"], "in_setup", e["in_setup_ps"], "in_hold", e["in_hold_ps"], e["in_hold_pin"], e["arcs"])
