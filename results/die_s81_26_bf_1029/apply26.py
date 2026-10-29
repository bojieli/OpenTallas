# DIE-S81-26: master_slice.kit_apply (main tools) of the re-planned slice into a variant kit; --summary prints sinkcheck counts
import json, sys
if sys.argv[1] == "--summary":
    d = json.load(open(sys.argv[2]))
    print(d["actual_clk_pins"], d["planned"], "leaves", d["leaves"], "gates", d["gates"], "copies", d["copies"])
    sys.exit(0)
m, kv, sd = sys.argv[1:4]
sys.path.insert(0, m)
import master_slice as M
print(M.kit_apply(kv, "ot_v41_bf_col", [450.168, 198.72], slice_dir=sd, trial=True, clock_ports=["clk"]))
