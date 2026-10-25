# stage r3 preflight kits: base kit copy + kvspc_face_ports (RTL) + local in-memory plan delta on pins.json
import sys, json, shutil
from pathlib import Path
B, O, H = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, H)
import kvspc_face_ports as X
for mod in ("qkd_kvs_pc", "qkd_kvs_pc_h_head_p"):
    src = B / mod
    dst = O / f"{mod}__397.44x362.88"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("run", "__pycache__", "face_guard*.json", "face_guard*.log", "fg_full.json", "run_*.log", "synth_odb_v.*", "1_synth_odb.v"))
    X.apply_kit(dst / "rtl", mod)
    head = mod.endswith("_h_head_p")
    pins = json.loads((dst / "pins.json").read_text())
    np_ = X.pins_update(pins, head)
    (dst / "pins.json").write_text(json.dumps(np_) + "\n")
    # sdc_lint context: drop the removed inputs / clocks
    lc = json.loads((dst / "sdc_lint.json").read_text())
    gone = {"hck", "pc__front_hbm_data", "pc__return_hbm_data"}
    lc["clock_ports"] = [c for c in lc["clock_ports"] if c not in gone]
    lc["inputs"] = [b for b in lc["inputs"] if b not in gone]
    fl = lc["io_floor_ps"][ "pc__land_er"]
    for g in gone:
        lc["io_floor_ps"].pop(g, None)
    adds = ["pc__land_er_259"] + (["pc__ki_15", "pc__ki_31"] if head else [])
    lc["inputs"] += adds
    for a_ in adds:
        lc["io_floor_ps"][a_] = fl
    (dst / "sdc_lint.json").write_text(json.dumps(lc, indent=1) + "\n")
    sdc = (dst / "constraint.sdc").read_text()
    assert sdc.count("[get_ports {ck hck}]") == 1
    (dst / "constraint.sdc").write_text(sdc.replace("[get_ports {ck hck}]", "[get_ports {ck}]").replace("# ASSUMPTION (labelled", "# KV-CORE-RTL/PC 10-25: ONE clock (owner decision 14: hck = die clock; hck pin dropped). Superseded: # ASSUMPTION (labelled"))
    (dst / "kvspc_face_delta.json").write_text(json.dumps(dict(
        transform="kvspc_face_ports.py", plan_dropped_pins=X.dropped_pins(head), pins_before=len(pins), pins_after=len(np_),
        renamed_buses=(["pc__land_er[260:259] -> pc__land_er_259"] + (["pc__ki[20:15] -> pc__ki_15", "pc__ki[32:31] -> pc__ki_31"] if head else [])),
        cycles=dict(kc_chain_ko="+1 hclk per kc station" if not head else "n/a (head: no ko)", fi_fault="+1 edge (upstream fault only)" if not head else "n/a (head: no fi)", other=0),
        note="LOCAL plan delta applied in-memory for preflight; KV-PLAN3 owns the plan"), indent=1) + "\n")
    print(mod, len(pins), "->", len(np_))
