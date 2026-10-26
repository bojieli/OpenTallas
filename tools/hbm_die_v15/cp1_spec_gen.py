import json, sys
Q = ['SW', 'SE', 'NW', 'NE']           # QID 0..3 (coll_idx_link v15_to_v16 map)
SRC = 'rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv'
SPT = 'rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv'
BUS = [('cfg_v', 1), ('cfg_target', 8), ('cfg_addr', 12), ('cfg_data', 256), ('desc_v', 1), ('desc_base', 12),
       ('desc_limit', 13), ('desc_loops', 16), ('launch_v', 1)]
BB = ('host F20 broadcast: ot_hbm_host_static_ingress.sv:18-23 outputs (same names/widths) -> collar pin flops; same '
      'pattern as coll_idx_link (COLL TARGET 52+QID)')
inst, edges, clocks, status = [], [], [], {}


def e(src, dst, bits, basis):
    edges.append(dict(src=src, dst=dst, bits=bits, clock='stream', basis=basis))


def bus(name):
    for p, w in BUS:
        e(['host_cp_ingress', p], [name, p], w, BB)
    clocks.append(dict(inst=name, port='clk', domain='stream', kind='clock'))


for qi, q in enumerate(Q):
    # ---- service-group programme/descriptor/run collars (G-HOST-LOADER-SVG)
    for k in range(8):
        t = 64 + 8 * qi + k; n = f'cp_svg_{q}{k}'; g = f'svg_{q}{k}'
        inst.append(dict(name=n, master='ot_static_cmd_target', source=SRC,
                         params=dict(TARGET=f"8'd{t}", MODE=0, AWA=10, AWB=7, RBW=7, RCW=8, NA=2, NF=1),
                         slot=f'svg_{q}{k}', owner='H-NETLIST/cp1 (host control plane)',
                         note=f'TARGET {t}: window A rows 0..1023 -> {g}.program_cfg (feed programme calendar SRAM), '
                              f'window B rows 0x400..0x47f -> {g}.desc (issuer 128x256 descriptor SRAM), desc F28/F2c '
                              f'[base,limit) x1 -> run_base/run_count at the global launch. Pin-registered; +2 edges.'))
        bus(n)
        bb = 'ot_static_cmd_target MODE 0 -> ot_hbm_svc_sm_group.sv:10-12 (issuer desc/run, feed programme)'
        for a, b, w in [('a_we', 'program_cfg_we', 1), ('a_addr', 'program_cfg_addr', 10), ('a_data', 'program_cfg_data', 256),
                        ('b_we', 'desc_we', 1), ('b_addr', 'desc_addr', 7), ('b_data', 'desc_data', 256),
                        ('run_v', 'run_v', 1), ('run_base', 'run_base', 7), ('run_count', 'run_count', 8)]:
            e([n, a], [g, b], w, bb)
        sb = 'status join inside the collar (pin-registered): active = running|program_active, fault |= group fault'
        e([g, 'running'], [n, 'tgt_active', 0, 1], 1, sb)
        e([g, 'program_active'], [n, 'tgt_active', 1, 2], 1, sb)
        e([g, 'fault'], [n, 'tgt_fault'], 1, sb)
        status[n] = dict(target=t, configured=[n, 'configured'], fault=[n, 'fault'], active=[n, 'active'])
    # ---- VM calendar programme targets (G-HOST-LOADER-CAL / G-SMVM-CALISS): reuse the port-exact collar
    t = 96 + qi; n = f'cp_cal_{q}'; g = f'calendar_{q}'
    inst.append(dict(name=n, master='ot_static_program_target', source=SPT, params=dict(TARGET=f"8'd{t}", PCW=10),
                     slot=f'calendar_{q}', owner='H-NETLIST/cp1 (host control plane)',
                     note=f'TARGET {t}: port-exact (program_cfg_we/addr10/data256, start_v/base10/limit11/loops16) to '
                          f'hfd_hgi_vm_calendar_{q}; existing master (no new tile).'))
    bus(n)
    cb = 'ot_static_program_target #(PCW 10) outputs == hfd_hgi_vm_calendar_static.sv:4-10 inputs'
    for a, b, w in [('program_cfg_we', 'cfg_we', 1), ('program_cfg_addr', 'cfg_addr', 10), ('program_cfg_data', 'cfg_data', 256),
                    ('program_start_v', 'start_v', 1), ('program_start_base', 'start_base', 10),
                    ('program_start_limit', 'start_limit', 11), ('program_start_loops', 'start_loops', 16)]:
        e([n, a], [g, b], w, cb)
    e([g, 'active'], [n, 'program_active'], 1, 'calendar active -> collar interlock (cfg/desc/launch while active = fault)')
    status[n] = dict(target=t, configured=[n, 'configured'], fault=[n, 'fault'], active=[g, 'active'],
                     target_fault=[g, 'fault'], done=[g, 'done'])
    # ---- static x-load command issuer (G-SMVM-XCMD)
    t = 100 + qi; n = f'cp_xl_{q}'; g = f'xl_{q}_ctl'
    inst.append(dict(name=n, master='ot_static_cmd_target', source=SRC,
                     params=dict(TARGET=f"8'd{t}", MODE=1, CW=108, RELF=0, NA=1, NF=1),
                     slot=f'xl_{q}', owner='H-NETLIST/cp1 (host control plane)',
                     note=f'TARGET {t}: command calendar (128 x {{x-load cmd 108, at 32}}, one 128x256 SRAM) fired at '
                          f'launch_base+loop*period+at; x_v pulse + fields, no x_rdy (the cl2 ctl has none). '
                          f'cmd = {{x_xb7,x_fmt2,x_space2,x_stride32,x_p4,x_n21,x_base40}}.'))
    bus(n)
    xb = 'ot_static_cmd_target MODE 1 cmd -> ot_hgi_sm_xload_static_cl2.sv:44-51 command pins (registered there)'
    e([n, 'cmd_v'], [g, 'x_v'], 1, xb)
    lo = 0
    for p, w in [('x_base', 40), ('x_n', 21), ('x_p', 4), ('x_stride', 32), ('x_space', 2), ('x_fmt', 2), ('x_xb', 7)]:
        e([n, 'cmd', lo, lo + w], [g, p], w, xb); lo += w
    assert lo == 108
    e([g, 'x_busy'], [n, 'tgt_active'], 1, 'x-load busy -> collar active (install interlock only)')
    e([g, 'x_fault'], [n, 'tgt_fault'], 1, 'x-load sticky fault -> collar fault')
    status[n] = dict(target=t, configured=[n, 'configured'], fault=[n, 'fault'], active=[n, 'active'], done=[g, 'x_done'])
    # ---- static DMA dispatcher (G-DMA command side)
    t = 104 + qi; n = f'cp_dma_{q}'; g = f'hb_dbk_{q}'
    inst.append(dict(name=n, master='ot_static_cmd_target', source=SRC,
                     params=dict(TARGET=f"8'd{t}", MODE=1, CW=308, RELF=2, NA=1, NF=1),
                     slot=f'dbk_{q}', owner='H-NETLIST/cp1 (host control plane)',
                     note=f'TARGET {t}: command calendar (128 x {{dn308, at 32}}, two 128x256 SRAMs) = the static '
                          f'dispatcher of dma_back_static_abi.json "producer" (dn309 = mv227,issue32,drain32,bank1,epoch16,v1); '
                          f'issue_at/drain_at are launch-relative in the table and leave rebased on the collar cycle '
                          f'counter, which also drives the DMA absolute cycle input (+1 per edge from reset).'))
    bus(n)
    db = 'ot_static_cmd_target MODE 1 cmd -> ot_hgi_dma_back_static_vp4_banks.sv:15-21 (dma_back_static_abi.json command)'
    e([n, 'cycle'], [g, 'cycle'], 32, db)
    e([n, 'cmd_v'], [g, 'mv_v'], 1, db)
    lo = 0
    for p, w in [('issue_at', 32), ('drain_at', 32), ('mv', 227), ('mv_wb_bank', 1), ('mv_wb_epoch', 16)]:
        e([n, 'cmd', lo, lo + w], [g, p], w, db); lo += w
    assert lo == 308
    e([g, 'busy'], [n, 'tgt_active'], 1, 'DMA busy -> collar active')
    e([g, 'mv_fault'], [n, 'tgt_fault'], 1, 'DMA sticky fault -> collar fault')
    status[n] = dict(target=t, configured=[n, 'configured'], fault=[n, 'fault'], active=[n, 'active'],
                     done=[g, 'mv_done'], quiet=[g, 'quiet'])

