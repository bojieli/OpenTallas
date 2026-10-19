from pathlib import Path
import sys
kind=sys.argv[1]
if kind=='epoch':
 p=Path('ot_qwen_d2d_cal_sf_fe.sv');s=p.read_text();a='cfg_valid && (!epoch_valid || cfg_epoch == installed_epoch)';assert a in s;s=s.replace(a,'cfg_valid');p.write_text(s)
elif kind=='metadata':
 p=Path('qkd_d2d_firstepoch_component.sv');s=p.read_text();a='.bcfg_epoch(m1[16:1]),.bcfg_valid(m1[0])';assert a in s;s=s.replace(a,'.bcfg_epoch(m0[16:1]),.bcfg_valid(m0[0])');p.write_text(s)
elif kind=='status':
 p=Path('current_safe_fo.sv');s=p.read_text();start=s.index('module ot_qwen_d2d_status_rx_sf');pos=s.index('wire bad_hdr =',start);end=s.index(';',pos);s=s[:pos]+'wire bad_hdr = 1\'b0'+s[end:];p.write_text(s)
else: raise SystemExit('bad kind')
