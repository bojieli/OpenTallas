#!/usr/bin/env python3
"""HBM-REFORM-B5 d44v part 33: composition and glue of ot_hfd_coll_q2n2_body_core = ot_q2nf_rest + ot_q2nf_qout, port list unchanged. Wires only.
    gen_comp.py OLD_BODY.sv REST_WRAPPED.sv PARENT.v GEN_DIR OUT_DIR
Every rest and tile bit is resolved by its source net name in the extract; an unresolved bit stops the run."""
import json, re, sys
from pathlib import Path
old_f, rest_f, parent_f, gen, out = [Path(x) for x in sys.argv[1:6]]
C = "ot_hfd_coll_q2n2_body_core"
def wrapper(txt, top):
    i = txt.index(f"module {top} ("); j = txt.index("\n);", i); hdr = txt[i:j]
    ports = []
    for m in re.finditer(r"^\s*(input|output)\s+wire\s*(?:\[(\d+):0\]\s*)?(\w+),?\s*$", hdr, re.M):
        ports.append((m[1], int(m[2]) + 1 if m[2] else 1, m[3]))
    e = txt.index("endmodule", j); body = txt[j:e]
    conn = {}   # extract bit name -> (pin, bit)
    for m in re.finditer(r"\.(\\\S+|\w+)\s*\(\s*(\w+)(?:\[(\d+)\])?\s*\)", body):
        conn[m[1].lstrip("\\")] = (m[2], int(m[3]) if m[3] else 0)
    return hdr, ports, conn
old_t = old_f.read_text(); rest_t = rest_f.read_text()
ohdr, oports, oc = wrapper(old_t, C); rhdr, rports, rc = wrapper(rest_t, "ot_q2nf_rest")
OW = {n: w for d, w, n in oports}; OD = {n: d for d, w, n in oports}
# ports whose extract name is not per bit (whole port wires in .x(y) form)
par = parent_f.read_text()
i = par.index("ot_q2nf_qout"); j = par.index(");", i); inst = par[i:j]
def lst(port):
    m = re.search(r"\." + port + r"\(\{(.*?)\}\)", inst, re.S)
    if m:
        out_ = []
        for x in [x.strip().lstrip("\\") for x in re.split(r"\s*,\s*", m[1].strip())][::-1]:
            r_ = re.fullmatch(r"(.*)\[(\d+):(\d+)\]", x)
            out_ += [f"{r_[1]}[{i}]" for i in range(int(r_[3]), int(r_[2]) + 1)] if r_ else [x]
        return out_
    m = re.search(r"\." + port + r"\(([^)]*)\)", inst); x = m[1].strip().lstrip("\\"); r_ = re.fullmatch(r"(.*)\[(\d+):(\d+)\]", x)
    return [f"{r_[1]}[{i}]" for i in range(int(r_[3]), int(r_[2]) + 1)] if r_ else [f"{x}[{i}]" for i in range({"lk_d":1090,"select_fault":18,"unavailable_fault":18,"pin_d":4773}.get(port,1))] if port in ("lk_d","select_fault","unavailable_fault") else [x]
bus = json.loads((gen / "q2n_tilebus.json").read_text()); pinmap = json.loads((gen / "q2n_pinmap.json").read_text())
OUTS = {}
for n, v in pinmap.items():
    for j_, (k, kd, b) in enumerate(v): OUTS[(k, kd, b)] = (n, j_)
A = []  # assign lines
rw = {n: w for d, w, n in rports}; rdir = {n: d for d, w, n in rports}
A.append(" wire clk_t=clk_qslots[9];")
MOVED = {pin for name, (pin, bit) in rc.items() if name in oc and pin in OW and oc[name] != (pin, bit)}
def is_same(n, d, w): return n in OW and OW[n] == w and OD[n] == d and n not in MOVED
for d, w, n in rports:
    if n != "clk_qslots" and not is_same(n, d, w): A.append(f" wire [{w-1}:0] r_{n};")
# ports the wrapper numbered differently (link 0 and 1 order): per bit by extract name
for name, (pin, bit) in rc.items():
    if pin in MOVED or (pin in rw and pin not in OW):
        if name in oc:
            p, q = oc[name]
            A.append(f" assign {p}[{q}]=r_{pin}[{bit}];" if rdir[pin] == "output" else f" assign r_{pin}[{bit}]={p}[{q}];")
