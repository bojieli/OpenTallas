P = "/srv/opentallas-scratch2/claude/die-s81-85/probe_vT3/rep/"
s = open(P + "relrep.tcl").read()
mv = open(P + "mv.tcl").read()
key = "estimate_parasitics -placement\nputs \"REL swapped"
assert key in s
s = s.replace(key, mv + key)
s = s.replace("relay_plain_repaired.odb", "relay_station_repaired.odb")
open(P + "relrep_station.tcl", "w").write(s)
open(P + "inner_station.sh", "w").write(open(P + "inner.sh").read().replace("relrep.tcl", "relrep_station.tcl"))
print("ok")
