#!/usr/bin/env python3
"""S81 svc_lo_dsdv_svc_rs__t7 macro path fix (COORD 11-05 19:37 item (f), KW-RELAUNCH-1 row PLAN-PATH-MISMATCH):
t7 is the chain-end idx reader: its bound netlist instantiates u_u_irg_07 as dsdv_idx_rg3_nq, a 30-line wrapper
(bind/source_modules/portfix178/dsdv_idx_rg3_nq.sv) whose only child is u_rg3 = dsdv_idx_rg3_nq_native; the 13 SRAMs
(g_lm[0..1].u_mem, g_land[0..3].u_h0/u_h1, u_iq, u_mq, u_sq) sit inside u_rg3 with the same generate names as
dsdv_idx_rg3.  The plan contents rows were copied from the rg3 types (t1..t6, w__t1) and miss the u_rg3 level, so
KIT_PREFLIGHT refused all 13 ("component 'g_land[0]' is neither an instance nor a generate block of dsdv_idx_rg3_nq").
This delta inserts '.u_rg3' after u_bound.u_u_irg_07 in those 13 contents insts only (a text edit inside the t7
block, so the rest of the file keeps its layout): no site, outline, pin, clock, reset or define change.  The other svc_lo types bind dsdv_idx_rg3 (g_land directly) and are not touched.
usage: delta_svclo_path_1105.py PLAN_IN PLAN_OUT"""
import json, re, sys

TYPE, OLD, NEW = "svc_lo_dsdv_svc_rs__t7", "u_bound.u_u_irg_07.", "u_bound.u_u_irg_07.u_rg3."


def main():
    src, dst = sys.argv[1:3]
    p = json.load(open(src))
    t = p["partition_types"][TYPE]
    rows = [c for c in t.get("contents", []) if c["inst"].startswith(OLD)]
    assert len(rows) == 13 and not any(c["inst"].startswith(NEW) for c in rows), [c["inst"] for c in rows]
    assert not [h for h in t.get("hard_cores", []) if h["inst"].startswith(OLD)]
    done = []
    for c in rows:
        c["inst"] = NEW + c["inst"][len(OLD):]
        done.append(c["inst"])
    s = json.dumps(t)
    assert s.count("u_u_irg_07.") == len(done) == s.count("u_u_irg_07.u_rg3.")
    text = open(src).read()                 # text edit inside the t7 block only
    m = re.search('^  "' + re.escape(TYPE) + '": ', text, re.M)
    _, j = json.JSONDecoder().raw_decode(text, m.end())
    blk = text[m.end():j]
    assert blk.count('"' + OLD) == len(done), blk.count('"' + OLD)
    text = text[:m.end()] + blk.replace('"' + OLD, '"' + NEW) + text[j:]
    assert json.loads(text) == p
    open(dst, "w").write(text)
    print(json.dumps({"type": TYPE, "renamed": len(done), "insts": done}))


if __name__ == "__main__":
    main()
