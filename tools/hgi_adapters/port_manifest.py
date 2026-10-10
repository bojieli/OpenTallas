#!/usr/bin/env python3
"""hgi-adapters (2026-10-09): die-view port manifest of the HGI-1 record adapters (for hgi-takeover's die binding).
Ports are parsed from the RTL (tools/die_top_lint.parse_module, LEGACY = 0 = the routed adapters: the lg_* ports exist
but are unused; hgi_en is a static strap, tie 1 by_design).  Writes results/rtl/hgi_adapters_20261009/port_manifest.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_top_lint as L  # noqa: E402

A = 'rtl/hbm_accel/generic/adapters'
ADP = {
    'sm': dict(unit=1, top='ot_hgi_sm_record', site='beside hfd_cmdproc (drives the 32 SM control leaves: the legacy SM '
               'launch tree)', record=['rec_*: header, desc A / B / O, n_A / n_B'],
               peers={'sm_cmd / sm_ret': 'the 32 hfd_sm control_leaf + sm_desc buses (106 b / 4 b a SM): EXISTING SM ports',
                      'x_*': 'x-load to the VM / STREAM x multicast root (hfd_vm x staging): NO RTL PEER YET (gap)',
                      'pub_*': 'result publication into O (VM): NO RTL PEER YET (gap)'}),
    'su': dict(unit=2, top='ot_hgi_su_record', site='hfd_su (in front of the SU controller op port)',
               record=['rec_*: header, SUT, desc A B C D O R I, n_A'],
               peers={'op_v / op_rdy / op_w / su_idle / su_fault': 'ot_hdc_v41x_vec go / ready / i_* (PFIELDS word) / idle / '
                      'fault: EXISTING SU controller port (the hfd_su die view is a lane envelope without CTL12: gap owned by '
                      'the SU controller)'}),
    'sfu': dict(unit=3, top='ot_hgi_sfu_record', site='hfd_sfu', record=['rec_*: header, desc A B C O, n_A'],
                peers={'op_*': 'the SFU quarter vec op port (same ABI as SU)'}),
    'att': dict(unit=5, top='ot_hgi_att_issue', site='behind Codex ot_hgi_att_record_adapter (att_* port)',
                record=['att_*: from the G12 record adapter'],
                peers={'job_*': 'attention controller job port: NO RTL PEER on the HBM die (the tiles are packet pipes; the '
                       'ld / issue packet former = the RQ-HF-4 formatter + a q / p loader: gap, hbm-forks / ATT owner)'}),
    'argmax': dict(unit=7, top='ot_hgi_argmax_record', site='hfd_mtp slot (2nd instance with ot_hgi_argmax18_m)',
                   record=['rec[682:0]: the hgi_die_dispatch argmax bus (683 b) / ret {fault, done, ready}'],
                   peers={'e_*': 'ot_hgi_argmax18_m GENERIC18 = 1 (EXISTING, closed pinsep 30853dbe1)',
                          'vmq / vmr': 'one hfd_hgi_vm packet client (EXISTING ot_hgi_vm_unit)',
                          'am_stream': 'hb_su_red_mtp_am 523 b (mtp-lead r25gm)'}),
    'dma': dict(unit=8, top='ot_hgi_dma_record', site='beside hfd_loader / the svc', record=['rec_*: header, desc A / O, n, pos1'],
                peers={'mv_* / fence_*': 'DMA row mover (svc native read / write clients + VM packet client + format '
                       'converters): NO RTL PEER YET (gap)'}),
    'fused': dict(unit=4, top='ot_hgi_fused_record', site='FUSED front (unit 4): forwards QDQ to hfd_quant',
                  record=['rec_*: header, desc A B C O, n_A n_B n_O'],
                  peers={'mv_*': 'ot_hgi_dma_mover (gain staging)', 'op_*': 'a vec op port (the FUSED stream unit)',
                         'ne_*': 'DS norm engine / hc-post job (ot_hbm_accel_su_fused_stream KIND 0 / 4): binding is D1',
                         'q_rec': 'the quant record bus (hfd_quant, unchanged)'}),
    'hc': dict(unit=10, top='ot_hgi_hc_record', site='hfd_hc', record=['rec_*: header, desc A / B / O, n_A / n_O'],
               peers={'job_*': 'HC unit = ot_hdc_v41x_hcp cmd + ot_hdc_v41x_hcp_hbm_window + the mix post stage: '
                      'EXISTING engines, the HC unit wrapper binding them is the gap'}),
}


PEERS = {
    'dma_mover': ('ot_hgi_dma_mover', 'rtl/hbm_accel/generic/peers'),
    'sm_xload': ('ot_hgi_sm_xload', 'rtl/hbm_accel/generic/peers'),
    'sm_pub': ('ot_hgi_sm_pub', 'rtl/hbm_accel/generic/peers'),
    'ds_mux': ('ot_hgi_ds_mux', 'rtl/hbm_accel/generic/peers'),
    # D1 die bodies (adapter + local memory + the r25 engine + stage / drain through one VM packet client)
    'su_unit': ('ot_hgi_su_unit', 'rtl/hbm_accel/generic/peers'),       # GLU = 1: the SFU unit
    'hc_unit': ('ot_hgi_hc_unit', 'rtl/hbm_accel/generic/peers'),
}


def main():
    out = {}
    for k, (top, d) in PEERS.items():
        p = L.parse_module(str(ROOT / d / f"{top}.sv"), top, None)['ports']
        out[k] = dict(top=top, kind='peer', ports={n: dict(dir=dd, bits=w) for n, (dd, w) in p.items()},
                      in_bits=sum(w for dd, w in p.values() if dd == 'input'),
                      out_bits=sum(w for dd, w in p.values() if dd == 'output'))
    for k, a in ADP.items():
        if k in out:
            continue
        p = L.parse_module(str(ROOT / A / f"{a['top']}.sv"), a['top'], None)['ports']
        out[k] = dict(a, ports={n: dict(dir=d, bits=w) for n, (d, w) in p.items()},
                      in_bits=sum(w for d, w in p.values() if d == 'input'),
                      out_bits=sum(w for d, w in p.values() if d == 'output'))
    rec = dict(schema='opentallas.hgi_adapters.port_manifest.v1', source=A, adapters=out,
               notes=['Record side = the sequencer dispatch fields of ot_hgi_seq v1.0 (u_v / u_rdy, d_hdr, d_sut, d_desc '
                      'effective, d_n, d_pos1); return = rec_rdy / rec_done / rec_fault (pulses) exactly as the coll / '
                      'quant wrappers.',
                      'LEGACY = 0 for the die: lg_* unused (static tie by_design), hgi_en tie 1.'])
    o = ROOT / 'results/rtl/hgi_adapters_20261009/port_manifest.json'
    o.write_text(json.dumps(rec, indent=1) + '\n')
    for k, a in out.items():
        print(f"{k:7s} {a['top']:22s} in {a['in_bits']:5d} out {a['out_bits']:5d}")


if __name__ == '__main__':
    main()
