"""QC batch 2 (COORD-approved): append D-QC-STM-ROM-INVENTORY ROM slots (codex/kits-wave-qc-2155@9ebdf335a
results/kits_wave_qc_2155/stm_rom_proposal/proposal.json) to the qwen_compute plan contents. Idempotent."""
import json, sys
plan, prop = sys.argv[1], sys.argv[2]
d = json.load(open(plan)); p = json.load(open(prop))
n = 0
for t, items in p["contents_append"].items():
    c = d["partition_types"][t].setdefault("contents", [])
    have = {x["inst"] for x in c}
    for it in items:
        if it["inst"] in have: continue
        it = dict(it); it["note"] = it["note"].replace("PROPOSED ", "") + " (QC batch 2 D-QC-STM-ROM-INVENTORY)"
        c.append(it); n += 1
json.dump(d, open(plan, "w"), indent=1)
open(plan, "a").write("\n")
print("appended", n)
