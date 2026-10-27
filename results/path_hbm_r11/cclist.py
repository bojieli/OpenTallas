import json,collections,re,sys
R=json.load(open(sys.argv[1]+"/r11_delta_report.json"))
out=open(sys.argv[2],"w"); out.write("hub\tconn\tlaunch\tcapture\tbits_parallel\twires\tlength_um\tk\n")
f=lambda s: re.sub(r"(_?\d+)?(__q\d)?$","",(s or "").split(".")[0])
for tn,h in R["hubs"].items():
  agg=collections.Counter(); n=collections.Counter()
  for l in h["cc_links"]:
    out.write("\t".join(str(x) for x in (tn,l["conn"],l["launch"],l["capture"],l["bits"],l["wires"],l["length_um"],l["k"]))+"\n")
    key=(f(l["launch"]),f(l["capture"])); agg[key]+=l["bits"]; n[key]+=1
  tot=sum(l["bits"] for l in h["cc_links"])
  print(tn,"links",len(h["cc_links"]),"bits",tot,"len max",max(l["length_um"] for l in h["cc_links"]),"k",h["k"],"we",h["we_chain"],"interseg_ser",h["stations"].get("serialised"),"inter_seg",h["stations"].get("inter_segment"),"lat_up",h["stations"].get("latency_up"),h["stations"].get("latency_up_hist"),"failed",h["stations"].get("failed"))
  for k,v in agg.most_common(8): print("  ",k,n[k],v)
