import pathlib,importlib.util,json,hashlib
R=pathlib.Path('/srv/opentallas-scratch2/claude/codex-hbm-su-opf4-1106');spec=importlib.util.spec_from_file_location('g',R/'su_operand_face_variant.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
anchor='assign u_bank0__read_v[3:0] = bank0_read_v[3:0];'
for name,op,ind,local in [('positive',2,0,True),('external',2,0,False),('operand',0,0,True),('index',2,2,True)]:
 out=R/('rtl_'+name);rec=g.generate(R/'rtl',out,op,ind)
 p=out/(g.NEW+'.sv');s=p.read_text();assert s.count(anchor)==1
 if local:
  terms='\n'.join(f"assign u_bank0__read_v[{i}] = u_lane0__rd_re[{i}] && (u_lane0__rd_src[{2*i} +: 2] == 2'd0);" for i in range(4));s=s.replace(anchor,terms);p.write_text(s)
 rec['local_operand_read_enable']=local;rec['external_drain_enable_retained']=True;rec['status']='FUNCTION_AND_PHYSICAL_QUALIFICATION_PENDING' if name=='positive' else 'MUTANT_DO_NOT_ROUTE';(out/'operand_variant.json').write_text(json.dumps(rec,indent=1)+'\n')
s=(R/'tb_opf4_lane1_phase.sv').read_text();s=s.replace('for(integer r=0;r<68;r=r+1)','for(integer r=0;r<69;r=r+1)').replace('if(r>=4)','if(r>=5)').replace('(r-4)*512','(r-5)*512');s=s.replace('localparam integer FIRST_OUTPUT=8+LATENCY+4*PINREG;','localparam integer FIRST_OUTPUT=8+LATENCY+4*PINREG+4;');s=s.replace('if(count==0)$display("PHASE op=%0d first_output=%0d",op,cycle);','if(count==0)begin $display("PHASE op=%0d first_output=%0d",op,cycle); if(cycle!=FIRST_OUTPUT)fail("selected profile first-output edge");end');(R/'tb_local_enable.sv').write_text(s)
job='''#!/usr/bin/env bash
set -euo pipefail
phase_root=/srv/opentallas-scratch2/claude/codex-hbm-su-opf4-1106
baseline_root=/srv/opentallas-scratch2/claude/hbm-bind-6/tip2
variant=$1
cd "$phase_root"
"$HOME/.local/opentallas-tools/bin/verilator" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_su_static_lane_leaf --Mdir "$phase_root/obj_local_$variant" "$phase_root/tb_local_enable.sv" "$phase_root/rtl_$variant"/*.sv "$baseline_root/physical/die_plan/hbm/over_cap_split/reform_1103/bench/lanes8_11/sram_bench_model.sv" > "$phase_root/build_local_$variant.log" 2>&1
set +e
"$phase_root/obj_local_$variant/Vtb_su_static_lane_leaf" +DIR="$phase_root/vec" > "$phase_root/local_$variant.log" 2>&1
rc=$?
set -e
cat "$phase_root/local_$variant.log"
if [ "$variant" != positive ]; then test "$rc" -ne 0; exit $?; fi
if [ "$rc" -ne 0 ]; then exit "$rc"; fi
set +e
"$phase_root/obj_local_$variant/Vtb_su_static_lane_leaf" +DIR="$phase_root/vec" +MUT_DATA > "$phase_root/local_field_mutant.log" 2>&1
rc=$?
set -e
test "$rc" -ne 0
''';(R/'run_local.sh').write_text(job);print('prepared localpositive+external/operand/index controls')
