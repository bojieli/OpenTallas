from pathlib import Path
import sys,shutil,json,hashlib,subprocess,copy
R=Path(__file__).parent;sys.path.insert(0,"/srv/opentallas-scratch2/claude/qc-pinaccess-o/r2/tools/die_plan");import kit_assembly as A
src=Path("/srv/opentallas-scratch2/claude/fable-fix-qc-cbglue/headseg44/group44/w1_44868/src/rtl/physical")
w=R/"assembly_proof";assert not w.exists();w.mkdir();master="qfd_qc_su_lane_w_l1_m44s1"
for n in range(1,8):shutil.copy2(src/f"qfd_qc_su_lane_w_l{n}_m44s1.sv",w/f"lane{n}.sv")
(w/(master+"_bb.v")).write_text("(* blackbox *) module "+master+"(input clk,input rst_n,input [759:0] c_i,output [247:0] c_o); endmodule\n")
head="module alias_parent(input clk,input rst_n,input [759:0] c_i, output [1735:0] c_o);\n"
for n in range(1,8):head+=f"qfd_qc_su_lane_w_l{n}_m44s1 u_lane{n}(.clk(clk),.rst_n(rst_n),.c_i(c_i),.c_o(c_o[{248*n-1}:{248*(n-1)}]));\n"
head+="endmodule\n";(w/"parent.sv").write_text(head);seal=hashlib.sha256(head.encode()).hexdigest()
children=[dict(master=master,native_master=f"qfd_qc_su_lane_w_l{n}_m44s1",inst=f"u_lane{n}") for n in range(1,8)]
contracts=[dict(master=c["master"],native_master=c["native_master"],instance=c["inst"],child_params={},binding_sha256=seal) for c in children]
# Wrong seal must fail atomically on copied full production wrapper sources.
bad=copy.deepcopy(contracts);bad[2]["binding_sha256"]="0"*64
before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in w.iterdir()}
try:A.assemble_fixed_children(w,children,bad)
except ValueError as e:mutant=str(e)
else:raise AssertionError("Wrong binding seal accepted")
assert before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in w.iterdir()}
rec=A.assemble_fixed_children(w,children,contracts)
script="read_verilog "+" ".join(str(p) for p in sorted(w.glob("*.v")))+" "+" ".join(str(p) for p in sorted(w.glob("*.sv")))+"; hierarchy -check -top alias_parent; write_json "+str(w/"hierarchy.json")
with (w/"yosys.log").open("w") as log:subprocess.run(["yosys","-Q","-q","-p",script],stdout=log,stderr=subprocess.STDOUT,check=True)
inv=A.hierarchy_inventory(json.load(open(w/"hierarchy.json")),"alias_parent",children);assert not inv["problems"],inv
cells=json.load(open(w/"hierarchy.json"))["modules"]["alias_parent"]["cells"];assert len(cells)==7 and {c["type"] for c in cells.values()}=={master}
out=dict(verdict="PASS",shape=dict(input_bits=760,per_instance_output_bits=248,instances=7),master=master,all7_actual_wrapper_sources_used=True,assembly_receipt=rec,inventory=inv,negative_control=dict(verdict="REFUSED",reason=mutant,source_bytes_unchanged=True),scope="Assembly/inventory proof only; exact behavioral alias congruence is separate; actual W1 physical signoff remains required",production_seal_rule="Seal SHA of actual emitted post-bind parent source; this fixture SHA must never be reused for production")
(R/"assembly_proof_receipt.json").write_text(json.dumps(out,indent=2)+"\n");print(json.dumps({"verdict":"PASS","master_count":1,"instances":7,"mutant":"REFUSED"}))
