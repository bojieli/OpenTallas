# OR-CTS-PROBE-1: stand-alone TritonCTS problem from one die_trial clock region (sinks at routed tap xy, root at region LCA).
import json, sys, os, math
reg_json, out_dir, mode = sys.argv[1:4]          # mode: qc | s81
r = json.load(open(reg_json)); os.makedirs(out_dir, exist_ok=True)
xs = [t["xy"][0] for t in r["taps"]]; ys = [t["xy"][1] for t in r["taps"]]
root = (r["lca_node"]["x"], r["lca_node"]["y"])
cores = []
if mode == "qc":
    P = json.load(open(sys.argv[4])); pp = [p for p in P["partitions"] if p["name"] == "c_W2_bn_01"][0]; T = P["partition_types"]; ty = T[pp["type"]] if isinstance(T, dict) else [x for x in T if x.get("module") == pp["type"]][0]
    ox, oy = pp["origin_um"]; W, H = ty["outline_um"]; assert pp["orient"] == "MX"
    for hc in ty["hard_cores"]:
        (x0, y0), (w, h) = hc["origin_um"], hc["outline_um"]
        cores.append(dict(inst=hc["inst"], rect=[ox + x0, oy + H - y0 - h, ox + x0 + w, oy + H - y0]))
    xs += [c["rect"][0] for c in cores] + [c["rect"][2] for c in cores]; ys += [c["rect"][1] for c in cores] + [c["rect"][3] for c in cores]
M = 60.0
DX0 = math.floor((min(xs + [root[0]]) - M) / 0.216) * 0.216; DY0 = math.floor((min(ys + [root[1]]) - M) / 1.08) * 1.08
DX1 = max(xs + [root[0]]) + M; DY1 = max(ys + [root[1]]) + M
def loc(x, y): return (round(x - DX0, 4), round(y - DY0, 4))
core_taps = [t for t in r["taps"] if "__clk_c" in t["port"]]; glue = [t for t in r["taps"] if "__clk_c" not in t["port"]]
ins = {}
for c in ("TT", "FF"):
    if core_taps:
        ins[c] = round(r["lat_" + c][core_taps[0]["port"]] - r["lat_" + c][glue[0]["port"]], 1)
# assign core taps to cores (nearest rect)
lef, lib = [], []
def dist(rect, p): return math.hypot(max(rect[0] - p[0], 0, p[0] - rect[2]), max(rect[1] - p[1], 0, p[1] - rect[3]))
for t in core_taps:
    c = min(cores, key=lambda c: dist(c["rect"], t["xy"])); t["core"] = c["inst"]; t["core_dist"] = round(dist(c["rect"], t["xy"]), 2)
    c.setdefault("taps", []).append(t)
lef.append("VERSION 5.8 ;\nBUSBITCHARS \"[]\" ;\nDIVIDERCHAR \"/\" ;\n")
for c in cores:
    x0, y0, x1, y1 = c["rect"]; n = "A0SINK_" + c["inst"]
    pins = ""
    for i, t in enumerate(c["taps"]):
        px = min(max(t["xy"][0], x0 + 0.5), x1 - 0.5) - x0; py = min(max(t["xy"][1], y0 + 0.5), y1 - 0.5) - y0
        pins += f"  PIN clk{i}\n    DIRECTION INPUT ;\n    USE CLOCK ;\n    PORT\n      LAYER M7 ;\n        RECT {px-0.04:.3f} {py-0.04:.3f} {px+0.04:.3f} {py+0.04:.3f} ;\n    END\n  END clk{i}\n"
    lef.append(f"MACRO {n}\n  CLASS BLOCK ;\n  ORIGIN 0 0 ;\n  SIZE {x1-x0:.3f} BY {y1-y0:.3f} ;\n  SYMMETRY X Y ;\n{pins}  OBS\n" +
               "".join(f"    LAYER M{k} ;\n      RECT 0 0 {x1-x0:.3f} {y1-y0:.3f} ;\n" for k in range(1, 7)) + f"  END\nEND {n}\n")
    c["master"] = n
lef.append("END LIBRARY\n")
for C in ("TT", "FF"):
    s = ['library (a0sink_%s) {\n delay_model : table_lookup;\n time_unit : "1ps";\n voltage_unit : "1V";\n current_unit : "1mA";\n'
         ' capacitive_load_unit (1,ff);\n pulling_resistance_unit : "1kohm";\n leakage_power_unit : "1nW";\n nom_voltage : 0.7; nom_temperature : 25; nom_process : 1;\n' % C]
    for c in cores:
        s.append(f" cell ({c['master']}) {{\n  area : 1;\n  is_macro_cell : true;\n")
        for i, _ in enumerate(c["taps"]):
            s.append(f"  pin (clk{i}) {{\n   direction : input;\n   clock : true;\n   capacitance : 3.0;\n"
                     f"   timing () {{ timing_type : max_clock_tree_path; timing_sense : positive_unate; cell_rise (scalar) {{ values (\"{ins[C]}\"); }} cell_fall (scalar) {{ values (\"{ins[C]}\"); }} }}\n"
                     f"   timing () {{ timing_type : min_clock_tree_path; timing_sense : positive_unate; cell_rise (scalar) {{ values (\"{ins[C]}\"); }} cell_fall (scalar) {{ values (\"{ins[C]}\"); }} }}\n  }}\n")
        s.append(" }\n")
    s.append("}\n"); lib.append(("".join(s), C))
if cores:
    open(f"{out_dir}/a0sink.lef", "w").write("".join(lef))
    for s, C in lib: open(f"{out_dir}/a0sink_{C}.lib", "w").write(s)
# verilog
v = ["module region (clk);\n input clk;\n"]
for i, t in enumerate(glue): v.append(f" DFFHQNx1_ASAP7_75t_R g{i} (.CLK(clk), .D(1'b0), .QN());\n")
for c in cores: v.append(f" {c['master']} {c['inst']} (" + ", ".join(f".clk{i}(clk)" for i, _ in enumerate(c["taps"])) + ");\n")
v.append("endmodule\n"); open(f"{out_dir}/region.v", "w").write("".join(v))
pl = [f"set DIE {{0 0 {DX1-DX0:.3f} {DY1-DY0:.3f}}}", f"set ROOT {{{loc(*root)[0]} {loc(*root)[1]}}}"]
for i, t in enumerate(glue):
    x, y = loc(*t["xy"]); x = round(round(x / 0.054) * 0.054, 3); y = round(round(y / 0.27) * 0.27, 3)
    pl.append(f"ot_fix g{i} {x} {y}")
for c in cores:
    x, y = loc(c["rect"][0], c["rect"][1]); pl.append(f"ot_fix {c['inst']} {x} {y}")
open(f"{out_dir}/place.tcl", "w").write("\n".join(pl) + "\n")
meta = dict(origin=[DX0, DY0], root=root, glue=[dict(inst=f"g{i}", port=t["port"], xy=t["xy"]) for i, t in enumerate(glue)],
            cores=[dict(inst=c["inst"], rect=c["rect"], taps=[dict(port=t["port"], pin=f"clk{i}", core_dist=t["core_dist"]) for i, t in enumerate(c["taps"])]) for c in cores],
            insertion_rel=ins)
json.dump(meta, open(f"{out_dir}/meta.json", "w"), indent=1)
print("die", DX1 - DX0, DY1 - DY0, "glue", len(glue), "cores", len(cores), "core taps", [(t["port"], t["core"], t["core_dist"]) for t in core_taps], "ins", ins)
