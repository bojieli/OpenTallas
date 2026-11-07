import json,sys
for f in sys.argv[1:]:
    d=json.load(open(f)); d["modules"].pop("ot_sram_1r1w_128x256_m1_r2c2",None); json.dump(d,open(f,"w"))
