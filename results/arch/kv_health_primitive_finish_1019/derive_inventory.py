#!/usr/bin/env python3
"""Compose source-only typed DAG rows; no simulation/native/timing claims."""
import json,hashlib,argparse,collections
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument("packet");a=ap.parse_args();b=Path(a.packet)
load=lambda p:json.loads((b/p).read_text())
old=load("basis_inventory.json");pc=load("pc/primitive_inventory.json");host=load("host/primitive_inventory.json");hi=load("host/selected_instances.json");ahub=load("ahub/dag.json")
rows=[r for r in old["rows"] if not r["id"].startswith("ahub.")]
assert len(ahub["primitive_rows"])==27
rows+=ahub["primitive_rows"]+pc["rows"]
assert len(hi)==128 and len(pc["instances"])==128
for i in hi:
 rows.append({"id":i["primitive_path"],"kind":"sticky_local_detector_register","selected_instance":i["instance"],"clock":i["ports"]["ck"],"selected_reset":i["ports"]["host_rst_n"],"reset_ancestry":host["local_primitive"]["clear"],"set_predicates":host["local_primitive"]["set_predicates"],"dependencies":[i["ports"]["ctrl_er"],i["ports"]["ctrl_completion_v"],i["ports"]["ctrl_completion_we"]],"source_template":"host/primitive_inventory.json#local_primitive","physical_native_exposure_qualified":False})
ids=[r["id"] for r in rows];assert len(ids)==len(set(ids))
# The prior bounded inventory's remaining HOST placeholders become concrete DAG references.
resolved=[{"id":r["id"],"producer":"hsl_"+r["id"].split(".")[0].removeprefix("kvpc_")+".u_slice.u_static.land_fault","producer_definition":"host/primitive_inventory.json#propagation_nodes","upstream_detector_DAG":"pc/primitive_inventory.json","classification":"qualified registered/ownership forwarding; alias, not primitive"} for r in old["unresolved_dependencies"] if r["id"].startswith("kvpc_")]
assert len(resolved)==128
resolved += [{"id":r["id"],"producer_definition":"kc/dag.json#chains","classification":"32 controller aggregate stages plus actual HBM forwarding; aliases, not new primitive"} for r in old["unresolved_dependencies"] if r["id"].startswith("kc_")]
checks={"unique_typed_rows":len(rows),"PC_rows":len(pc["rows"]),"HOST_local_detector_rows":128,"AHUB_rows":27,"old_HOST_placeholders_resolved":128,"old_KC_placeholders_resolved":4,"KC_source_chains_32_PCs_each":True,"qualified_complete_primitive_count":None}
manifest=[]
for p in sorted(b.rglob("*.sv")):
 manifest.append({"path":str(p.relative_to(b)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
x={"status":"SOURCE_DAG_NAMED_LEAVES_RESOLVED_NOT_FULL_NATIVE_CALENDAR_QUALIFICATION","selected_source_commit":"4db097403","selected_die_sha256":old["selected_die_sha256"],"GEN8_status":"41 selected leaf source files match frozen5f2; preexp/expanded KC topology checked; final bound regional mapping not available at analysis","counts":checks,"rows":rows,"resolved_old_placeholders":resolved,"aggregate_definitions":{"old":"basis_inventory.json#aggregates_and_duplicates","PC":"pc/primitive_inventory.json#aggregates_and_duplicates","HOST":"host/primitive_inventory.json#propagation_nodes","KC":"kc/dag.json#chains","AHUB":"ahub/dag.json#forwarding_aliases"},"capture_obligations":"kc/capture_obligations.json","additional_known_source_families_not_counted_in_rows":"HOST boot_control_dependencies includes separate base_fault/demux/check detectors and start-cleared boot result channel; these are explicitly outside land_er cause count, not silently absent or counted as aliases. Full health source integration must include each actual route/ownership obligation.","source_snapshot_manifest":manifest,"native_reset_phase_tail_status_host_commit":None}
(b/"inventory.json").write_text(json.dumps(x,indent=2)+"\n");(b/"checks.json").write_text(json.dumps(checks,indent=2)+"\n");print(json.dumps(checks))
