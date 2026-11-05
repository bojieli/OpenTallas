#!/usr/bin/env python3
"""HBM-BIND-5 candidate top t1 from the tip aliased top, netlist-level, plan unchanged:
 (1) one ot_hnx_idxn_kb_ctl per role drives the 7 keybuf control ports (TOK-HBM-3 provider; d4g qctl: key_row 0, pre 0, single-row calendar).
 (2) S-role emission: for every N-role instance whose plan core is X__q1 and X__q0 exists in the hub, with no S instance in the top, emit a copy named by role swap,
     mapped to the q0 half. Inputs: role-swapped net when an S driver exists (another copy or the top); otherwise an explicit native_required__ obligation, never a tie.
 No S instance is emitted for a family without a planned q0 core.
usage: gen_top_t1.py TOP.sv MAP_IN PLAN OUT.sv MAP_OUT REPORT"""
import json, re, sys, collections
top, mi, plan, out, mo, rp = sys.argv[1:7]
pads = json.load(open(sys.argv[7]))["pads"] if len(sys.argv) > 7 else {}
src = open(top).read()
inst_re = re.compile(r'\n {1,2}(\w+)(?: #\(([^\n]*?)\))? (\w+) \(\n(.*?)\n {0,2}\);', re.S)
insts = {m.group(3): dict(master=m.group(1), params=m.group(2) or "", body=m.group(4)) for m in inst_re.finditer(src)}
decl = {m.group(3): (m.group(1) or "wire", int(m.group(2)) + 1) for m in re.finditer(r'\n  (input|output)? ?wire \[(\d+):0\] (\w+);', src)}
swap = lambda s: s.replace("_NW", "_SW").replace("_NE", "_SE")
P = json.load(open(plan)); T = P["partition_types"]; parts = {p["name"]: p for p in P["partitions"]}
hc = {n: {h["inst"] for h in T[parts[n]["type"]].get("hard_cores", [])} | {h["inst"] for h in T[parts[n]["type"]].get("contents", [])} for n in ("NW_hub", "NE_hub")}
M = json.load(open(mi)); mp = M["parts"]
rep = dict(kb=[], emit=[], obligations=[], skipped=[])
# which N instances have a planned q0 half and no S instance
emit = {}
for i in insts:
    if not re.search(r"_N[EW]", i) or swap(i) in insts: continue
    h = mp.get(i)
    if not h: continue
    q = h[1]
    home = "NW_hub" if "_NW" in i else "NE_hub"      # the q0 half stays in the hub even when the N half moved (B0)
    q0 = q.replace("__q1", "__q0") if q.endswith("__q1") else q + "__q0"
    if q0 in hc[home]: emit[i] = (home, q0)
    else: rep["skipped"].append(dict(inst=i, q=q))
# hcoll* families carry a C25c q0 named by parts
print("emit", len(emit), collections.Counter(re.sub(r"_N[EW].*", "", i) for i in emit))
outputs_of = {}
drv = {}
for i, x in insts.items():
    for pm in re.finditer(r'\.(\w+)\((\w+)\[', x["body"]):
        if pm.group(2) == f'{i}__{pm.group(1)}': drv[pm.group(2)] = i
new_outs = {}
for t in emit:
    ni = swap(t)
    for pm in re.finditer(r'\.(\w+)\((\w+)\[', insts[t]["body"]):
        if pm.group(2) == f'{t}__{pm.group(1)}': new_outs[f'{ni}__{pm.group(1)}'] = decl[pm.group(2)][1]
frag = []; wires = {}; closed = []; newin = {}
def s_driven(n):
    return n in new_outs or n in drv or (n in decl and decl[n][0] == "wire")
for t, (hub, q0) in sorted(emit.items()):
    ti = insts[t]; ni = swap(t); lines = []
    for ln in ti["body"].split("\n"):
        m = re.match(r'\s*\.(\w+)\((.*)\),?\s*$', ln)
        if not m: lines.append(ln); continue
        port, expr = m.group(1), m.group(2)
        if expr.startswith(f"{t}__{port}["):
            n2 = f"{ni}__{port}"
            lines.append(ln.replace(f"{t}__{port}", n2)); continue
        names = re.findall(r'(\w+)\[\d+:\d+\]', expr)
        if not any(swap(n) != n for n in names):
            lines.append(ln); continue
        def sub(mm):
            n = mm.group(1); s = swap(n)
            if s == n: return mm.group(0)
            if s_driven(s): return s + mm.group(0)[len(n):]
            return None
        ok = True
        def sb(mm):
            global ok
            r = sub(mm)
            if r is None: ok = False; return mm.group(0)
            return r
        e2 = re.sub(r'(\w+)\[\d+:\d+\]', sb, expr)
        if ok:
            lines.append(ln.replace(expr, e2)); continue
        w = sum(int(a) - int(b) + 1 for a, b in re.findall(r'\[(\d+):(\d+)\]', expr))
        ob = f"native_required__{ni}__{port}"; newin[ob] = w
        rep["obligations"].append(dict(inst=ni, port=port, bits=w, from_=sorted({re.sub(r"__.*", "", n) for n in names})))
        lines.append(ln.replace(expr, f"{ob}[{w-1}:0]"))
    prm = f" #({ti['params']})" if ti["params"] else ""
    frag.append(f"  // HBM-BIND-5 S-role emission, q0 half {hub}.{q0}, template {t}\n  {ti['master']}{prm} {ni} (\n" + "\n".join(lines) + "\n  );")
    mp[ni] = [hub, q0]; rep["emit"].append(dict(inst=ni, template=t, hub=hub, q0=q0, master=ti["master"]))
