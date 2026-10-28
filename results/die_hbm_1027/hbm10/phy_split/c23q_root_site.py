"""DIE-HBM-10 C23q: ft_corridor siting of ONLY the unsited (PHY-family) ft slots of one type, keeping the already-sited
slots of that type (C22b sites, untouched) as reserved space.  ft_corridor.py itself re-sites every slot of a type and
fails root on L4x1 (a non-PHY slot this event does not change), so this driver calls the SAME ft_corridor._place_type
with the type's slot list restricted to the unsited slots and the RowAllocator pre-reserving every kept bit site.
usage: c23q_root_site.py PLAN_IN PLAN_OUT TOOLS_DIE_PLAN TYPE [--margin M]"""
import json, sys
src, dst, tools, tn = sys.argv[1:5]
margin = float(sys.argv[sys.argv.index("--margin") + 1]) if "--margin" in sys.argv else .98
sys.path.insert(0, tools)
import ft_corridor as F
import schema as S
raw = json.load(open(src)); ty = raw["partition_types"][tn]
orig = list(ty["ft_slots"])
keep = [s for s in orig if s.get("bit_sites_um")]
Base = F.RowAllocator


class Reserved(Base):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        for s in keep:
            cw, ch = s.get("bit_site_cell_um") or F.CELL
            for st in s["bit_sites_um"]:
                for x, y in st:
                    self.reserve_rectangle((x + .01, y + .01, x + cw - .01, y + ch - .01))
        # clock branch buffers + leg repeaters of this type: check.py CLOCK_BUF_HALO_UM (2 um) keep-out around each point
        ck = ty.get("clock") or {}
        for b in ck.get("branch_buffers") or []:
            for q in [b["xy"]] + [r["xy"] for r in b.get("leg_repeaters") or []]:
                self.reserve_rectangle((q[0] - 2.05, q[1] - 2.05, q[0] + 2.05, q[1] + 2.05))


F.RowAllocator = Reserved
model = S.Plan(raw)
mt = model.types[tn]
mt["ft_slots"][:] = [s for s in mt["ft_slots"] if not s.get("bit_sites_um")]
errs = []
try:
    led = F._place_type(model, tn, 405., margin, {}, {}, errs=errs)
except ValueError as ex:          # failed slots stay unsited (left to path_hbm_census_complete.py layered siting)
    led = []
    print("unsited:", ex)
done = {s["name"]: s for s in mt["ft_slots"]}
ty["ft_slots"] = [done.get(s["name"], s) for s in orig]
raw["partition_types"][tn]["ft_slots"] = ty["ft_slots"]
json.dump(raw, open(dst, "w"), indent=1)
print("sited", [s["name"] for s in ty["ft_slots"] if s.get("bit_sites_um") and s not in keep], "kept", [s["name"] for s in keep],
      "unsited", [s["name"] for s in ty["ft_slots"] if not s.get("bit_sites_um")])
