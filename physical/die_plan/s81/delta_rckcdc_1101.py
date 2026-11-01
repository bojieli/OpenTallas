"""DIE-S81-46 (COORD 10-31 21:19 (1)): declare the serdes io_pma_rck pad clocks cdc synchronized with evidence.
Text edit of the plan (format kept): insert the two keys after "dir": "in" of every pad_clock io_pma_rck pin."""
import json, sys
p = sys.argv[1]
EV = ("ot_pdie_serdes.sv: pma_rck -> clk only through ot_s81_rate_match (8-deep gray-pointer FIFO, 2-flop gray "
      "pointer synchronisers both ways; KP4 SRAM 1r1w2c wclk=pma_rck rclk=clk is its storage), per-domain reset "
      "synchronisers (rs_r), 2-flop status synchronisers (lk_s/uf_s); 300 ppm two-die bench tb_pdie_ucie_col")
L = open(p).read().split("\n")
before = json.loads("\n".join(L))
n, out, i = 0, [], 0
while i < len(L):
    out.append(L[i])
    if L[i].strip() == '"name": "io_pma_rck",' and i + 2 < len(L) and L[i + 1].strip() == '"dir": "in",' \
            and L[i + 2].strip().startswith('"period_ps"'):
        ind = L[i + 1][:len(L[i + 1]) - len(L[i + 1].lstrip())]
        out.append(L[i + 1])
        out.append(f'{ind}"cdc": "synchronized",')
        out.append(f'{ind}"cdc_evidence": {json.dumps(EV)},')
        i += 2
        n += 1
        continue
    i += 1
CO = '{"name":"io_pma_rck","dir":"in","period_ps"'
for j, line in enumerate(out):
    if CO in line:
        assert line.count(CO) == 1, j
        out[j] = line.replace(CO, '{"name":"io_pma_rck","dir":"in","cdc":"synchronized","cdc_evidence":'
                              + json.dumps(EV) + ',"period_ps"')
        n += 1
after = json.loads("\n".join(out))
types = []
for tn, t in before["partition_types"].items():
    a = after["partition_types"][tn]
    if a != t:
        pins = a["clock"]["pad_clock"]["pins"]
        assert all(q.get("cdc") == "synchronized" for q in pins if q["name"] == "io_pma_rck")
        for q in pins:
            q.pop("cdc", None); q.pop("cdc_evidence", None)
        assert a == t, tn
        types.append(tn)
for k in before:
    if k != "partition_types":
        assert before[k] == after[k], k
open(p, "w").write("\n".join(out))
print(n, "pins", sorted(types))
