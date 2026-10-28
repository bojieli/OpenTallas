import json, sys
d, feed = sys.argv[1], sys.argv[2]
L = json.load(open(f"{d}/loc_v1/loc_{feed}.json"))
with open(f"{d}/local_{feed}_feed.tsv", "w") as f:
    f.write("child_region\tparent_region\tfeed_tap_xy_um\tw_mm\th_mm\tins_ps\n")
    G = {g["region"]: g for g in L["regions"]}
    for c, p in sorted(L["feed"]["parent"].items(), key=lambda kv: (kv[1] is not None, kv[0])):
        g = G.get(c, {})
        f.write(f"{c}\t{p or 'ROOT'}\t{L['feed']['tap'].get(f'{p}->{c}', '')}\t{g.get('w_mm')}\t{g.get('h_mm')}\t{g.get('ins_ps')}\n")
with open(f"{d}/local_{feed}_crossings.tsv", "w") as f:
    f.write("port\tsrc_region\tdst_region\tbits\tclass\ttree_hops\ttree_node_region\tunshared_src_ps\tunshared_dst_ps\tunshared_ps\tocv_tt_ps\tocv_ff_ps\tdepth\tL_lo_ps\tL_hi_ps\tmargin_lo_ps\tmargin_hi_ps\tlat_cycles\n")
    for r in sorted(L["rows"], key=lambda r: -r["unshared"]):
        cls = "tree-edge" if r["on_feed"] else ("short-loop" if r["unshared"] <= 2500 else "long-loop")
        f.write(f"{r['id']}\t{r['ra']}\t{r['rb']}\t{r['width']}\t{cls}\t{r['tree_hops']}\t{r['lca']}\t{r['ua']}\t{r['ub']}\t{r['unshared']}\t{r['p_tt']}\t{r['p_ff']}\t{r['depth'] or ('16' if r['d16_ok'] else 'FAIL')}\t{r['L_lo']}\t{r['L_hi']}\t{r['m_lo']}\t{r['m_hi']}\t{r['lat']}\n")
import collections
c = collections.Counter(); 
for r in L["rows"]:
    cls = "tree-edge" if r["on_feed"] else ("short-loop" if r["unshared"] <= 2500 else "long-loop")
    c[(cls, r["depth"] or 16)] += 1
print(sorted(c.items(), key=str))
