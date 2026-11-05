#!/usr/bin/env python3
"""HBM-REFORM-B d44v part 20: ot_pdie_serdes -> ot_pdie_serdes_tx + ot_pdie_serdes_rx + signed ot_s81_kp4_dchn inside its slots.
    mk_p20.py pre PLAN_DIR    slot 600.048x600.48 -> 596.16x596.16 (origin kept): mk_split tile edges need the 8.64 lattice
    (mk_split.py PLAN_DIR split_p20.json split_p20)
    mk_p20.py post PLAN_DIR TABLE    dchn table = the signed pins (HEAD core_pins kp4_276x138_pins.json), part20_event.json"""
import json, sys
from pathlib import Path
mode, pd = sys.argv[1], Path(sys.argv[2]); NEW = [596.16, 596.16]; OLD = [600.048, 600.48]; DCHN = "ot_s81_kp4_dchn"
TN = f"cores/{DCHN}__276.48x138.24__signed.json"
D = json.loads((pd / "die_plan.json").read_text())
rows = [(t, h) for t, ty in D["partition_types"].items() for h in ty.get("hard_cores") or []]
if mode == "pre":
    r = [(t, h) for t, h in rows if h["module"] == "ot_pdie_serdes"]
    if not r or any(h["outline_um"] != OLD for _, h in r): raise SystemExit("pdie rows not as read")
    for _, h in r: h["outline_um"] = NEW
    (pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n")
    print("part 20 pre:", len(r), "rows", sorted({h.get("orient", "R0") for _, h in r}))
else:
    T = json.loads(Path(sys.argv[3]).read_text()); T = T["pins"] if isinstance(T, dict) else T; ck = [p for p in T if p["name"] == "clk"]
    if len(T) != 945 or len(ck) != 1: raise SystemExit("signed table not as read")
    (pd / TN).write_text(json.dumps(T))
    r = [(t, h) for t, h in rows if h["module"] == DCHN]
    old = sorted({h["pins_file"] for _, h in r})
    for _, h in r:
        h["pins_file"] = TN
        # the signed dchn rst_n is a net of the master (glue: u_chn.rst_n(rst)), not a die wavefront pin: its centre pin sits in the slot clock keepout
        h["reset_from_master"] = {"kind": "internal", "content": h["inst"].removesuffix("__chn"), "pin": "rst_n",
                                  "source": "rtl/hbm_accel/cores_split/reform_1104b glue ot_pdie_serdes__p20glue.sv u_chn.rst_n(rst); master rst is the partition reset consumer"}
    (pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n")
    (pd / "part20_event.json").write_text(json.dumps({"schema": "opentallas.hbm_plan_event.part20", "core": "ot_pdie_serdes",
        "outline": {"from": OLD, "to": NEW}, "subs": ["ot_pdie_serdes_tx", "ot_pdie_serdes_rx", DCHN], "dchn_pins_file": TN, "rows": len(r),
        "cycles": "pma_rx to rx +2; uncorrectable to st[0] +2; e_flt to st[0] +2; pma_tx, tx, st[1] 0 (cycles/pdie.tsv)",
        "open": "rate matcher timed as synchronous on one SDC clock; the real CDC is proved in simulation only; die-level PMA clock note stays open"}, indent=1) + "\n")
    print("part 20 post:", len(r), "dchn rows; replaced tables", old)
