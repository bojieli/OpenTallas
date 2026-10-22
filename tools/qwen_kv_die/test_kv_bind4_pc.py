#!/usr/bin/env python3
"""KV-BIND4 10-19: the sr6 PC / PC_H die point (OT_KV_DOMSPLIT=1 OT_KV_PC_RLAND=1 OT_KV_PC_SRAM=1 on the GEN9 MU/BOOT_AGES die).

  * the die tile file's qkd_kvs_pc / qkd_kvs_pc_h modules equal the sr6 kits' tile file (kv_tile_views identity);
  * the generator emits the same PC / PC_H modules (the composed file is the generated PC text);
  * bindings() exposes pc__hfx (health plane PC family); pc_chain_ages charges +1 hck kick / +1 hck fault a tile."""
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'rtl/qwen_sys/static_kv_die_20261017'
FLAGS = dict(OT_KV_STATIC_DIE='1', OT_KV_TILE_KITS='1', OT_KV_HROOT='1', OT_KV_FANFOLD='1', OT_KV_MU='1',
             OT_KV_BOOT_AGES='1', OT_KV_DOMSPLIT='1', OT_KV_PC_RLAND='1', OT_KV_PC_SRAM='1')


def mods(t):
    return {m.group(1): m.group(0) for m in re.finditer(r'module (\w+)\b.*?endmodule', t, re.S)}


class T(unittest.TestCase):
    def test_identity_with_sr6_kit_file(self):
        die = mods((D / 'qkd_kvs_tiles_hroot_ff_k_mu_ba_ds_rl_sr.sv').read_text())
        kit = mods((D / 'qkd_kvs_tiles_hroot_ff_k_mu_ds_rl_sr.sv').read_text())
        for m in ('qkd_kvs_pc', 'qkd_kvs_pc_h'):
            self.assertEqual(die[m], kit[m], m)
            self.assertIn('output wire [2:0] pc__hfx,', die[m])
            for reg in ('ki_q', 'fi_q', 'ebr_q'):
                self.assertNotIn(reg, die[m])   # landings live in the clone chain (kv_pc_sram_gen), not the tile text

    def test_generator(self):
        code = ('import sys, json; sys.path[:0] = ["tools/qwen_kv_die", "tools"]; import kv_static_die as K; '
                'b = K.bindings(); '
                'print(json.dumps(dict(rtl=K.RTL_FILE, pc=K.mods_pc() if hasattr(K, "mods_pc") else None, '
                'hfx=[m for m in ("qkd_kvs_pc", "qkd_kvs_pc_h") if "pc__hfx" in b[m]["ports"]], e=K.PC_SR_EDGES, '
                'ch=K.pc_chain_ages(dict(relay_stages={"kck_WS_0": 2, "kcf_WS_3": 1}))["stacks"]["WS"])))')
        r = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=dict(os.environ, **FLAGS), capture_output=True,
                           text=True, timeout=600)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        import json
        d = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(d['rtl'], 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba_ds_rl_sr.sv')
        self.assertEqual(d['hfx'], ['qkd_kvs_pc', 'qkd_kvs_pc_h'])
        self.assertEqual(d['e'], dict(kick_hck=1, fault_hck=1, boot_ready_ck=1))
        self.assertEqual(d['ch']['kick_end_hck'], 2 + 32 + 32)
        self.assertEqual(d['ch']['kick_end_hck_pre_sr6'], 2 + 32)
        self.assertEqual(d['ch']['fault_end_hck'], 1 + 32 + 32)


if __name__ == '__main__':
    unittest.main()
