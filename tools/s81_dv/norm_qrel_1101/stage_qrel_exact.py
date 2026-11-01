from pathlib import Path
import re,shutil,hashlib,json
root=Path('/srv/opentallas-scratch2/claude/wt/codex-s81b-1101');out=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101/QREL_exact_v1');out.mkdir(exist_ok=False)
lut='8f7505bfab710037b5ad5c6521018b53';text=(root/'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv').read_text();(out/'ot_s81sl_xrt.sv').write_text(text);shutil.copyfile(root/'rtl/lib/ot_rst_relay.sv',out/'ot_rst_relay.sv')
small=(root/'rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rstd_release.sv').read_text().replace("128'h866f166f5f3b9a00888a3e0050029d55","128'h"+lut).replace('`timescale 1ns/1ps','`timescale 1ps/1fs').replace('always #0.5 clk','always #416.5 clk').replace('#0.01;','#1;').replace('cy<154','cy<199').replace('cy<152','cy<207')
# Explicit failing exit makes the causal mutant meaningful to automation.
small=small.replace('else $display("FAIL QREL");','else $fatal(1,"FAIL QREL");');(out/'tb_exact_release.sv').write_text(small)
parts=re.findall(r'^module (?:ot_s81sl_xrt(?:1|3)?)\b.*?^endmodule',text,re.M|re.S);assert len(parts)==3
ref='\n'.join(re.sub(r'\bot_s81sl_xrt(?:1|3)?\b',lambda m:'ref_'+m[0].removeprefix('ot_'),s)for s in parts);(out/'ref_xrt.sv').write_text(ref+'\n')
tb=(root/'rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_xrt_qrel_eq.sv').read_text();tb=tb.replace('`timescale 1ns/1ps','`timescale 1ps/1fs').replace('always #0.5 clk','always #416.5 clk').replace("128'h866f166f5f3b9a00888a3e0050029d55","128'h"+lut).replace('parameter integer QEN = 0','parameter integer QEN = 1')
tb=tb.replace('.FACE_LAND(LAND),.QDELAYS','.FACE_LAND(LAND),.PDSK(15\'d512),.QDELAYS').replace('.FACE_LAND(0)) rf','.FACE_LAND(0),.PDSK(15\'d512),.QDELAYS(128\'d0)) rf')
tb=tb.replace('sid = r32() % 16;','sid = HB ? 6 : 12;')
tb=tb.replace('nlo = 0, np = 0','nrstd = 0, nlo = 0, np = 0').replace('ncmp = ncmp + 1;','ncmp = ncmp + 1;nrstd=nrstd+od[OW-1544-W-513];')
tb=tb.replace('if (err == 0 && nxs > 100','if (err == 0 && nrstd>30 && nxs > 100').replace('else $display("FAIL");','else $fatal(1,"FAIL");')
tb=tb.replace('$finish;','$display("EXACT_QREL_RSTD_WORDS %0d",nrstd);$finish;');(out/'tb_exact_xrt.sv').write_text(tb)
(out/'source.json').write_text(json.dumps(dict(actual_current_XRT_file=str(root/'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv'),source_sha256=hashlib.sha256(text.encode()).hexdigest(),LUT_hex=lut,PDSK=512,FACE_LAND=1,clock_ps=833,reference='samecurrentXRT Q0 plusindependentexternalSIDpipeline; FACE1 representedbyreferenceinputflops',native_HB0_SID=12,native_HB1_SID=6,parameter_PREP_only=True),indent=1)+'\n');(out/'.keep').write_text('critical ROOTapprovedQRELparameter PREP exactgate\n')
