import copy,json,re
from pathlib import Path
import pytest
import qc_r29_coresu as Q
from qc_su_lane_cut import cut
def fixture():
 s="module orig(input wire clk,input wire rst_n,input wire [7:0] x,output wire [301:0] y);\n    wire [7:0] x_q;\n    assign x_q=x;\n"
 for k in ["exp","rsq","head","rcp"]:s+=f"    wire w_u_{k}0_y;\n"
 for n,w in [("a",49),("kv_wdata",32),("m",196),("wrom_addr",24),("z",1)]:
  s+=f"    wire [{w-1}:0] w_u_lrly0_{n};\n"
 for k in ["exp","rsq","head","rcp"]:
  s+=f"    // as-built root.u_{k}0\n    leaf u_u_{k}0 (\n        .clk(clk),\n        .rst_n(rst_n),\n        .x(x_q),\n        .y(w_u_{k}0_y)\n    );\n"
 s+="    // as-built root.u_lrly0\n    leaf u_u_lrly0 (\n        .clk(clk),\n        .rst_n(rst_n),\n        .x(x_q),\n"
 s+=",\n".join(f"        .{n}(w_u_lrly0_{n})" for n in ["a","kv_wdata","m","wrom_addr","z"])+"\n    );\n"
 return s+"    assign y={w_u_lrly0_z,w_u_lrly0_wrom_addr,w_u_lrly0_m,w_u_lrly0_kv_wdata,w_u_lrly0_a};\nendmodule\n"
def test_scoped_narrow_parent_zero_reconstruction():
 rtl,frame,r=cut(fixture(),0,"qfd_qc_su_lane_e_l0",constant_outputs="su_lane0_zero24")
 assert r["output_bits"]==278 and r["narrowing"]["old_width"]==302
 assert len(r["narrowing"]["removed"])==24 and r["added_cycles"]==0
 assert "output wire [277:0] c_o" in rtl
 assert len(re.findall(r"assign w_u_lrly0_.*= 1'b0;",frame))==24
 assert len(re.findall(r"assign c_o\[",rtl))==278
 assert r["narrowing"]["old_to_new"]["301"]==277
def test_wrong_semantic_role_fail_closed():
 with pytest.raises(ValueError,match="semantic/index"):
  cut(fixture().replace("kv_wdata","kv_payload"),0,"qfd_qc_su_lane_e_l0",constant_outputs="su_lane0_zero24")
 with pytest.raises(ValueError,match="approved"):
  cut(fixture(),0,"another",constant_outputs="su_lane0_zero24")
def test_owned_plan_fields_preserve_geometry(tmp_path):
 repo=Path(__file__).resolve().parents[2]
 src=json.loads((repo/"physical/die_plan/qwen_compute/die_plan.json").read_text())
 dst,r=Q.apply(src)
 assert len(r["su"])==16 and len(r["face_memories"])==30 and r["added_cycles"]==0
 assert dst["partition_types"].keys()==src["partition_types"].keys()
 for tn,t in dst["partition_types"].items():
  for k in ["outline_um","ft_slots","buses"]:assert t.get(k)==src["partition_types"][tn].get(k)
  for a,b in zip(t.get("hard_cores",[]),src["partition_types"][tn].get("hard_cores",[])):
   for k in ["outline_um","origin_um","orient"]:assert a.get(k)==b.get(k)
 for tn in Q.FACE_BINDINGS:
  mem=[m for m in dst["partition_types"][tn]["contents"] if m["module"].startswith("ot_sram")]
  for i,a in enumerate(mem):
   ax,ay=a["origin_um"];aw,ah=a["outline_um"]
   for b in mem[i+1:]:
    bx,by=b["origin_um"];bw,bh=b["outline_um"]
    assert ax+aw+10.8<=bx or bx+bw+10.8<=ax or ay+ah+10.8<=by or by+bh+10.8<=ay
