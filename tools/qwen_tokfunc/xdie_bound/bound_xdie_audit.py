#!/usr/bin/env python3
"""TOK-QW xdie_bound static audit: do the BOUND tops on this checkout carry the CAL-AUTO regenerated D2D constants, and
are the two bound link ends / calendar images mutually consistent?  Reads the bound tops + partition modules + the
included calendar images, and a regenerated pair image (d2d_cal_image_production.sh with the regen recipe).
    bound_xdie_audit.py --regen REGEN/d2d_cal_image.svh --out audit.json
"""
import argparse, json, re
from pathlib import Path
QB = Path('physical/die_plan/qwen_compute/bind/bound_r8'); KB = Path('physical/die_plan/qwen_kvsys/bind/bound_pv')
IMG = Path('rtl/qwen_sys/d2d_static_20261015')

def lp(t):
    return {m.group(1): m.group(2).strip() for m in re.finditer(r'localparam\s+(?:\[[^\]]*\]\s*|integer\s+)?(\w+)\s*=\s*([^;]+);', t)}

def inst(text, name):
    m = re.search(r'^\s*(\w+)\s*(#\((.*?)\))?\s+' + name + r'\s*\(', text, re.M)
    return (m.group(1), m.group(3) or '') if m else (None, None)

def hx(v):
    m = re.search(r"'h([0-9a-fA-F]+)", v or ''); return int(m.group(1), 16) if m else None

