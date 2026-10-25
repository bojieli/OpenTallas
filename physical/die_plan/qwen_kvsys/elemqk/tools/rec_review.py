"""rec_review.py TYPE VERDICT PNG KITDIR_LOCAL "reasons" "fixes" -> results/geom_review JSON in the elem-qk worktree"""
import hashlib, json, sys, datetime, pathlib
t, v, png, kit, reasons, fixes = sys.argv[1:7]
k = pathlib.Path(kit)
h = hashlib.sha256(b"".join((k / f).read_bytes() for f in ("config.mk", "pins.json", "io.tcl", "macro_place.tcl") if (k / f).exists())).hexdigest()[:16]
o = pathlib.Path("/srv/opentallas-scratch/claude/wt/elem-qk/results/geom_review") / f"kv_g3_{t}__elemqk__{h}.json"
o.write_text(json.dumps({"element": f"kv_g3_{t}", "kit": f"claude/elem-qk-1024@88f5349870 tools (main 24b2da3433+ merged) + kv41 kit-rtl, plan copy die_plan_elemqk.json; kit intel1/intel2:/srv/opentallas-scratch2/claude/elem-qk/kvg3g/{t}",
  "verdict": v, "hash": h, "reasons": f"[ELEMQK-KV self-review] {png}: " + reasons, "fixes": fixes, "reviewer": "ELEMQK-KV (self)",
  "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "rule": "OWNER 2026-10-24 08:05 review before route"}, indent=1) + "\n")
print(o)
