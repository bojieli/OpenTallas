"""DIE-S81-85 (3) bind name gate: plan names of the 31 new macros vs the bind's leaf naming + bound_macro_paths.resolve.
Context: a real svc_hi t4 bound module (codex_svc_hardening_1551 native_smd_c, bind of plan_h2_2249) + the leaves the
bind emits for -DOT_SVC_ATT_MEM_MACRO: dsdv_svc_att and dsdv_svc_rs_c are in asbuilt.dissolve, so their non-dissolved
children dsdv_svc_mem_la / dsdv_svc_mem_ar become leaves `// as-built <path>` + `<module> #(..) u_<sv_id(rel)> (`
(bind.py emit, short_id('u_' + r, 90)).  usage: bind_gate.py REPO PLAN_OUT TYPE BOUND_SV OUT_JSON [SW_LEAF]
SW_LEAF: the sw leaf module (dsdv_svc_mem_la; dsdv_svc_mem_lr under -DOT_SVC_ATT_RDPIPE, same instance paths)."""
import json, re, sys
from pathlib import Path
repo, plan, tn, bsv, out = sys.argv[1:6]
sw_leaf = sys.argv[6] if len(sys.argv) > 6 else "dsdv_svc_mem_la"
sys.path.insert(0, f"{repo}/tools/die_plan")
import bound_macro_paths as BMP
from bind import short_id
P = json.load(open(plan)); t = P["partition_types"][tn]
txt = Path(bsv).read_text()
ab = BMP.asbuilt_map(txt)
root = sorted({a.rsplit(".u.u_att.", 1)[0] + ".u" for a in ab if ".u.u_att." in a})
assert len(root) == 1, root
R = root[0]
asb = re.compile(r"(?m)^([ \t]*// as-built )")
leaves = [(sw_leaf, f"{R}.u_att.u_sw_mem")] + \
         [("dsdv_svc_mem_ar", f"{R}.u_att.g_wqm[{c}].g_pc[{p}].u_wq_mem") for c in range(3) for p in range(2)] + \
         [("dsdv_svc_mem_ar", f"{R}.u_att.u_qmem_mem"), ("dsdv_svc_mem_ar", f"{R}.u_pbuf_mem")]
rel = lambda path: path.split(".", 1)[1] if "." in path else path
add = "".join(f"    // as-built {p}\n    {m} #(.W(1)) {short_id('u_' + re.sub(r'[^A-Za-z0-9_]', '_', rel(p).replace('.', '_')), 90)} (\n        .clk(ck)\n    );\n"
              for m, p in leaves)
i = txt.rindex("endmodule")
txt2 = txt[:i] + add + txt[i:]
new = [c for c in t["contents"] if "DIE-S81-85 form A (3)" in c.get("note", "")]
rows = {r["inst"]: r for r in BMP.resolve(t, txt2)}
res = []
for c in new:
    r = rows.get(c["inst"])
    ok = bool(r) and r["physical_master"] == c["module"] and r["physical_inst"].startswith("u_bound.u_")
    res.append(dict(inst=c["inst"], ok=ok, physical_inst=r and r["physical_inst"], asbuilt=r and r["asbuilt"]))
bad = [x for x in res if not x["ok"]]
rep = dict(schema="opentallas.s81_svc_prov_bind_gate.v1", type=tn, bound_context=bsv, asbuilt_root=R, leaves=[p for _, p in leaves],
           macros=len(new), mapped=len(new) - len(bad), unmapped=bad, rows=res, verdict="PASS" if (len(new) == 31 and not bad) else "STOP")
Path(out).write_text(json.dumps(rep, indent=1) + "\n")
print(rep["verdict"], rep["macros"], rep["mapped"], res[0], res[-1])