ap = argparse.ArgumentParser(); ap.add_argument('--regen', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--closure', action='append', required=True, help='<die>_closure.json from stage_closure.py (the files the binder resolves)')
a = ap.parse_args()
K = json.loads((QB / 'regen/constants.json').read_text())['constants']
def kval(n):
    c = K[n]; return c.get('sv_literal') or c.get('value')
want_c, want_k = hx(str(kval('D2D_TXDP_C'))), hx(str(kval('D2D_TXDP_K')))
glue = (QB / 'rtl/qfd_qc_glue_part.sv').read_text()
sysc = (KB / 'rtl/kv3_sys_c_part.sv').read_text()
cm, cp = inst(glue, 'u_d2d_rom'); km, kp = inst(sysc, 'u_d2d_kv'); dm, dp = inst(sysc, 'u_dcal')
c_txdp = hx(re.search(r'\.TXDP\(([^)]*)\)', cp).group(1)) if '.TXDP(' in cp else 0
k_txdp = hx(re.search(r'\.TXDP\(([^)]*)\)', kp).group(1)) if '.TXDP(' in kp else 0
src = {p.name: p.read_text() for p in IMG.glob('*.sv')}
CL = [f.split('/', 2)[2] for c in a.closure for f in json.loads(Path(c).read_text())['files'] if '/bound/' not in f]
def includes_of(mod):
    hits = []
    for f in CL:
        m = re.search(r'module\s+' + mod + r'\b(.*?)endmodule', Path(f).read_text(), re.S)
        if m:
            hits.append((f, re.findall(r'`include\s+"([^"]+)"', m.group(1))))
    assert len(hits) == 1, (mod, hits)
    return hits[0][1], hits[0][0]
k_imgs, k_file = includes_of(dm)
c_imgs, c_file = includes_of('qfd_d2d_cal_seq_ovl_rope')
R = lp(Path(a.regen).read_text())
def cmp_img(f):
    I = lp((IMG / f).read_text())
    keys = ['D2D_TXDP_C', 'D2D_TXDP_K', 'OVL_TXDP_C', 'OVL_TXDP_K', 'D2D_TOKEN_PERIOD', 'D2D_CAL_START', 'D2D_CAL_K_TX_IMG',
            'D2D_CAL_K_RX_IMG', 'D2D_CAL_C_TX_IMG', 'D2D_CAL_C_RX_IMG', 'D2D_CAL_K_TX_SEG2', 'D2D_CAL_K_RX_SEG2']
    out = {}
    for k in keys:
        if k in I:
            rk = k.replace('OVL_', 'D2D_')
            out[k] = dict(image=I[k][:24], regen=(R.get(rk) or 'n/a')[:24], equal=I[k] == R.get(rk))
    return out
# STATUS codec pairing: compute master STATUS TX vs KV master STATUS RX
obs = src['ot_qwen_status_observers_v1.sv']
c_status_ext = "assign tx_payload={base_payload[547:512],held_obs,148'd0,base_payload[155:0]};" in obs
fo = src['ot_qwen_d2d_safe_fo.sv']
k_legacy_rx = "d[511:156] != 0" in fo
sfm = src['ot_qwen_d2d_sfm.sv']
k_rx_mod = re.search(r'module qkd_d2d_static_core_sfm .*?(ot_qwen_d2d_status_rx_\w+)', sfm, re.S).group(1)
obs1_rx_users = [n for n, t in src.items() if re.search(r'^\s*ot_qwen_d2d_status_rx_sfm3_obs1\b', t, re.M)]
F = []
F.append(dict(id='F1', ok=c_txdp == want_c, what='compute bound glue.u_d2d_rom TXDP', module=cm, params=cp, bound=f'{c_txdp:08x}',
              regen=f'{want_c:08x}', note='no #() override -> TXDP 0 with PR 1 = D2D_TXDP_NOT_COMPILED trap (elaboration fails); '
              'constants.json: ' + K['D2D_TXDP_C'].get('bind_applied', '')))
F.append(dict(id='K1', ok=k_txdp == want_k, what='KV bound sys_c.u_d2d_kv TXDP', module=km, params=kp, bound=f'{k_txdp:08x}', regen=f'{want_k:08x}'))
F.append(dict(id='K2', ok=(k_txdp & 0xff) == int(kval('D2D_KV_TX_LAT')), what='D2D_KV_TX_LAT == KV TXDP port0', bound=k_txdp & 0xff,
              regen=kval('D2D_KV_TX_LAT')))
F.append(dict(id='F6', ok=not (c_status_ext and k_legacy_rx), what='STATUS codec pairing',
              note=f'compute {cm} sends the kind15 v1 observer extension DATA[511:304] (={c_status_ext}); KV {km} core uses '
              f'{k_rx_mod} which faults unless d[511:156]==0 (={k_legacy_rx}); obs1-aware KV RX ot_qwen_d2d_status_rx_sfm3_obs1 '
              f'instantiated by: {obs1_rx_users or "nothing on main"}'))
F.append(dict(id='F7k', ok=all(v['equal'] for f in k_imgs for v in cmp_img(f).values() if not v['regen'] == 'n/a' and 'IMG' not in f),
              what=f'KV calendar sequencer {dm} compiled-in image', source=k_file, includes=k_imgs, compare={f: cmp_img(f) for f in k_imgs},
              note='boot target 11 reloads the K TX/RX tables (66 words); D2D_CAL_START / D2D_TOKEN_PERIOD / SEG constants stay compiled in'))
F.append(dict(id='F7c', ok=False, what='compute sys_face calendar producer qfd_d2d_cal_seq_ovl_rope images', source=c_file, includes=c_imgs,
              compare={f: cmp_img(f) for f in c_imgs if (IMG / f).exists()},
              note='OVL 4-user frame image (ovl_release_rope, ROM content via VIAMAP not in bound RTL) compiled for TXDP_K 0x16 (22)'))
k7 = F[-2]
k7['ok'] = all(v['equal'] for f in k_imgs for k, v in k7['compare'][f].items() if k in ('D2D_TOKEN_PERIOD', 'D2D_CAL_START', 'D2D_CAL_K_TX_SEG2', 'D2D_CAL_K_RX_SEG2', 'D2D_TXDP_K'))
c7 = F[-1]
c7['ok'] = all(v['equal'] for f in c7['compare'] for v in c7['compare'][f].values())
rep = dict(schema='opentallas.tok_qw.xdie_bound_audit.v1', regen_image=a.regen, regen_lp={k: R[k][:24] for k in ('D2D_TXDP_C', 'D2D_TXDP_K', 'D2D_TOKEN_PERIOD')},
           constants={n: kval(n) for n in ('D2D_TXDP_C', 'D2D_TXDP_K', 'D2D_KV_TX_LAT', 'XDIE_DIE_STAGES')}, checks=F)
Path(a.out).write_text(json.dumps(rep, indent=1) + '\n')
for f in F:
    print(f"{f['id']:4s} {'OK  ' if f['ok'] else 'FAIL'} {f['what']}" + (f" bound={f.get('bound')} regen={f.get('regen')}" if 'bound' in f else ''))
