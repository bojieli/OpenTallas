import importlib.util,shlex
from pathlib import Path
b=Path('/srv/opentallas-scratch2/scratch/codex/hgi-quant-physical-7202d4ec4');p=b/'src/tools/run_abi3_physical.py';s=importlib.util.spec_from_file_location('physical',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
cfg=(b/'src/physical/qwen_die_masters/cfg/hgi_quant_pd50.env').read_text();sources=shlex.split(next(x for x in cfg.splitlines() if x.startswith('SRCS=')).split('=',1)[1])[0].split()
lines=m.orfs_config_lines('hgi_quant_config_audit',{'top':'ot_hgi_quant_decode','parameters':{},'sources':sources},'asap7',{'corner_env':'WC','extra_config':{'WC_NLDM_LIB_FILES':'$(TC_NLDM_LIB_FILES)','OT_HOLD_MM':'1','NUM_CORES':'12'}},20,.5,{'hold_corners':['WC','BC'],'hold_margin_ns':.01,'hold_margin_library_units':10},None,None)
assert 'export CORNERS = WC BC' in lines and 'export WC_LIB_FILES = $(WC_NLDM_LIB_FILES)' in lines and 'export BC_LIB_FILES = $(BC_NLDM_LIB_FILES)' in lines
(b/'gate/route_config_audit.mk').write_text('\n'.join(lines)+'\n')
print('\n'.join(x for x in lines if any(w in x for w in ('CORNER','LIB_FILES','HOLD_MM'))))
