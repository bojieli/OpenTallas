"""KV-KITS-3 10-27 (COORD ruling 04:26 (1)): io_cor +1 station on ft6/ft9/ft13/ft14/ft19 (reach is structural),
then the FT stations are sited by tools/die_plan/ft_corridor.py.  Step 1 only: bump the stations (writes PLAN_OUT)."""
import json, sys
src, dst = sys.argv[1:3]
SLOTS = ("ft6", "ft9", "ft13", "ft14", "ft19")
d = json.load(open(src))
n = 0
for s in d["partition_types"]["kv3_io_cor"]["ft_slots"]:
    if s["name"] in SLOTS:
        s["stations"] += 1; n += 1
assert n == len(SLOTS), n
open(dst, "w").write(json.dumps(d))
print("bumped", n)
