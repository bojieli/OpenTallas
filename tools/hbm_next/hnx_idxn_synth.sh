#!/bin/bash
# HBM-NEXT-UNITS-IDXN 2026-10-19: synthesis AREA ESTIMATE of the IDXN additions (pre-layout std-cell area, ASAP7 RVT TT,
# Yosys in the ORFS asap7lock image as tools/hbm_die_v15/synth_master.sh; SRAM macros are blackboxes counted by
# instance, their area from physical/asap7_memory_macros/<m>/<m>.json). Run from a bundle root:
#   tools/hbm_next/hnx_idxn_synth.sh OUT
# Tops: one d4g selector (the S - 1 added copies), the idxn issuer vs the d4g issuer, one key replay buffer (per scorer),
# the row-slot link vs the d4g link.
set -u
SRC=$(pwd); O=$(realpath -m "${1:?OUT}"); mkdir -p $O
X=rtl/hbm_accel/index; N=rtl/hbm_next/idxn; M=physical/asap7_memory_macros
BB="$M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_bb.v $M/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_bb.v"
declare -A F=(
 [sel]="$X/ot_hbm_idx_selector_static.sv"
 [cal_idxn]="$N/ot_hnx_idxn_calendar.sv"
 [cal_d4g]="$X/ot_hbm_idx_calendar_static.sv"
 [keybuf]="$N/ot_hnx_idxn_keybuf.sv"
 [link_idxn]="$N/ot_hnx_idxn_link.sv"
 [link_d4g]="$X/ot_hbm_idx_topk_link_static.sv")
declare -A T=([sel]=ot_hbm_idx_selector_static [cal_idxn]=ot_hnx_idxn_calendar [cal_d4g]=ot_hbm_idx_calendar_static
 [keybuf]=ot_hnx_idxn_keybuf [link_idxn]=ot_hnx_idxn_link [link_d4g]=ot_hbm_idx_topk_link_static)
for k in "${!T[@]}"; do
 { for b in $BB; do echo "read_verilog -lib $b"; done
   for f in ${F[$k]}; do echo "read_verilog -sv -DSYNTHESIS $f"; done
   echo "hierarchy -check -top ${T[$k]}"; echo "synth -top ${T[$k]} -flatten"
   echo "dfflibmap -liberty /tmp/lib/seq.lib"; echo "abc -liberty /tmp/lib/all.lib"; echo "opt_clean"
   echo "tee -o /out/$k.stat stat -liberty /tmp/lib/all.lib"; } > $O/$k.ys
done
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
for k in "${!T[@]}"; do
docker run --rm --name idxn-synth-$k-$$ --cpus=4 --memory=48g -v $SRC:/src:ro -v $O:/out -w /src openroad/orfs:asap7lock bash -lc "
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; mkdir -p /tmp/lib;
  zcat $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz > /tmp/lib/seq.lib 2>/dev/null || cp $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib /tmp/lib/seq.lib;
  for f in AO_RVT_TT_nldm_211120 INVBUF_RVT_TT_nldm_220122 OA_RVT_TT_nldm_211120 SIMPLE_RVT_TT_nldm_211120; do zcat $L/asap7sc7p5t_\$f.lib.gz; done > /tmp/lib/comb.lib;
  python3 - <<'PY2'
import re
txt = open('/tmp/lib/comb.lib').read() + open('/tmp/lib/seq.lib').read()
libs = re.split(r'(?m)^library\s*\(', txt)
head = 'library (' + libs[1].split('cell (', 1)[0]
cells = []
for l in libs[1:]:
    body = l.split('cell (', 1)[1] if 'cell (' in l else ''
    body = 'cell (' + body
    body = body[:body.rstrip().rfind('}')]
    cells.append(body)
open('/tmp/lib/all.lib', 'w').write(head + '\n'.join(cells) + '\n}\n')
PY2
  yosys -q -l /out/$k.log -s /out/$k.ys" > $O/$k.docker.log 2>&1 &
done
wait
python3 - $O $SRC <<'PY'
import json, re, sys
from pathlib import Path
O, S = Path(sys.argv[1]), Path(sys.argv[2])
mac = {m: json.loads((S / f'physical/asap7_memory_macros/{m}/{m}.json').read_text())['area']['macro_area_um2']
       for m in ('ot_sram_1r1w_256x256_m2_r2c2', 'ot_sram_1r1w_64x512_m1_r2c2')}
res = {}
for st in sorted(O.glob('*.stat')):
    t = st.read_text()
    a = re.search(r'^\s+\d+\s+([0-9.E+]+) cells', t, re.M)
    ff = sum(int(n) for n in re.findall(r'^\s+(\d+)\s+\S+\s+(?:DFF|SDF|DHL)\S*', t, re.M))
    mc = {m: sum(int(n) for n in re.findall(rf'^\s+(\d+)\s+-\s+{m}\b', t, re.M)) for m in mac}
    res[st.stem] = dict(cell_area_um2=float(a.group(1)) if a else None, flops=ff, macros={m: n for m, n in mc.items() if n},
                        macro_area_um2=round(sum(mac[m] * n for m, n in mc.items()), 1))
(O / 'area.json').write_text(json.dumps(dict(macro_area_um2=mac, units=res), indent=1) + '\n')
print(json.dumps(res))
PY
