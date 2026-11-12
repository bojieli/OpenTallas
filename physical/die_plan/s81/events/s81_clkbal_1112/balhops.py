"""S81-CLKRUN-2: seam-pair damage of the balanced die_clock tree vs the 416.5 ps landing window, by corner and part-class."""
import sys, json, collections
sys.path.insert(0, "/srv/opentallas-scratch2/claude/die-recheck-1/s81/auto/db1da17a93ab/repo/tools/die_plan")
import die_clock as D
out = {}
cap = {}
orig_sp = D.seam_pairs
def sp(P, tbp):
    r = orig_sp(P, tbp); cap["sp"] = list(r); return r
D.seam_pairs = sp
orig_pcd = D.pair_clock_damage
calls = []
def pcd(*a, **k):
    r = orig_pcd(*a, **k); calls.append(r); return r
D.pair_clock_damage = pcd
class A: pass
a = A(); a.dir = "/srv/opentallas-scratch2/claude/s87bind/clkbal_1112/dieclock_run"; a.plan = "/srv/opentallas-scratch2/claude/die-recheck-1/s81/auto/db1da17a93ab/repo/physical/die_plan/s81/events/s81_ready11r_1112/plan_ready11r_db1da17a93ab.json"
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    D.cmd_report(a)
nseam = len(cap["sp"])
# cmd_report loops corners SS,TT,FF; each corner: seam rows first (nseam) then intra
per = []
i = 0
while i < len(calls):
    per.append((calls[i:i+nseam], i)); 
    # skip intra of unknown length: derive from remaining / number of corners left
    break
# robust: corners present = TT, FF -> total = 2*(nseam+nintra)
tot = len(calls); nint = tot//2 - nseam
res = {}
for ci, c in enumerate(("TT","FF")):
    base = ci*(nseam+nint)
    seam = calls[base:base+nseam]
    keys = cap["sp"]
    W = 416.5
    over = [(keys[j], seam[j]["max_damage_ps"]) for j in range(nseam) if seam[j]["max_damage_ps"] > W]
    grp = collections.Counter()
    for (k, d) in over:
        grp[(k[2] if len(k) > 2 else "?")] += 1
    res[c] = dict(pairs=nseam, over_416_5=len(over), max=max(s["max_damage_ps"] for s in seam),
                  over_300=sum(1 for s in seam if s["max_damage_ps"] > 300),
                  over_250=sum(1 for s in seam if s["max_damage_ps"] > 250),
                  by_where=dict(grp), worst=[(str(k[:2]), round(d,1)) for k, d in sorted(over, key=lambda x: -x[1])[:15]],
                  setup_max=max(s["setup_damage_ps"] for s in seam), hold_max=max(s["hold_damage_ps"] for s in seam))
json.dump(res, open("/srv/opentallas-scratch2/claude/s87bind/clkbal_1112/balhops_result.json", "w"), indent=1)
print(json.dumps(res, indent=1)[:3500])
