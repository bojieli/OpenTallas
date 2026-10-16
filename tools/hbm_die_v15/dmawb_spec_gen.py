#!/usr/bin/env python3
"""H-NETLIST/dmawb 2026-10-16: v16 spec for G-DMA-WB / DMA_WRITEBACK_TO_HBM.

Per quadrant q: wbk_<q> = ot_hbm_svc_wb_kport (pin-registered WB partner of hb_dbk_<q>: real cut-through write-back
block + reservation receipts + WB window command) joined to
  * hb_dbk_<q> write-back outputs (wb_reserve_* / wb_fill_* / wd[2312]) and its wb_ready / wa[12] inputs;
  * the eight K-port window leaves vmks_<q><k> (ot_hbm_svc_vm_kshare, WB write windows: decision 23:21, DMA write-back
    shares the controller K ports, no dedicated PCs): window command broadcast + K write port of PC p = 4k+l on lane l.
Writes tools/hbm_die_v15/v16_specs/dmawb_0030.json.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Q = ('SW', 'SE', 'NW', 'NE')
QID = dict(SW=0, SE=1, NW=2, NE=3)
SRC = 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_wb_kport.sv'
KS = 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_vm_kshare.sv'
DMA_BASIS = ('rtl/hbm_accel/generic/peers/static/ot_hgi_b2_swap_wb_grp_static.sv (DMA <-> write-back composition, '
             'same port names) + rtl/hbm_accel/loader/service_native/ot_hbm_svc_wb_kport.sv header')
K_BASIS = ('rtl/hbm_accel/loader/service_native/ot_hbm_svc_wb_kport.sv: K write port p = PC p of the stack -> '
           'ot_hbm_svc_vm_kshare SM=p//4 lane p%4 (header: WB WRITE WINDOWS)')
W_BASIS = ('ot_hbm_svc_wb_kport window command {wbw_v, wbw_base, wbw_total} broadcast to the quadrant\'s eight '
           'ot_hbm_svc_vm_kshare leaves (per-lane exact counts computed in each kshare)')
KEXC = ('HBM stack / PHY controller boundary (HANDOFF 0az): K-port flow control of the write-back K write port '
        '(vmks is the PC-side K window leaf of that boundary)')


def main():
    inst, edges, clocks, straps = [], [], [], []
    for q in Q:
        w, d = f'wbk_{q}', f'hb_dbk_{q}'
        inst.append(dict(name=w, master='ot_hbm_svc_wb_kport', source=SRC, params=dict(WOPEN=0, MUT=0),
                         slot=d, owner='H-NETLIST/dmawb',
                         note='DMA write-back partner: pin regs + ot_hbm_svc_wb_cutthrough_cdc (32 x 128x256 SRAM, '
                              '32 CDC payload FIFOs, per-PC posted count on true k_wr_done) + reservation receipts '
                              '(wb_ready, wa) + WB window command to vmks_<q>0..7; 32 K write ports via pin skids'))
        clocks += [dict(inst=w, port='stream_clk', domain='stream', kind='clock'),
                   dict(inst=w, port='stream_fifo_clk', domain='stream', kind='clock'),
                   dict(inst=w, port='hbm_clk', domain='hbm', kind='clock'),
                   dict(inst=w, port='stream_rst_n', domain='stream', kind='reset'),
                   dict(inst=w, port='hbm_rst_n', domain='hbm', kind='reset')]
        straps.append(dict(inst=w, port='stk', lo=0, hi=2, value=QID[q],
                           reason='Registered physical stack identity (same value as hb_dbk_<q>.stk); no runtime selection.'))
        for p in ('wb_reserve_v', 'wb_reserve_bank', 'wb_fill_bank', 'wb_reserve_epoch', 'wb_fill_epoch',
                  'wb_reserve_sectors', 'wb_reserve_base', 'wb_fill_start', 'wd'):
            edges.append(dict(src=[d, p], dst=[w, p], clock='stream', basis=DMA_BASIS))
        for p in ('wb_ready', 'wa'):
            edges.append(dict(src=[w, p], dst=[d, p], clock='stream', basis=DMA_BASIS))
        for k in range(8):
            ks = f'vmks_{q}{k}'
            for p in ('wbw_v', 'wbw_base', 'wbw_total'):
                edges.append(dict(src=[w, p], dst=[ks, p], clock='stream', basis=W_BASIS))
            for p, b, out in (('w_k_v', 1, True), ('w_k_addr', 30, True), ('w_k_wdata', 256, True),
                              ('w_k_rdy', 1, False), ('w_k_wr_done', 1, False)):
                lo, hi = 4 * k * b, 4 * k * b + 4 * b
                e = (dict(src=[w, p, lo, hi], dst=[ks, p, 0, 4 * b]) if out else
                     dict(src=[ks, p, 0, 4 * b], dst=[w, p, lo, hi]))
                e.update(clock='hbm', basis=K_BASIS, ready_or_credit=p == 'w_k_rdy',
                         allowed_exception=KEXC if p == 'w_k_rdy' else None)
                edges.append(e)
    spec = dict(region='dmawb', author='H-NETLIST/dmawb 2026-10-16', basis_commit='origin/main d8c4aa677',
                instances=inst, retire_v15=[], edges=edges, drop_v15_edges=[], clocks=clocks, straps=straps, gaps=[],
                notes=dict(
                    closes='G-DMA-WB (wb_ready, wa into hb_dbk_<q>) and the DMA_WRITEBACK_TO_HBM output join '
                           '(wb_reserve_*/wb_fill_*/wd consumed by wbk_<q>)',
                    timing='static: DMA wb_reserve_v -> wb_ready valid +3 stream edges (sampled at the first drain, '
                           '>= 10 edges later); DMA fill start (drain_at+1) -> wbk window command +2 stream edges -> '
                           'kshare count +2 stream + CDC; wd -> WB SRAM +1 stream edge vs the unwrapped composition; '
                           'K write: WB block -> wbk pin skid +1 hbm -> kshare E skid +1 -> request skid +1 -> controller '
                           'KREG; k_wr_done -> kshare +1 -> wbk +1 hbm.  Variable waits only inside the HBM boundary.',
                    fault='wbk_<q>.fault (strap/receipt/WB block faults) has no consumer yet: ot_hbm_svc_stack_fault '
                          '(H-DIE) needs a wb_fault input; listed as a request, not wired as glue.',
                    bench='rtl/hbm_accel/loader/service_native/run_wb_kshare_bench.sh'))
    out = ROOT / 'tools/hbm_die_v15/v16_specs/dmawb_0030.json'
    out.write_text(json.dumps(spec, indent=1) + '\n')
    print(f'{out}: {len(inst)} instances, {len(edges)} edges')


if __name__ == '__main__':
    main()