gaps = [dict(id='G-DMA-WB', owner='owner / H-DIE (HBM K-port ownership)',
             missing_rtl='DMA write-back partner (wb_ready, wa[12] into hb_dbk_<q>; consumer of wd[2312] + wb_reserve_*/'
                         'wb_fill_*): the real successor exists on main (ot_hbm_svc_wb_block_cdc / _pipeline_cdc: reserve/fill/'
                         'wd -> two-buffer WB SRAM -> CDC -> 32 HBM K write ports per stack, wa = posted sectors on true PHY '
                         'completion; composed with this DMA in ot_hgi_b2_swap_wb_grp_static.sv) but every HBM controller K '
                         'port of the v16 die is owned by an svg_<q><k> read feed (4 PCs each). Binding the WB needs an '
                         'architecture decision: (a) a static K-port time slot shared by svg read feed and WB write (fixed '
                         'calendar slot in the feed issuer), or (b) dedicated write PCs. wa/wb_ready are true off-die '
                         'completion signals and cannot be produced by a dispatcher.',
             affects=[[f'hb_dbk_{q}', p] for q in Q for p in ('wb_ready', 'wa')],
             note='cp1 closes the DMA command side (cycle/mv_v/mv/issue_at/drain_at/mv_wb_bank/mv_wb_epoch).')]

