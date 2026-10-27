"""CLOCK-KV-R12 plan delta (cuts): die-owned NS M7 ft band over the WN head-grid column (kv3_hgi_v6/v7/v8).
Root cause (also on the main KV plan): the WN hgi column is the N-S road for the die system buses (host.fdi 1044 b,
d2d_kv.rec_rx 552, host.rec_tx 549, kvs_emb 548, serdes_W 523 + local vport/slg legs at hgi_WN_0, up to 6473 b per
cut).  The cut model gives a partition only ft_track_frac 0.25 of M5/M7, and the head cores (M5 ceiling) block M5 over
864 of 1279 um, so a 1279-um column offers 7155 tracks and every hgi_WN cut reads 0.63-0.90.  The head cores never use
M7 (core route ceiling M5), so M7 over the column is the free road the master plan (12.7a roads) should declare: a
die-owned NS band on M7 over the full type width at die_share 0.5 (the other half stays with the partition for its
M7 PG/via access + local glue: ASSUMPTION, UNCHECKED until the hgi kit PG is read).  Needed share for 0.60: 0.432."""
import json, sys
src, dst = sys.argv[1:3]
P = json.load(open(src))
for tn in ("kv3_hgi_v6", "kv3_hgi_v7", "kv3_hgi_v8"):
    t = P["partition_types"][tn]
    w = t["outline_um"][0]
    t["die_ft_bands"] = [dict(dir="NS", span_um=[0.0, w], layers=["M7"], die_share=0.5,
                              note="CLOCK-KV-R12: WN column system-bus road over M5-ceiling head cores (cuts root cause)")]
P["note"] = "CLOCK-KV-R12 WN M7 ft band <- " + P.get("note", "")[:200]
json.dump(P, open(dst, "w"))
print("bands on kv3_hgi_v6/v7/v8")
