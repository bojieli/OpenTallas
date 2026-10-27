#!/usr/bin/env python3
"""HEAD-RTL 2026-10-26 candidate plan delta: bind the real content providers of hd_lep0N and hd_mesh.
Writes a COPY; never mutates the canonical (frozen) plan.  Adoption is a COORD plan event.

  hd_lep0N: Codex head_lep_plan_delta.apply (u_core = ot_s81hd_lep0N_core + its +1 live fault return
            lep0N.fault_o0 -> ctl.lep_fault_i), sources from results/arch/head_lep_source_1026/sources.json.
  hd_mesh:  u_core = ot_s81hd_mesh_ep_core (the plan named the wrapper and the core both ot_s81hd_mesh_ep, which
            cannot elaborate), ck/rst_n bound to the wrapper clock/reset; buses unchanged (fault status in-band).
hd_ctl / hd_host are NOT touched: their providers do not exist (see lanes/HEAD-RTL.md ASK).
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_head')); sys.path.insert(0, str(ROOT / 'tools/die_plan'))
import head_lep_plan_delta as LEP
from gen import latency_table
from schema import Plan

T = 'rtl/dsrom_sys/s81_head/'
MESH_SOURCES = ['rtl/link/ot_link_crc32.sv', 'rtl/lib/ot_rst_relay_tree3.sv', 'rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv',
    'rtl/lib/ot_sram_oldread_b64.sv', 'rtl/lib/ot_sram_showahead_b64.sv', 'rtl/common/ot_link_credit_rx_b64.sv',
    'rtl/common/ot_link_credit_tx_rc.sv', 'rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe4.sv',
    'rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv', 'rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv',
    'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v',
    'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1/ot_sram_1r1w2c_256x64_m1.v',
    T + 'ot_s81hd_util.sv', T + 'ot_s81hd_lsc_parts.sv', T + 'ot_s81hd_beat_link.sv', T + 'ot_s81hd_best64.sv',
    T + 'ot_s81hd_mesh_ep_core.sv']


def apply(raw, lep_closure):
    raw = LEP.apply(raw, lep_closure)
    m = raw['partition_types']['hd_mesh']
    if [c['module'] for c in m['contents']] not in (['ot_s81hd_mesh_ep'], ['ot_s81hd_mesh_ep_core']):
        raise ValueError('hd_mesh contents changed; re-compose explicitly')
    m['contents'] = [dict(inst='u_core', module='ot_s81hd_mesh_ep_core', status='new', bind={'ck': 'clk', 'rst_n': 'rst_n'},
        note='2 x stacked MAIN head lane (dsfd_coll_lane_w_safe8_ntf + closed s81hd_lsc_t9/t8/r0m/r1m) + best64 TX decode '
             '+ copy-A/B slots -> 110-b words {ep_fault12, copy, BEST97} in 2 beats; ctl side ot_s81hd_mesh64_rx')]
    m['sources'] = MESH_SOURCES
    raw['latency'] = dict(lanes=latency_table(Plan(raw)))
    return raw


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base', type=Path, required=True); ap.add_argument('--lep-closure', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True); a = ap.parse_args()
    if a.base.resolve() == a.out.resolve(): raise SystemExit('refusing canonical in-place mutation')
    raw = apply(json.loads(a.base.read_text()), json.loads(a.lep_closure.read_text()))
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(raw, indent=2) + '\n')
    print('HEAD_RTL_DELTA candidate written (hd_lep0N + hd_mesh providers); no adoption')
