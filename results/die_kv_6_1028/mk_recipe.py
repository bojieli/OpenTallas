"""DIE-KV-6: recipe_kv_2350 -> landed strap-form recipe: + clock_landing_table, ungzipped compose file, inner_uniform
expanded to the compose cohort splits (T__cl*) of each listed type.  usage: mk_recipe.py PLAN SIDECAR_REL OUT"""
import json, sys
plan, side, out = sys.argv[1:4]
r = json.load(open("physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv_2350.json"))
pt = json.load(open(plan))["partition_types"]
r["compose"] = r["compose"][:-3] if r["compose"].endswith(".gz") else r["compose"]
r["inner_uniform"] = sorted({t for s in r["inner_uniform"] for t in pt if t == s or t.startswith(s + "__")})
r["clock_landing_table"] = side
r["note"] = "DIE-KV-6 strap-form landed bind: recipe_kv_2350 + clock_landing_table + inner_uniform cohorts | " + r["note"]
json.dump(r, open(out, "w"), indent=1)
print("inner_uniform", r["inner_uniform"])