NAME_SRC = {"reduce_out_data": "u_body.g_qcap[8].u_cap.src_d", "vm_as_il": "u_body.vm_as_il"}
def source(net):
    """expression for a tile input net"""
    if net in rc and rdir.get(rc[net][0]) == "output":
        p, b = rc[net]; return f"{'r_' if not is_same(p,'output',rw[p]) else ''}{p}[{b}]"
    m = re.fullmatch(r"inj_d\[(\d+)\]", net)
    if m: return net
    m = re.fullmatch(r"u_body\.reduce_out_data\[(\d+)\]", net)
    if m: p, b = oc[f"u_body.g_qcap[8].u_cap.src_d[{m[1]}]"]; return f"{p}[{b}]"
    m = re.fullmatch(r"u_body\.vm_as_il\[(\d+)\]", net)
    if m: p, b = oc[net]; return f"{p}[{b}]"
    sys.exit("unresolved input " + net)
L = {}
for port, w in (("captured", 9 * 545), ("cap_slot", 9), ("sink_slot", 15), ("sink_select", 60)):
    v = lst(port); assert len(v) == w, (port, len(v), v[:3]); L[port] = [source(x) for x in v]
    A.append(f" wire [{w-1}:0] t_{port}={{" + ",".join(reversed(L[port])) + "};")
# tile outputs into the rest
for port, w in (("lk_d", 1090), ("select_fault", 18), ("unavailable_fault", 18)):
    v = lst(port); assert len(v) == w, (port, len(v))
    A.append(f" wire [{w-1}:0] t_{port};")
    for b, net in enumerate(v):
        p, q = rc[net]; assert rdir[p] == "input", net
        A.append(f" assign r_{p}[{q}]=t_{port}[{b}];")
A.append(" wire [4772:0] t_pin_d;")
n = 0
for k, d, o, cw in bus:
    for i in range(cw):
        p, q = OUTS[(k, "d", d * cw + i)]; A.append(f" assign {p}[{q}]=t_pin_d[{o+i}];"); n += 1
assert n == 4773
for j_, (k, kd, b) in enumerate(pinmap["u_body_g_qout_0_g2_w_o_u_out_u_dst_v"]):
    p, q = rc[f"u_body.q2f_dv[{b}]"]; A.append(f" assign u_body_g_qout_0_g2_w_o_u_out_u_dst_v[{j_}]=r_{p}[{q}];")
# reduced/other ports: used bits of old pins that the rest reads through its own name
cons = []
for d, w, nm in rports:
    if nm == "clk_qslots": cons.append(".clk_qslots(clk_qslots[9:0])")
    elif is_same(nm, d, w): cons.append(f".{nm}({nm})")
    else: cons.append(f".{nm}(r_{nm})")
unused = [nm for d, w, nm in oports if d == "output" and nm not in [x[2] for x in rports] and not nm.startswith("u_body_g_qout_")]
assert not unused, unused
miss = [(d, w, nm) for d, w, nm in oports if d == "input" and nm not in rw and nm not in ("inj_d", "u_body_vm_as_il", "u_body_g_qcap_8_u_cap_src_d")]
assert not miss, miss
def comp(name, fs):
    s = "__fs" if fs else ""
    return "\n".join([f"// HBM-REFORM-B5 d44v part 33: GENERATED by gen_comp.py. {'Bench' if fs else 'Plan'} form. Wires only.", "`default_nettype none",
      ohdr.replace(f"module {C} (", f"module {name} (") + "\n);", *A,
      f" ot_q2nf_rest{s} u_r(" + ",".join(cons) + ");",
      f" ot_q2nf_qout{s} u_q(.clk(clk_t),.rst_n(rst_n),.captured(t_captured),.cap_slot(t_cap_slot),.sink_slot(t_sink_slot),.sink_select(t_sink_select),.lk_d(t_lk_d),.pin_d(t_pin_d),.select_fault(t_select_fault),.unavailable_fault(t_unavailable_fault));",
      "endmodule", "`default_nettype wire", ""])
out.mkdir(parents=True, exist_ok=True)
(out / f"{C}__p33comp.sv").write_text(comp(C + "__p33comp", False)); (out / f"{C}__p33fs.sv").write_text(comp(C + "__p33fs", True))
pm = ", ".join(f".{nm}({nm})" for d, w, nm in oports)
bodyp = ohdr[ohdr.index("(") + 1:]
(out / f"{C}__p33glue.sv").write_text(f"// HBM-REFORM-B5 d44v part 33: plan module {C} = thin parent glue of the split hard core (wires only).\n`default_nettype none\n"
  + f"module {C}__fcore ({bodyp}\n);\n {C}__p33comp u_core ({pm});\nendmodule\nmodule {C} ({bodyp}\n);\n {C}__fcore u_fcore ({pm});\nendmodule\n`default_nettype wire\n")
print("moved", sorted(MOVED)); print("comp ok; rest ports", len(rports), "old ports", len(oports), "assign lines", len(A))
