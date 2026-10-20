import sys,gzip,re
from pathlib import Path
v=sys.argv[1];root=Path('/work/src');p=root/f'physical/ref_tile/s81sl_lepmu{v}_dr/kit.env';src=p.read_text().split("SRCS='")[1].split("'")[0].split();top=f'ot_s81sl_lep_mu_{v}';text=(root/'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv').read_text().split('module '+top+' #(',1)[1];ports=text.split(') (',1)[1].split(');',1)[0]
out=Path('/work')/f'native5_{v}';out.mkdir(exist_ok=True);wrapper=out/'top.sv';wrapper.write_text('module native_mu_top ('+ports+');\n'+top+' #(.RX_SRAM(1),.IN_PIPE(1),.NATIVE32(1)) u (.*);\nendmodule\n')
src += [str(p.relative_to(root)) for p in (root/'physical/asap7_memory_macros').rglob('*_bb.v')] + [str(p.relative_to(root)) for p in (root/'physical/asap7_memory_macros_v2').rglob('*_bb.v')]
pdk=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM');libs=[]
for name in ['AO','INVBUF','OA','SEQ','SIMPLE']:
 f=next(pdk.glob('asap7sc7p5t_'+name+'_RVT_TT_nldm_*'));p=out/(name+'.lib');p.write_bytes(gzip.open(f,'rb').read() if f.suffix=='.gz' else f.read_bytes());libs.append(str(p))
ys=['read_liberty -lib '+f for f in libs]+['read_verilog -sv '+str(root/f) for f in src]+['read_verilog -sv '+str(wrapper),'hierarchy -check -top native_mu_top','tcl /work/src/physical/common_flow/ot_keep_regs.tcl','synth -top native_mu_top -flatten -noshare','dfflibmap -liberty '+str(out/'SEQ.lib'),'abc '+' '.join('-liberty '+f for f in libs)+' -D 770','clean','stat','write_verilog -noattr '+str(out/'mapped.v'),'write_json '+str(out/'mapped.json')]
(out/'synth.ys').write_text('\n'.join(ys)+'\n')
