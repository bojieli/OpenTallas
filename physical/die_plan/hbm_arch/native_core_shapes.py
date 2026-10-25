#!/usr/bin/env python3
"""Native B2 physical-view shapes derived from explicit RTL instance parameters."""
import json
import re

def native_core_pins(plan, out, log):
    """Use the actual r18h5/B2 NPC2 delivery-lane shape, keeping retained pins on their proven faces/tracks.

    The legacy physical census had elaborated the NPC4 default. Native instances all explicitly bind NPC2;
    only the high, nonexistent PC-slot bits leave this view. Old pin tables remain as historical inputs.
    """
    limits = dict(fill_v_i=2, fill_bank_i=2, fill_slot_i=12, fill_epoch_i=32, fill_data_i=512)
    changed = []
    for tn, t in plan["partition_types"].items():
        for h in t.get("hard_cores", []):
            if h.get("module") != "ot_hbm_svc_vmdel_lane_n":
                continue
            src = out / h["pins_file"]
            pins = json.loads(src.read_text())
            kept = []
            for pin in pins:
                m = re.fullmatch(r"(.+)\[(\d+)\]", pin["name"])
                if m and m[1] in limits and int(m[2]) >= limits[m[1]]:
                    continue
                kept.append(pin)
            for bus, n in limits.items():
                bits = {int(m[1]) for pin in kept
                        if (m := re.fullmatch(re.escape(bus) + r"\[(\d+)\]", pin["name"]))}
                assert bits == set(range(n)), (tn, h["inst"], bus, len(bits), n)
            dst = src.with_name(src.stem + "_npc2.json")
            dst.write_text(json.dumps(kept) + "\n")
            h["pins_file"] = str(dst.relative_to(out))
            h["note"] = h.get("note", "") + "; native NPC2 fill ports (explicit as-built parameter)"
            changed.append(dict(type=tn, inst=h["inst"], old=len(pins), new=len(kept), pins_file=h["pins_file"]))
    (out / "native_core_shapes.json").write_text(json.dumps(dict(vmdel_npc=2, changes=changed), indent=1) + "\n")
    log.append(f"native delivery lanes: {len(changed)} NPC2 pin tables; removed only high NPC4 slot bits")


