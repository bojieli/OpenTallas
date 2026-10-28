import json,sys,collections
for f in sys.argv[1:]:
    d=json.load(open(f)); s=d["summary"]; st=s["start_tree"]
    F=[e for e in d["start_edges"] if not e["clean_ok"]]
    cr=d["crossings"]; fails=[c for c in cr if c.get("margin_lo_ps",1e9)<104.1 or c.get("fail")]
    print(f, "start", st["start_edges"], "clean", st["start_clean"], "fail", st["start_fail"], "retime", st.get("retime_nodes"), "virt", st.get("virtual_nodes"),
      "width med/max", st["start_width_ps"], "xing", len(cr), "D", collections.Counter(c["depth"] for c in cr), "min lo", min(c["margin_lo_ps"] for c in cr))
    print("  fail types", collections.Counter((e["src"].split("_",2)[-1] if e["src"].startswith("sl_") else e["src"][:6])+"->"+(e["dst"].split("_",2)[-1] if e["dst"].startswith("sl_") else e["dst"][:6]) for e in F).most_common(12))
    for k in ("violations","worst_lo_to_guard_ps"):
        print("  ",k, s.get(k), s.get("mc",{}).get(k) if isinstance(s.get("mc"),dict) else "")
