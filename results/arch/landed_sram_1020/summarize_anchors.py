"""Summarize native diagnostic placed register pins; no EDA or qualification."""
import csv
import gzip
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

source = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
groups = defaultdict(dict)
clock_nets = defaultdict(set)
top_ports = {}
reset_pins = []
drivers = defaultdict(list)
retained = []
with gzip.open(source, "rt") as stream:
    for row in csv.DictReader(stream, delimiter="\t"):
        inst = row["instance"].replace("\\", "")
        if row["direction"] == "OUTPUT":
            drivers[row["net"]].append({k: row[k] for k in ("instance", "master", "pin", "x_um", "y_um")})
        if row["instance"] == "TOP":
            top_ports[row["net"]] = row["pin"]
        crossing = re.match(r"u_lpl_(\d+)_([wr])\.", inst)
        if not crossing:
            continue
        retained.append(row)
        key = crossing.group(1) + "_" + crossing.group(2)
        if row["pin"] == "CLK":
            clock_nets[row["net"]].add(key)
        if re.match(r"u_lpl_\d+_[wr]\.rq\$", inst) and row["pin"] == "D":
            reset_pins.append(dict(crossing=key, net=row["net"], instance=inst))
        match = re.match(r"u_lpl_(\d+)_([wr])\.(?:b\[(\d+)\]\[(\d+)\]|o\[(\d+)\])", inst)
        if match and row["direction"] == "OUTPUT" and row["pin"] == "QN":
            assert row["xy_valid"] == "1", row
            bit = int(match[4] or match[5])
            slot = int(match[3]) if match[3] is not None else 0
            groups[key][(slot, bit)] = dict(x=float(row["x_um"]), y=float(row["y_um"]), instance=row["instance"], pin=row["pin"])

summaries = []
for crossing in range(16):
    writer, reader = groups[str(crossing) + "_w"], groups[str(crossing) + "_r"]
    distances = []
    for (slot, bit), src in writer.items():
        dst = reader.get((0, bit))
        if dst:
            distances.append(dict(bit=bit, slot=slot, distance_um=abs(src["x"]-dst["x"])+abs(src["y"]-dst["y"]), writer=src, reader=dst))
    worst = max(distances, key=lambda x: x["distance_um"])
    summaries.append(dict(crossing=crossing, mapped_writer_data_ff=len(writer), mapped_reader_data_ff=len(reader),
                          matched_slot_bits=len(distances), worst_original_bank_qn_to_reader_qn=worst,
                          original_bank_qn_to_reader_qn_over405=sum(x["distance_um"] > 405 for x in distances)))

for row in reset_pins:
    row["direct_native_drivers"] = drivers[row["net"]]
    row["top_port"] = top_ports.get(row["net"])
doc = dict(scope="FAILED lg4 3_place native pin geometry diagnostic only; QN-to-QN anchor distance is not data-path timing/reach and is not a new SRAM placement", source_gzip_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
           crossings=summaries, clock_roots={k:dict(top_port=top_ports.get(k),crossings=sorted(v)) for k,v in clock_nets.items()}, reset_rq_inputs=reset_pins)
(out/"hbm_native_anchor_summary.json").write_text(json.dumps(doc, indent=2)+"\n")
with gzip.open(out/"hbm_lg4_register_pins.tsv.gz", "wt") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(retained[0]), delimiter="\t")
    writer.writeheader()
    writer.writerows(retained)
print("crossings", len(summaries), "retained_register_pin_records", len(retained), "clock_roots", len(clock_nets))
for row in summaries:
    print(row["crossing"], row["mapped_reader_data_ff"], row["worst_original_bank_qn_to_reader_qn"]["distance_um"])
