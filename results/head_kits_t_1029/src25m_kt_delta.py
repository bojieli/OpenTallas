# src25m_kt = die-head-33/src25m_cf (89fbd78f) + this kit-only clock tag on the 4 untagged edge-clock types
import json,sys
p=sys.argv[1]; a=json.load(open(p))
for k in ["hd_spn_wshim_rx","hd_spn_eshim_rx","hd_ctl_n","hd_ctl_e"]:
  c=a["partition_types"][k]["clock"]; c["landing_export_form"]="fwd_buffer"; c["tap_passthrough"]=True
open(p,"w").write(json.dumps(a,indent=1)+"\n")
