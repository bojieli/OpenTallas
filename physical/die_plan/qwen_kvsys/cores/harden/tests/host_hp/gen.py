#!/usr/bin/env python3
"""Extract the actual header-selection mechanism; compare its frozen reference and seeded fault."""
from pathlib import Path
import sys
here=Path(__file__).resolve().parent
repo=here.parents[6]
source=repo/'rtl/qwen_sys/mu_qwen_20261018/hr_tx_predecode/qkd_host_ctrl_token_service_packet_collected_mu.sv'
text=source.read_text()
a=text.index(' if(HDR_PREDECODE)begin:g_hp');b=text.index(' end else begin:g_hr',a)
block=text[a:b]+' end\n'
ref=(here/'old.sv').read_text();prefix=ref[:ref.index(' if(HDR_PREDECODE)begin:g_hp')]
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
for name,body in [('hp_new',block),('hp_mut',block.replace('oh<={oh[2:0],oh[3]}','oh<={oh[0],oh[3:1]}'))]:
 (out/(name+'.sv')).write_text(prefix.replace('module hp_old','module '+name)+body+'endmodule\n')
