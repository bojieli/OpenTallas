"""g0diff.py BASE_REPORT NEW_REPORT OUT_JSON: G0 findings diff by level/check (message-exact)."""
import json, sys, collections
a, b = (json.load(open(f)) for f in sys.argv[1:3])
def S(d, lv): return collections.Counter((f["check"], f["msg"]) for f in d["findings"] if f["level"] == lv)
out = dict(base=dict(verdict=a["verdict"], errors=a["errors"], warnings=a["warnings"]), new=dict(verdict=b["verdict"], errors=b["errors"], warnings=b["warnings"]))
for lv in ("ERROR", "WARN"):
    A, B = S(a, lv), S(b, lv); new, gone = B - A, A - B
    out[lv] = dict(new_by_check=dict(collections.Counter(c for c, _ in new.elements())), gone_by_check=dict(collections.Counter(c for c, _ in gone.elements())),
                   new=[m for _, m in sorted(new)] if lv == "ERROR" else None, gone=[m for _, m in sorted(gone)] if lv == "ERROR" else None)
json.dump(out, open(sys.argv[3], "w"), indent=1)
print(out["base"], out["new"]); print("ERR new", out["ERROR"]["new_by_check"], "gone", out["ERROR"]["gone_by_check"]); print("\n".join(out["ERROR"]["new"]))
print("WARN new", out["WARN"]["new_by_check"], "gone", out["WARN"]["gone_by_check"])
