from pathlib import Path
import sys,json,subprocess,hashlib
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/"tools/die_plan"))
import gen_phys as G
import native_bb as N
w=Path(__file__).resolve().parent
kit=Path("/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/3fa87b84b18/items/dsdv_slice_kv512_C__t1/attempt_6/gen/dsdv_slice_kv512_C__t1")
tree=Path("/srv/opentallas-scratch2/claude/kw45/src_s81_pin_3c913dbdfb23_f2s4_cohort_d5d")
bb=kit/"rtl/ot_s81sl_egn_bb.v";native=tree/"rtl/dsrom_sys/s81_dv/eng/ot_s81sl_eg.sv"
top=w/"top.sv";top.write_text("module top(input clk,rst_n,i_v,input [31:0] i_x,eps,output o_v,o_f,output [31:0]o_r);\not_s81sl_egn #(.LA(4),.LM(5)) u(.clk(clk),.rst_n(rst_n),.i_v(i_v),.i_x(i_x),.eps(eps),.o_v(o_v),.o_f(o_f),.o_r(o_r));\nendmodule\n")
out=G.macro_param_blackboxes([("u","ot_s81sl_egn","","",0,0,"N")],[top,native,bb],w,tree)
assert out==[w/bb.name]
checks={}
for name,path in [("baseline",bb),("successor",out[0])]:
 cmd=["yosys","-Q","-T","-p",f"read_verilog -lib -sv {path}; read_verilog -sv {top}; hierarchy -check -top top; check"]
 r=subprocess.run(cmd,text=True,capture_output=True);(w/(name+".log")).write_text(r.stdout+r.stderr);checks[name]={"exit":r.returncode,"LM_error":"parameter named" in (r.stdout+r.stderr)}
assert checks["baseline"]["exit"]!=0 and checks["successor"]["exit"]==0,checks
hp=N.headers_params(out);passargs=[("ot_s81sl_egn","top","u","LM","1",f"{5:032b}"),("ot_s81sl_egn","top","u","LA","1",f"{4:032b}")]
assert not N.plan(passargs,hp)[2]
mut=N.plan([("ot_s81sl_egn","top","u","LM","1",f"{6:032b}")],hp)[2];assert mut
checks["mutant_rejected"]=mut;checks["fixed_abi_unchanged"]=G._module_header(bb.read_text(),"ot_s81sl_egn")==G._module_header(out[0].read_text(),"ot_s81sl_egn")
checks["sources"]={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [bb,native]};checks["added_cycles"]=0
(w/"result.json").write_text(json.dumps(checks,indent=1)+"\n");print(json.dumps(checks))
