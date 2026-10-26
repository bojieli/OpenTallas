from infra_mesh_connect import connect
from infra_replay import load_db,physical_snapshot
r=connect("/work/mesh_straps.odb","/work/mesh_connected_widthfinal.odb")
a,b=load_db("/work/mesh_connected_tool.odb");x,y=load_db("/work/mesh_connected_widthfinal.odb")
for n in ["ck_mesh","VDD","VSS"]:assert physical_snapshot(b.findNet(n))==physical_snapshot(y.findNet(n)),n
assert r["mesh"]["ck_mesh"]["access_width_um"]==.16
print("ACTUAL_WIDTH_INFERENCE_EXACT_GEOMETRY_PASS")
