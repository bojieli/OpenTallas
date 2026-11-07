#!/usr/bin/env python3
# DIE-HEAD-83 hd_ctl vF lockstep benches: old = vE kit RTL (modules renamed *_O), new = vF RTL.
import re, sys, pathlib
old, new, out = map(pathlib.Path, sys.argv[1:4])
out.mkdir(parents=True, exist_ok=True)
files = ['ot_dsrom_mtp_seq.sv','dsfd_mtp_tops.sv','ot_s81hd_ctl_hsf0_static.sv','ot_s81hd_static_issue.sv',
         'ot_s81hd_util.sv','ot_s81hd_best64.sv','ot_s81hd_lsc_parts.sv','ot_s81hd_beat_link.sv','ot_s81hd_mesh_ep_core.sv',
         'ot_link_crc32.sv','ot_link_credit_rx_b64.sv','ot_link_credit_tx_rc.sv','ot_dsrom_mtp_link_pair.sv','ot_rst_relay_tree3.sv']
files = [f for f in files if (new/f).exists()]
txt_old = ''.join((old/f).read_text()+'\n' for f in files)
names = sorted(set(re.findall(r'^\s*(?:\(\*[^)]*\*\)\s*)?module\s+(\w+)', txt_old, re.M)), key=len, reverse=True)
pat = re.compile(r'\b(' + '|'.join(map(re.escape, names)) + r')\b')
(out/'old.v').write_text(pat.sub(lambda m: m.group(1)+'_O', txt_old))
(out/'new.v').write_text(''.join((new/f).read_text()+'\n' for f in files))
(out/'files.txt').write_text('\n'.join(files)+'\n')
