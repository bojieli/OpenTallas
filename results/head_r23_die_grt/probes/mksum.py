import json, re, shutil, subprocess, collections
from pathlib import Path
W = Path("/srv/opentallas-scratch2/claude/wt/claude-head-r23"); R = Path("/srv/opentallas-scratch2/claude/head-r23")
E = W / "results/head_r23_die_grt"; E.mkdir(parents=True, exist_ok=True)
for c in ("TT", "FF"):
    shutil.copy(R / f"clk/combo_{c}.log", E / f"combo_{c}.log")
for f in ("attachment_receipt.json", "encoder_receipt.json"):
    shutil.copy(R / "clk" / f, E / f)
shutil.copy(R / "r23_jogs.png", E / "r23_jogs.png")
M = json.load(open(R / "clk/mesh.json")); cs = M["meta"]["clock_shield"]
st = json.load(open(R / "clk/shield_ties.json"))
(E / "shield_ties_summary.json").write_text(json.dumps(dict(record=st["record"], metal_census={k: v for k, v in st["metal_census"].items() if k != "rows"}, clock_shield=cs), indent=1) + "\n")
def grt(c):
    t = (R / f"clk/combo_{c}.log").read_text()
    tot = re.search(r"^Total\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s+(\d+) /\s+(\d+)", t, re.M)
    use = {m.group(1): float(m.group(2)) for m in re.finditer(r"^(M\d)\s+\d+\s+\d+\s+([\d.]+)%", t, re.M)}
    return dict(overflow_total=int(tot.group(6)), routed_nets=int(re.search(r"Routed nets: (\d+)", t).group(1)),
                wirelength_um=int(re.search(r"Total wirelength: (\d+)", t).group(1)), usage_pct=use,
                runtime=re.search(r"Global routing runtime = (\S+)", t).group(1), exit=re.search(r"EXIT (\d+)", t).group(1),
                db_written="OT_DB_WRITTEN" in t, odb=f"intel2:{R}/clk/combo_{c}.odb")
jog = collections.defaultdict(list); stub = collections.defaultdict(list)
for t in M["taps"]:
    mb = t["mesh_boundary"]; jog[mb["endpoint_kind"]].append(mb["jog_um"]); stub[mb["endpoint_kind"]].append(mb.get("stub_um", 0.))
q = lambda v: dict(n=len(v), max=round(max(v), 3), median=round(sorted(v)[len(v) // 2], 3))
S = dict(schema="opentallas.head_r23.die_grt_clock.v1",
    generated=subprocess.check_output(["date", "-Iseconds"]).decode().strip(),
    plan="results/head_r22_die_grt/die_plan_r22_signedviews.json (plan 7af81995 + signed tag-a/tag-b capsule views; unchanged, no plan delta)",
    kit="intel2:/srv/opentallas-scratch2/claude/head-r22/kit (R22 die_trial kit, reused unchanged)",
    clock_inputs=dict(build="codex-head-clock-1355/driver_boundary_lowerrows", straps="codex-head-clock-1355/driver_rows/straps.json",
                      endpoints="codex-head-clock-1355/r21_edge_taps/clock_endpoints.json (3654 = 1320 native core + 2334 grid)"),
    fix_a="head_attach_actual_mesh.py --plan: PG-aware M8 jog track per endpoint (drawn-shield envelope clear of every die M8 PG stripe incl. PHY domains, M8 mesh straps, shielded M8 H-tree legs and other jogs) to the nearest M9 strap spanning the track (<=450); endpoint within 1.08 um of an M8 strap ports on the strap; explicit_clock_mesh jog_y",
    jog_um=dict((k, q(v)) for k, v in jog.items()), stub_um=dict((k, q(v)) for k, v in stub.items()),
    stub_note="port node on the legal M8 track; the published pin is <= 1.06 um away in y (local M7 stub to the pin, not drawn in the die combo). Signed core pins (1320 native) NOT moved.",
    metal_census=dict(shorts=cs["metal_shorts"], spacing=cs["metal_spacing"], unflanked=cs["unflanked_segments"]),
    vss_ties=dict(vss_tied=cs["vss_tied"], freeze_evidence_ok=cs["freeze_evidence_ok"], grid_vias=st["record"]["grid_vias"],
                  shield_shield_vias=st["record"]["shield_shield_vias"], shield_stripes=st["record"]["shield_stripes"],
                  untied_stripes=st["record"]["untied_stripes"], pg_shorts=st["record"]["pg_shorts"]),
    grt_cmd="global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion",
    grt={c: grt(c) for c in ("TT", "FF")},
    post_grt="routed DB written before the diagnostic tree export (die_clock_mesh combo); explicit meshes skip the native-RC ckm_* tree export (R22 exit 139); EXIT 0",
    die_sta="NOT RUN: no explicit-mesh sign-off (mesh MC) input for die_sta_related --mesh-signoff yet",
    verdict="GRT0 PASS incl. fixed clock metal, 0 shorts / 0 spacing, vss_tied true; die STA open")
(E / "SUMMARY.json").write_text(json.dumps(S, indent=1) + "\n")
print(json.dumps(S, indent=1))
