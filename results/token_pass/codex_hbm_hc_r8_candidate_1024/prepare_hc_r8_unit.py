from pathlib import Path
import re,shutil,json
src=Path('/home/ubuntu/OpenTallas');out=Path('/srv/opentallas-scratch/claude/codex-hbm/hc_r8_unit');out.mkdir(exist_ok=True)
text=(src/'rtl/test/run_hbm_hc_eng4_ring.sh').read_text();section=text.split('src=(',1)[1].split(')\n',1)[0];H='rtl/hbm_accel/generic/peers/static_hc'
files=[x.replace('$H',H) for x in section.split()]+['rtl/test/tb_hbm_hc_eng4_static_hier.vlt','tools/rtl_hbm_hc_eng_static_gate.py','tools/hbm_static/leaf_split_latency.py']
files += [str(p.relative_to(src)) for pat in ('tools/hdc*.py','tools/rtl_hdc*.py') for p in src.glob(pat)]
for f in files:
 p=out/f;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src/f,p)
tb=(src/'rtl/test/tb_hbm_hc_eng4_static.sv').read_text();tb=tb.replace('ot_hbm_hc_root_static #(.MUT(MUTP),','ot_hbm_hc_root_static #(.XRD(10),.XRU(10),.MUT(MUTP),',1)
down={'qd_v':4,'qd_ss':4,'qd_nv':28,'qd_wa':40,'qd_xa':40,'qi_v':4,'qi_kind':4,'qi_slot':8,'qi_lo':20,'qi_w':20,'qi_cnt':48,'qi_word':40};up={'qps_v':4,'qps':128,'qps_f':4,'q_fault':4}
# root receives delayed quarter returns; quarters receive delayed root commands.
root_start=tb.index('ot_hbm_hc_root_static #');root_end=tb.index(');',root_start)+2;body=tb[root_start:root_end]
for n in up:body=body.replace('.'+n+'('+n+')','.'+n+'(xru_'+n+')')
tb=tb[:root_start]+body+tb[root_end:];qstart=tb.index('ot_hbm_hc_qeng_static #');qend=tb.index(');',qstart)+2;body=tb[qstart:qend]
for n in down:body=re.sub(r'(?<![\w])'+n+r'\[', 'xrd_'+n+'[',body)
tb=tb[:qstart]+body+tb[qend:]
extra='\n'.join(f'wire [{w-1}:0] xrd_{n};' for n,w in down.items())+'\n'+'\n'.join(f'wire [{w-1}:0] xru_{n};' for n,w in up.items())+'\n'
for prefix,ports in [('xrd',down),('xru',up)]:
 names=list(ports);a='{'+','.join(names)+'}';b='{'+','.join(prefix+'_'+n for n in names)+'}';extra+=f'ot_codex_hc_r8_pad #(.W({sum(ports.values())}),.D(10)) {prefix}(clk,rst_n,{a},{b});\n'
tb=tb.replace('    wire busy = dut.u_seq.busy;',extra+'    wire busy = dut.u_seq.busy;')
tb+='''\nmodule ot_codex_hc_r8_pad #(parameter W=1,D=10)(input clk,rst_n,input [W-1:0]a,output [W-1:0]b);reg[W-1:0]q[0:D-1];integer i;always@(posedge clk)if(!rst_n)begin for(i=0;i<D;i=i+1)q[i]<=0;end else begin q[0]<=a;for(i=1;i<D;i=i+1)q[i]<=q[i-1];end assign b=q[D-1];endmodule\n'''
(out/'rtl/test/tb_hbm_hc_eng4_static.sv').write_text(tb)
text=text.replace('--raw0 $raw0 --rs 104','--raw0 $raw0 --rs 104 --ding 12').replace('rm -rf "$out/obj"','')
text=text.replace('exit $rc','''if [ "$rc" != 0 ]; then exit "$rc"; fi
python3 tools/rtl_hbm_hc_eng_static_gate.py --run "$out/case_bad_ding" --split --npos 1 --raw0 $raw0 --rs 104 --ding 2 > "$out/vectors_bad.log"
set +e
(cd "$out/case_bad_ding" && "$out/obj/Vring" $(cat plus.txt)) > "$out/run_bad_ding.log" 2>&1
neg=$?
set -e
[ "$neg" != 0 ] || { echo HC_R8_MUTANT_NOT_CAUGHT; exit 1; }
echo "HC_R8_EXACT PASS XRD10_XRU10 RAW0=$raw0 DING12 wrongDING2_CAUGHT_rc=$neg extra_unit_cycles=20"
''')
(out/'rtl/test/run_hbm_hc_eng4_ring.sh').write_text(text)
(out/'manifest.json').write_text(json.dumps(dict(basis='native root+fourquarter ring vs singleblock numeric golden',xrd=10,xru=10,baseline_raw0=178,corrected_raw0=198,corrected_ingest_lead=12,mutant_ingest_lead=2,added_unit_edges=20,source_files=files),indent=1)+'\n')
