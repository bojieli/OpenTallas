"""HEAD-FORM-R3 W13 candidate marker v3 (candidate_w12.py pattern; adds CREDITED-UNVERSIONED to take_states). argv: NAME PREPNAME EVENT PLAN_SHA12 TOOLS_SHA40 ONLY_ITEMS(comma) SMOKE_DETAIL_FILE HOST...
stdin: live kit_wave die entry of s81_head (must be the W12f event)."""
import hashlib, json, sys
from pathlib import Path
root = Path("/srv/opentallas-scratch2/claude")
name, prepname, event, want, tools, only, detail = sys.argv[1:8]; hosts = list(dict.fromkeys(sys.argv[8:])); assert len(hosts) >= 2
tree = root / f"kw45/snap_s81_head/s81_head_{name}"
prep_root = tree / "physical/die_plan/s81_head/prep/NF15f"
prep = prep_root / prepname
plan = prep / "source_plan.json"; sidecar = prep / "source_sidecar.json"
band_base = prep_root / "prep_r18w8_b/source_plan.json"
remap_base = prep_root / "prep_r18w12_int_1126/source_plan.json"
release = tree / f"results/head_native_release_nf15f_{name}/native_release_receipt.json"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan_sha = sha(plan); sidecar_sha = sha(sidecar)
assert plan_sha.startswith(want), plan_sha
assert sha(remap_base).startswith("607dd5dd5c82")
assert band_base.is_file() and release.is_file()
prepared = json.loads((prep / "wave_prepare.json").read_bytes())
assert prepared["prepared_plan_sha256"] == plan_sha and prepared["sidecar_sha256"] == sidecar_sha
q = json.loads(release.read_bytes()); assert len(q["bindings"]) >= 12
live = json.load(sys.stdin)
TS = list(live["take_states"]) + [x for x in ["CREDITED-UNVERSIONED"] if x not in live["take_states"]]
assert live["event"] == "head_rp21z20NF15f_r18w12_1126", live["event"]
manifest = (tree / ".src-manifest.sha256").read_text().strip(); assert len(manifest) == 64
assert len(tools) == 40
items = [i for i in only.split(",") if i]
marker = {
 "die": "s81_head", "tree": str(tree), "manifest_hash": manifest, "src_manifest_sha": manifest,
 "tools_sha": tools, "hosts": hosts, "plan": str(plan), "plan_sha256": plan_sha,
 "sidecar": str(sidecar), "sidecar_sha256": sidecar_sha, "native_reset_receipt": str(release),
 "band_base": str(band_base), "remap_base": str(remap_base), "frozen_kit_tree": "",
 "physical_qualified": False, "most_recent_fable_verdict": "", "smoke": "PASS",
 "smoke_detail": Path(detail).read_text().strip(),
 "config": {
  "event": event, "tools_sha": tools, "gen_host": hosts[0], "gen_hosts": hosts,
  "kit_rtl": {"mode": "script", "script": str(tree / "physical/die_plan/s81_head/kit_wave/kit_rtl.sh")},
  "gen_args": ["--clock-landing", str(sidecar), "--hold-ff-margin", "0"],
  "review_before_route": {"event": event, "all_items": True, "required": True},
  "auto_visual_review_skip": ["*"], "tools_from_rt": True,
  "only_items": items,
  "take_states": TS,
  "take_states_note_w13": "HEAD-FORM-R3 11-27 (HEAD-INT-R3 PINREG ruling (a), COORD 21:00 cut): CREDITED-UNVERSIONED added so the PINREG-W13 hd_host_e rebuild launches; scope stays only_items (hd_host_w, hd_mesh, hd_serdes are CREDITED-UNVERSIONED but outside only_items)",
 },
 "die_gen_env": {"OT_SIGNED_VIEW_SHA": str(tree / "physical/die_plan/s81_head/kit_wave/signed_view_sha_head.json")},
 "records": {},
}
json.dump({"marker": marker, "optimistic": True}, sys.stdout, indent=1); print()
