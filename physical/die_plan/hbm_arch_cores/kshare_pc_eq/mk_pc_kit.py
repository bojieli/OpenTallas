#!/usr/bin/env python3
# DIE-HBM-97/KSHARE-PC: finish a private PC kit (copied vR kit inputs): new RTL, face_shell.json in_extra_stages, notes
import json, shutil, sys, hashlib, datetime
from pathlib import Path
kit, rtl, view = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
IN = ['w_k_v', 'w_k_addr', 'w_k_wdata', 'c_kr_v', 'c_kr_tag', 'c_kr_beat', 'c_kr_data']
shutil.rmtree(kit / 'rtl'); shutil.copytree(rtl, kit / 'rtl')
fs = json.loads((kit / 'face_shell.json').read_text())
fs['in_extra_stages'] = {n: 1 for n in sorted(IN)}
fs['in_extra_stage_flops'] = sum(fs['keep'][n] for n in IN)
fs['face_flops_in_relay_note'] = 'u_bimid<j>_<bus> relay flops are free-placed (face flop u_bin_<bus> stays at the face)'
fs['pcf_core_param'] = dict(PCF=1, note='core: per-lane reset relay (+1 reset release), registered fill crossing (+1 on fill_*), kept one-hot lane-state flags (0 cycles)')
(kit / 'face_shell.json').write_text(json.dumps(fs, indent=1) + '\n')
now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
sha = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:12] for p in sorted((kit / 'rtl').glob('*.sv'))}
(kit / 'KSHARE97_FORM.txt').write_text(
 f'DIE-HBM-97/KSHARE-PC {now} kshare {view} vPC = vR (vK conservative settings + OT_KEEP_WIRES=reset_pipe) + PIN-CYCLE form (COORD YES): '
 'face-shell input relays u_bimid0_<bus> (+1 hbm edge) on w_k_v/w_k_addr/w_k_wdata/c_kr_v/c_kr_tag/c_kr_beat/c_kr_data; '
 'core PCF=1: per-lane kept reset relay lrst_q (+1 lane reset release), registered stream_clk fill crossing fa_v/fa_d (+1 on fill_v/bank/slot/epoch/data), '
 'kept one-hot lane-state flag copies q_issue/q_wb/q_norm (0 cycles). Plan event kshare_pc_1109 (compiler reschedule). '
 'Not an ECO; fresh from synth. DO_NOT_COUNT (private form).\nrtl sha256[:12]: ' + json.dumps(sha) + '\n')
(kit / 'DO_NOT_COUNT').write_text(f'DIE-HBM-97/KSHARE-PC private pin-cycle form {view} vPC, {now}: not counted until plan event kshare_pc_1109 is merged and COORD adopts.\n')
print(kit, fs['in_extra_stage_flops'])