# C1 providers
ROLES = {"NW": "NW", "NE": "NE", "SW": "SW", "SE": "SE"}
for r in ROLES:
    s = f"hb_idx__s_{r}"; q = f"hb_idx__qctl_{r}"
    assert s in insts and q in insts, r
    c = f"hb_idx__kb_{r}"
    pre = f"native_required__{s}__"
    frag.append(f"""  // HBM-BIND-5 C1: single-row calendar, ot_hnx_idxn_kb_ctl folded at key_row 0, pre 0 (d4g qctl): wires and constants only
  assign {pre}clear = {q}__frame_start[0:0];
  assign {pre}live_v = {q}__key_slot[0:0];
  assign {pre}live_index = {q}__key_index[7:0];
  assign {pre}pre_v = 1'b0;
  assign {pre}pre_index = 8'd0;
  assign {pre}replay_v = 1'b0;
  assign {pre}replay_index = {q}__key_index[7:0];""")
    for p in ("clear", "live_v", "live_index", "pre_v", "pre_index", "replay_v", "replay_index"): closed.append(pre + p)
    rep["kb"].append(c)
    h = "NW_hub" if r[1] == "W" else "NE_hub"
# candidate ties (COORD 07:3x: C4b, C4c, C5 yes, marked unproven until SS33-TOK): literal 0 at the sink connection, port removed
TIE = re.compile(r"^(su_S[EW]\d+__lg_[rw]q|vmdel_S[EW]\d+__dq|svg_S[EW]\d+__sm_packet)$")
ties = sorted(n for n, d in decl.items() if d[0] == "input" and TIE.match(n))
rep["candidate_ties"] = {n: decl[n][1] for n in ties}
src0 = src
def tie_sub(m):
    return f"{int(m.group(2)) - int(m.group(3)) + 1}'d0"
pat = re.compile(r"\b(" + "|".join(ties) + r")\[(\d+):(\d+)\]")
src = pat.sub(tie_sub, src)
for n in ties:
    src, k = re.subn(r'\n  input wire \[\d+:0\] ' + n + ';', '', src); assert k == 1, n
    src, k = re.subn(r'(?<=[(, ])' + n + r', ', '', src, count=1); assert k == 1, n
# C3 tnode pad straps from plan stations (pad_straps.py): literal at the node pin, one strap per instance
rep["pad_straps"] = pads
for node, v in pads.items():
    for port, w in (("pad_k", 6), ("pad_b", 1)):
        n = f"native_required__{node}__{port}"
        if n not in decl: rep.setdefault("pad_missing", []).append(n); continue
        src, k = re.subn(r"\b" + n + r"\[\d+:\d+\]", f"{w}'d{v[port]}", src); assert k >= 1, n
        src, k = re.subn(r'\n  input wire \[\d+:0\] ' + n + ';', '', src); assert k == 1, n
        src, k = re.subn(r'(?<=[(, ])' + n + r', ', '', src, count=1); assert k == 1, n
# demote closed inputs + new wires; closed nets of S clients
for n, w in new_outs.items():
    if n in decl and decl[n][0] == "input": closed.append(n)
    elif n in decl and decl[n][0] != "wire": raise SystemExit(f"output clash {n}")
    elif n not in decl: wires[n] = w
txt = src
for n in closed:
    a = re.compile(r'\n  input wire \[(\d+):0\] ' + n + ';')
    assert a.search(txt), n
    txt = a.sub(lambda m: f"\n  wire [{m.group(1)}:0] {n};", txt)
    txt, k = re.subn(r'(?<=[(, ])' + n + r', ', '', txt, count=1)
    assert k == 1, n
hdr = re.search(r'module hbm_current_native_top \(', txt).end()
txt = txt[:hdr] + "".join(n + ", " for n in sorted(newin)) + txt[hdr:]
decls = "".join(f"\n  input wire [{w-1}:0] {n};" for n, w in sorted(newin.items())) + "".join(f"\n  wire [{w-1}:0] {n};" for n, w in sorted(wires.items()))
k = txt.index(");", hdr) + 2
txt = txt[:k] + decls + txt[k:]
e = txt.rindex("endmodule")
txt = txt[:e] + "\n".join(frag) + "\n" + txt[e:]
open(out, "w").write(txt); json.dump(M, open(mo, "w"), indent=1)
rep["closed"] = closed; rep["new_inputs_bits"] = sum(newin.values()); rep["closed_bits"] = sum(decl[n][1] for n in closed)
json.dump(rep, open(rp, "w"), indent=1)
tb = collections.Counter()
for o in rep["obligations"]:
    for f in o["from_"]: tb[re.sub(r"_N[EW]\d*.*", "", f)] += o["bits"]
print("closed ports", len(closed), "bits", rep["closed_bits"], "| new obligations", len(newin), "bits", rep["new_inputs_bits"], tb.most_common(14))
print("skipped N with no q0:", len(rep["skipped"]), [s["inst"] for s in rep["skipped"]][:40])
