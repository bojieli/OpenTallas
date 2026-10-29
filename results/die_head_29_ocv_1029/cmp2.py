import json, sys
A, B = (json.load(open(p)) for p in sys.argv[1:3])
def strip(d):
    for top in ("count_aligned", "count_aligned_info"):
        for c in (d.get(top) or {}).values():
            c.pop("start_skew", None)
    return json.dumps(d, sort_keys=True)
out = {}
for top in ("count_aligned",):
    for c in A[top]:
        ra = {r["port"]: r for r in A[top][c]["start_skew"]["rows"]}; rb = {r["port"]: r for r in B[top][c]["start_skew"]["rows"]}
        da = [r["sta_sync_dist_ps"] for r in ra.values() if "sta_sync_dist_ps" in r]; db = [r["sta_sync_dist_ps"] for r in rb.values() if "sta_sync_dist_ps" in r]
        flips = [p for p in ra if ra[p]["ok"] != rb[p]["ok"]]
        reasons_changed = sum(1 for p in ra if ra[p].get("reason") != rb[p].get("reason"))
        kinds = sum(1 for r in ra.values() if r["launch"] and r["launch"].startswith("__st__")) , sum(1 for r in ra.values() if r["capture"] and r["capture"].startswith("__st__"))
        out[c] = dict(rows=len(ra), ok_old=sum(r["ok"] for r in ra.values()), ok_new=sum(r["ok"] for r in rb.values()), ok_flips=len(flips),
                      reason_changes=reasons_changed, min_dist_old=min(da, default=None), min_dist_new=min(db, default=None),
                      below100_old=sum(x < 100 for x in da), below100_new=sum(x < 100 for x in db), st_launch_capture=kinds)
print("rest_identical_without_start_skew", strip(A) == strip(B)); print(json.dumps(out))
