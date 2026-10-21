#!/usr/bin/env bash
set -euo pipefail
mkdir -p cxbits_fixed_map
cd cxbits_fixed_map
cp ../ot_link_afifo.sv .
cp ../cxbits_cdc_fixed/qkc_afifo_bits_1021.sv .
ln -sfn ../libs libs
L='';S='';for f in libs/*.lib;do L="$L read_liberty -lib $f;";S="$S -liberty $f";done
# Existing SYNTH_KEEP_MODULES effect for this unparameterized source module.
yosys -l mapped.log -p "$L read_verilog -sv -DSYNTHESIS ot_link_afifo.sv qkc_afifo_bits_1021.sv; hierarchy -check -top qkc_afifo_bits_1021; setattr -mod -set keep_hierarchy 1 qkc_afifo_w1a4s2_1021; synth -flatten -top qkc_afifo_bits_1021; dfflibmap -liberty libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty libs/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib -liberty libs/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib; hilomap -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L; opt_clean; tee -o area.json stat -json $S; write_json mapped.json; write_verilog -noattr mapped.v" > mapped.stdout.log 2>&1
python3 - <<'PY'
import json,collections,hashlib
p=json.load(open('mapped.json'))['modules'];t=p['qkc_afifo_bits_1021'];leaf=p['qkc_afifo_w1a4s2_1021'];inst=[n for n,c in t['cells'].items() if c['type']=='qkc_afifo_w1a4s2_1021'];ff=[n for n,c in leaf['cells'].items() if c['type'].startswith('DFF')]
assert len(inst)==64,(len(inst),'fixed leaf copies collapsed')
assert len(ff)>=60,(len(ff),'leaf state unexpectedly merged')
json.dump(dict(qualified=False,source_sha256=hashlib.sha256(open('qkc_afifo_bits_1021.sv','rb').read()).hexdigest(),retained_leaf_instances=len(inst),leaf_flops=len(ff),total_leaf_flops=len(inst)*len(ff),top_cells=len(t['cells']),leaf_cells=len(leaf['cells']),keep_spec={'route':{'synth_keep_modules':['qkc_afifo_w1a4s2_1021']}},remaining='whole native32/controller/reset source qualification'),open('retention.json','w'),indent=2)
PY
args=(python3 ../native_census.py --netlist mapped.v --top qkc_afifo_bits_1021 --out native.json);for f in libs/*.lib;do args+=(--liberty "$f");done
"${args[@]}" > native.log 2>&1
