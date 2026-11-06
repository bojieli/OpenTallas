import json
a=json.load(open("asbuilt_t11.json"))
for s in ("col0","col1","col2","col3","ctl"):
    a["sub_core_leaf"]["u_hb_coll_Q_body_core__q0__"+s]="u_hb_coll_Q_body_core__q0"
a["sub_core_leaf_note"]=a.get("sub_core_leaf_note","")+" | HBM-BIND-10 t12: part 28 (main 943aae934ca) q3 body split col0..3 + ctl nested in as-built leaf u_hb_coll_Q_body_core__q0."
a["note"]="HBM-BIND-10 t12 = t11 + part 28 sub_core_leaf | "+a["note"]
json.dump(a,open("asbuilt_t12.json","w"),indent=1); print("ok")