spec = dict(region='cp1', author='Claude H-NETLIST sub-agent cp1 (die control plane: programme/command targets)',
            basis_commit='4b43cd77c', instances=inst, retire_v15=[], edges=edges, drop_v15_edges=[], clocks=clocks,
            straps=[], gaps=gaps, die_pins=[],
            target_ids=dict(svg='64+8*QID+k', vm_calendar='96+QID', xload='100+QID', dma='104+QID',
                            qid=dict(zip(Q, range(4))),
                            ingress_TARGET_MASK_add='bits 64..107 (cp2 owns host_misc.json)'),
            status_outputs=status,
            notes=('ONE new master ot_static_cmd_target (MODE 0 run collar for 32 svg, MODE 1 command calendar for 4 x-load + '
                   '4 DMA) + the existing ot_static_program_target for the 4 VM calendars. All collars take the raw host F20 '
                   'broadcast; every input is pin-flopped and every output is a flop (owner 19:50). Fixed latencies: cfg row '
                   '-> target window write 2 edges after cfg_v at the collar pin; launch_v -> run_v 2 edges; MODE 1: a table '
                   'entry fires (cmd_v at the collar pin) when the exported cycle == C + 2 + LEAD(8) + loop*period + at, '
                   'C = cycle value in the launch_v pin cycle; x-load / DMA add their own command-pin edge on top (cl2 ctl '
                   'cmd_v pin flop; DMA DESC_LAT4). Table read is one entry per 3 edges sustained (2-deep prefetch: 2 '
                   'back-to-back after a gap); a command whose cycle passes before it reaches the head is a sticky FAULT, '
                   'never a late issue (static schedule, no ready/credit). Status: each collar exports configured/fault/'
                   'active (status_outputs); cp2 joins them into the ingress block_ready/program_active/program_fault. '
                   'Physical: the 256-b cfg_data broadcast now has ~48 more sinks (44 collars + COLL); it is install-time '
                   'only but single-cycle at 1.2 GHz, so the parent must give it a pipelined relay tree (fixed edges, the '
                   'collars are edge-count agnostic: install latency only). No target RTL changed (svg/calendar/xload/DMA '
                   'tiles untouched; no re-closure). Bench: rtl/hbm_accel/host_static_20261015/tb_static_cmd_target.sv.'))
json.dump(spec, open(sys.argv[1] if len(sys.argv) > 1 else 'tools/hbm_die_v15/v16_specs/cp1.json', 'w'), indent=1)
print(len(inst), 'instances', len(edges), 'edges')
