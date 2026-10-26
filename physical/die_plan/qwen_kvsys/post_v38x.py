#!/usr/bin/env python3
"""KVG3-CORES 10-24: plan v3.8x = v3.8w + head_eighth slot shrink 285.12 -> 216 um (KV-G3 ruling on the KVG3-CORES
review-before-route: head_eighth std fill 22-33% of the 285.12 slot; ectl S face sat 25.92 um over head e6/e7 with 1818
detour pins).  Origins unchanged (the cores keep their lower-left corner), so in kv3_hg* / kv3_hgi*:
  ectl gap 1287.36 - (976.32 + 216) = 95.04 um; inter-head gaps 34.56 -> 103.68 um.
The 8 head_eighth pins files are re-spread onto 216 x 216 by core_pins_resize_v38x.py (same faces / order / rule) and
written in place (cores/kv3_head_eighth_e*_pins.json); this step only sets the outline.
    usage: post_v38x.py die_plan.json > die_plan.json"""
import json
import sys

NEW = [216.0, 216.0]


def main():
    p = json.load(open(sys.argv[1]))
    n = 0
    for tn, t in p["partition_types"].items():
        for c in t.get("hard_cores") or []:
            if c["module"].startswith("kv3_head_eighth_e"):
                assert c["outline_um"] in ([285.12, 285.12], NEW), (tn, c["inst"], c["outline_um"])
                if c["outline_um"] != NEW:
                    c["outline_um"] = list(NEW)
                    c["note"] = c.get("note", "") + " | v3.8x outline 285.12 -> 216 (KVG3-CORES review: fill, ectl gap)"
                    n += 1
    p["note"] = p.get("note", "") + " | v3.8x (KVG3-CORES 10-24): head_eighth slots 285.12 -> 216 um (fill, ectl/head gaps)"
    sys.stderr.write(f"post_v38x: {n} head_eighth cores -> 216 x 216\n")
    json.dump(p, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
