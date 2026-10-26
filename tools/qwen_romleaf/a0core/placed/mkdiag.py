import sys
s = open(sys.argv[1]).read()
s = s.replace('    ap.add_argument("--moves",', '    ap.add_argument("--diag", default="")\n    ap.add_argument("--moves",', 1)
add = r'''    if a.diag:
        rx = re.compile(a.diag)
        net_of = {d: r for r, d in drv.items()}
        rows = collections.defaultdict(list)
        for d in res["bb"]:
            k, kind, owner, master, pin, dd = f_pins[d]
            on = owner.replace("\\", "")
            if kind == "comb" or not rx.search(on):
                continue
            p0 = pos(d)
            if p0 is None or net_of.get(d) is None:
                continue
            stack = [net_of[d]]; seen = set(stack)
            while stack:
                r = stack.pop()
                for s_ in sinks.get(r, ()):
                    kk, kd, ow, ms, pn, di = f_pins[s_]
                    if kd == "comb":
                        for o in cell_out[ow]:
                            if o not in seen:
                                seen.add(o); stack.append(o)
                    elif pn not in NG.CLK_PINS:
                        q = pos(s_)
                        if q:
                            dist = abs(q[0] - p0[0]) + abs(q[1] - p0[1])
                            en = re.sub(r"^u_ot_pr_core\.u_g\.u_tile\.u_tile\.u_logic\.", "", ow.replace("\\", ""))
                            en = re.sub(r"\$.*", "", re.sub(r"\[\d+\]", "[]", en))
                            rows[(HCLS(on), kd, en, pn if kd != "seq" else "")].append(
                                (round(dist, 1), round(p0[0], 1), round(p0[1], 1), round(q[0], 1), round(q[1], 1)))
        for key, v in sorted(rows.items(), key=lambda kv: -max(x[0] for x in kv[1])):
            v.sort(reverse=True)
            if v[0][0] < float(DIAGMIN):
                continue
            print("DIAG", key, "n", len(v), "over405", sum(1 for x in v if x[0] > 405), "worst", v[0])
'''
s = s.replace("    if a.dump_ends:", add + "    if a.dump_ends:", 1)
s = s.replace("TOP_Y = 653.04", "TOP_Y = 653.04\nimport os\nDIAGMIN = os.environ.get('DIAGMIN', '300')", 1)
open(sys.argv[2], "w").write(s)
