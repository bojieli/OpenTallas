import json,sys,collections
for f in sys.argv[1:]:
    g=json.load(open(f+"/gates.json")); g=g.get("gates",g)
    print("==",f, {k:v.get("verdict") for k,v in g.items()})
    t=g["tree_commensurate"]
    print(" tree_comm", {k:v for k,v in t.items() if k not in ("rows","fail_examples","core_lattice")})
    rows=t.get("rows",[])
    if rows:
        c=collections.Counter((r["verdict"]) for r in rows); print(" rows",c)
        for r in [r for r in rows if r["verdict"]=="FAIL"][:60]:
            print("   ",r["region"],"cores",r["cores"],"types",r["types"],"tp",r["tree_points"],r["issues"], {a:[(x["module"][:28],x["n"],x["lines"]) for x in v["irregular_types"][:3]] for a,v in r["axes"].items()})
    b=g["bay_fill"]; print(" bay_fill", b.get("bay_fails"), b.get("max_fill"), b.get("partition_fill_fails"))
    print(" reach", {k:v for k,v in g["reach_gap"].items() if not isinstance(v,(list,dict))})
