import json,sys
types=["hd_tile","hd_turn_a","hd_turn_b","hd_spn","hd_spn_end","hd_serdes","hd_st_turn","hd_st_str","hd_st_n3","hd_st_n4","hd_st_m","hd_st_k5","hd_mesh","hd_lep0N","hd_ctl","hd_host"]
tile={"TT":{"fwd_out_ps":[192.6,196.7],"fclk_in_ps":[189.4,212.7],"reader_ps":[501.4,539.8]},
      "FF":{"fwd_out_ps":[157.6,161.2],"fclk_in_ps":[155.9,176.9],"reader_ps":[401.5,435.6]}}
def form(f,c,r):  # TT values; FF = TT x 0.817 (tile FF/TT ratio, UNCHECKED for other types)
    tt={"fwd_out_ps":f,"fclk_in_ps":c,"reader_ps":r}
    return {"TT":tt,"FF":{k:[round(x*0.817,1) for x in v] for k,v in tt.items()}}
forms={"A_tileform":None,
       "B_writer_late":form([295,300],[290,310],[525,565]),
       "C_writer_early":form([40,45],[40,60],[525,565]),
       "D_center":form([165,170],[150,170],[525,565])}
for n,fm in forms.items():
    T={t:(tile if (t=="hd_tile" or fm is None) else fm) for t in types}
    json.dump({"schema":"ca_ring_latency/1","source":f"DIE-HEAD-19 WHAT-IF {n} (ESTIMATE, not measured): non-tile types = assumed form; hd_tile = DH18 measured","types":T,
               "fwd_wire_ps":{"TT":[0.0,1.0],"FF":[0.0,1.0]}},open(f"{sys.argv[1]}/ring_{n}.json","w"),indent=1)
