import sys
t=open(sys.argv[1]).read()
a=t.index("// KV-PEER5"); b=t.index("module qkd_host_peer_root_mux_pl2")
hdr="""// DIE-KV-70 11-04 RE-FORM of qkd_host_peer_root_mux_pl2 (same ports, same per-channel word streams and faults).
// The shape and bad-header checks drive only fault, rq_oh / rq_v and the grant pointer; the 512-bit data registers load
// on the handshake alone (fault is sticky, so a word loaded on a fault edge is never presented).  physical_tx_data has no
// reset (physical_tx_valid qualifies it).  QKD_HR_PE_PL2_MUTANT (bench only): the physical RX slice corrupts bit 40.
"""
t=t[:a]+hdr+t[b:]
t=t.replace("module qkd_host_peer_root_mux_pl2","module qkd_host_peer_root_mux_r3")
s="if(!por_n)begin rr<=0;g<=0;physical_tx_valid<=0;physical_tx_data<=0;fault<=0;"
assert s in t; t=t.replace(s,"if(!por_n)begin rr<=0;g<=0;physical_tx_valid<=0;fault<=0;")
s="else begin physical_tx_valid<=1;physical_tx_data<=pick;rr<=rr_hit;end"
assert s in t; t=t.replace(s,"else begin physical_tx_valid<=1;rr<=rr_hit;end")
s="  if(rx_take&&shape)begin\n"
assert s in t; t=t.replace(s,"  if(hit!=0)physical_tx_data<=pick;\n  if(rx_take)begin\n")
open(sys.argv[2],"w").write(t)
