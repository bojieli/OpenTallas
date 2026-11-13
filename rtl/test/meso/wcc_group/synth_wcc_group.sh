#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/wt/hard-s81-dsdv-1
D=/srv/opentallas-scratch2/claude/hard-s81-dsdv-1/wcc_synth2
mkdir -p "$D"
cp "$R/rtl/common/ot_meso_fifo.sv" "$R/rtl/common/ot_dp_clk_landing.sv" "$D/"
git -C "$R" show 21bde8b3af:rtl/common/ot_meso_fifo.sv > "$D/ot_meso_fifo_before.sv"
cat > "$D/synth.py" <<'PY'
import glob,gzip,re,pathlib
p=pathlib.Path('/work')
libs=glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*')
text=''
for f in libs:
 s=gzip.open(f,'rt').read() if f.endswith('.gz') else open(f).read()
 if not text: text=s[:s.index('  cell (')]
 pos=s.index('  cell (')
 for m in re.finditer(r'  cell \(',s[pos:]):
  start=pos+m.start(); depth=0; begun=False
  for i in range(start,len(s)):
   if s[i]=='{': depth+=1;begun=True
   elif s[i]=='}':
    depth-=1
    if begun and depth==0:
     text+=s[start:i+1]+'\n';break
text+='}\n';(p/'all.lib').write_text(text)
for mode in ('before','group'):
 f='ot_meso_fifo_before.sv' if mode=='before' else 'ot_meso_fifo.sv'
 define='' if mode=='before' else '-DOT_MESO_WCC_GROUP=16'
 y=f'''read_liberty -lib /work/all.lib
read_verilog -sv -DSYNTHESIS {define} /work/{f} /work/ot_dp_clk_landing.sv
hierarchy -top ot_dp_clk_landing -chparam W 1105 -chparam WNEG 1 -chparam LOCAL 1 -chparam DSREP 8
synth -top ot_dp_clk_landing -noabc
dfflibmap -liberty /work/all.lib
abc -liberty /work/all.lib
clean
write_verilog -noattr /work/{mode}.v
'''
 (p/f'{mode}.ys').write_text(y)
PY
sudo docker run --rm -v "$D:/work" openroad/orfs:latest bash -lc 'python3 /work/synth.py; yosys -q -s /work/before.ys > /work/before.log 2>&1; yosys -q -s /work/group.ys > /work/group.log 2>&1'
for mode in before group; do
  python3 -I "$R/tools/die_plan/reg_fanout_gate.py" "$D/$mode.v" --top ot_dp_clk_landing --out "$D/$mode.fanout.json" > "$D/$mode.fanout.log" || true
  cat "$D/$mode.fanout.log"
done
echo WCC_SYNTH_DONE
