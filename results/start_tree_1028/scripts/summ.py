import json,sys,statistics as S
for die in sys.argv[1:]:
    for m in ("base","clock"):
        try: d=json.load(open(f"{die}/{m}.json"))
        except Exception as e: print(die,m,"ERR",e); continue
        s=d["summary"]; xs=d["crossings"]
        w=sorted(o["L_width_ps"] for o in xs if o.get("L_width_ps") is not None)
        q=lambda f: round(w[min(len(w)-1,int(f*len(w)))]) if w else None
        st=s.get("start_tree",{})
        print(f"{die:5s} {m:5s} xings {s['crossings']} FAIL {s['fail']} D4 {s['depth4']} D8 {s['depth8']} <100 {s['below_100ps']} lo/hi {s['worst_margin_lo_ps']}/{s['worst_margin_hi_ps']} maxamb {s['max_path_ambiguous_cycles']} width p50/p90/p99/max {q(.5)}/{q(.9)}/{q(.99)}/{round(w[-1]) if w else None} startedges {s['tree_edges']} clean {s['tree_edges_clean']} depth {s['max_tree_depth']} mc {s.get('mc',{}).get('violations')} lat {s['lat_total_vs_old3']}",
              (f"| virt {st.get('virtual_nodes')} retime {st.get('retime_nodes')} sfail {st.get('start_fail')} swidth {st.get('start_width_ps')} mindist {st.get('start_min_sync_dist_ps')} hops {st.get('crossing_start_hops')}" if st else ""))
