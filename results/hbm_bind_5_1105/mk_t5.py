s=open('gen_top_t3.py').read()
# su lg stays out of ties: S bank group 0 now driven by the pair
s=s.replace('TIE = re.compile(r"^(su_S[EW]\\d+__lg_[rw]q|vmdel_S[EW]\\d+__dq|svg_S[EW]\\d+__sm_packet)$")','TIE = re.compile(r"^(vmdel_S[EW]\\d+__dq|svg_S[EW]\\d+__sm_packet)$")\nPAIR = re.compile(r"^su_S[EW]\\d+__lg_[rw]q$")')
# C4q obligations: candidate ties
s=s.replace('''        ob = f"native_required__{ni}__{port}"; newin[ob] = w
''','''        ob = f"tie:{ni}.{port}"
''').replace('''        lines.append(ln.replace(expr, f"{ob}[{w-1}:0]"))''','''        lines.append(ln.replace(expr, f"{w}'d0"))''')
s=s.replace('''# demote closed inputs + new wires''','''# C2 option (a): pair cell per S bank, group 0
pair_ins = {}
for role, side in (("SW", "nw"), ("SE", "ne")):
    for k in range(8):
        v = f"vmb_{role}{k}"; c = f"hb_fvp_{role}{k}"
        ck = re.search(r"\\.clk\\(([^)]*)\\)", insts[v]["body"]).group(1)
        j = k // 2; rq = f"su_{role}{j}__lg_rq"; wq = f"su_{role}{j}__lg_wq"
        if k % 2 == 0:
            for n in (rq, wq):
                src, m = re.subn(r'\\n  input wire \\[\\d+:0\\] ' + n + ';', '', src); assert m == 1, n
                src, m = re.subn(r'(?<=[(, ])' + n + r', ', '', src, count=1); assert m == 1, n
        src, m = re.subn(rq + rf"\\[{17*(k%2)+16}:{17*(k%2)}\\]", f"{c}__rq0[16:0]", src); assert m == 1, (rq, k)
        src, m = re.subn(wq + rf"\\[{281*(k%2)+280}:{281*(k%2)}\\]", f"{c}__wq0[280:0]", src); assert m == 1, (wq, k)
        wires[f"{c}__rq0"] = 17; wires[f"{c}__wq0"] = 281; pair_ins[f"native_required__{c}__rst_n"] = 1
        conn = [f".clk({ck})", f".rst_n(native_required__{c}__rst_n[0:0])", f".rq0({c}__rq0[16:0])", f".wq0({c}__wq0[280:0])", f".rr0({v}__rr0[256:0])"]
        for t, L in (("a", 2 * k), ("b", 2 * k + 1)):
            for p, w in (("rq_v", 1), ("rq_s", 16), ("wq_v", 1), ("wq_s", 16), ("wq_d", 256)):
                n = f"fvp_in__{L}_{side}__{p}"; pair_ins[n] = w; conn.append(f".{t}_{p}({n}[{w-1}:0])")
            for p, w in (("rr_v", 1), ("rr_d", 256)):
                n = f"{c}__{t}_{p}"; wires[n] = w; conn.append(f".{t}_{p}({n}[{w-1}:0])")
        frag.append(f"  // HBM-BIND-5 C2 option (a): lanes {2*k},{2*k+1} of hub {side} on {v} group 0, candidate\\n  ot_hnx_fused_vm_pair {c} (\\n    " + ",\\n    ".join(conn) + "\\n  );")
        mp[c] = [("NW_hub" if side == "nw" else "NE_hub"), f"u_fvp_Q{k}"]
newin.update(pair_ins)
# demote closed inputs + new wires''',1)
open('gen_top_t5.py','w').write(s)
