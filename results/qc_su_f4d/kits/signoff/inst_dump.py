# QC-SU-F4D placement identity: sorted (name master x y orient) of every placed instance -> OUT
import os
from openroad import Design, Tech
t = Tech(); d = Design(t); d.readDb(os.environ["ODB"]); b = d.getBlock()
L = sorted("%s %s %d %d %s" % (i.getName(), i.getMaster().getName(), *i.getLocation(), i.getOrient()) for i in b.getInsts())
open(os.environ["OUT"], "w").write("\n".join(L) + "\n"); print("INST_DUMP", len(L))
