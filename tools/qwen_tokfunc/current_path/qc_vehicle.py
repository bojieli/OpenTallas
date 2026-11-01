#!/usr/bin/env python3
"""TOK-QK-2 11-01: whole-die QC (qwen_compute) vehicle top around the bound die top, nothing inside the die replaced.

    qc_vehicle.py --bound BIND_DIR --top TOP.sv --out OUT [--rom-top tb_qcdie.u_qc]

TOP.sv = BIND_DIR/rtl/qwen_compute_bound_top.sv, or its start_provider_bind successor (pst_* driven by the emitted
START stages; their t_st_*__clk stage clocks are die clock taps).  The bench drives only the die pads:
  clk_* / clock-tap inputs <- one core clock ck (the die clock run measures skew; functional sim is ideal-clock),
  rst_n, start             <- bench (start rises +START_AFTER core cycles after rst_n release),
  ucie_kv_far_{v,flit}     <- KV end: idle (0) in this QC-only vehicle; the QC+KV pair (carve_pair.py --whole-qc)
                              connects the real KV die instead.
  pst_*                    <- --start-bind: the plan's START tree (count_align bind with virtual st:<path> stages,
                              e.g. DIE-QC-57 r55a_P400/bind_A2.json) emitted FUNCTIONALLY by start_stage_emit's own
                              stage law (one ot_dp_landing_origin PAD/EDGE_FALL per stage, root ot_dp_landing_root
                              SETTLE) on the single bench clock; the physical emit (per-stage clock taps / placement)
                              changes no cycle in an ideal-clock sim.
Any other input is refused (no idle-zero environmental input is generated silently).
ROM: all 768 compute ROM tiles get their source-derived image ID (same law as carve_pair.py) via rom_bind.vh.
Observed: link_v count / first cycle / X on the link (QCDIE_SUMMARY), reset+START release, plusarg +NCYC.
"""
import argparse, json, re, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'tools/die_plan'))
import bind_smoke as SM


def top_ports(path):
    out, mod = {}, None
    for line in path.read_text().splitlines():
        if mod is None:
            m = re.match(r'^\s*module\s+(\w+)', line)
            if m:
                mod = m[1]
            continue
        m = re.match(r'^\s*(input|output)\s+wire\s*(?:\[(\d+):(\d+)\])?\s*(\w+)\s*[,;]?', line)
        if m:
            out[m[4]] = dict(direction=m[1], width=int(m[2]) - int(m[3]) + 1 if m[2] else 1)
        elif re.match(r'^\s*endmodule\b', line):
            break   # port declarations may follow internal wires (bound top lists the d2d link ports last)
    return mod, out


def rom_lines(bound_rtl, top, names, rom_top):
    _, insts = SM.parse_top(top)
    rom, ids = [], set()
    for i in insts:
        if not re.fullmatch(r'c_[EW][0-5]_[bt][fn]_[01][01]', i['name']):
            continue
        for r, c in SM.tiles_of(bound_rtl, i['module']):
            local = f"{i['name']}.u_u_t_{r}_{c}"
            m = re.fullmatch(r'c16_[EW][0-5]_([0-3])\.u_t_(\d)_(\d)', names.get(local, ''))
            if not m or (int(m[2]), int(m[3])) != (r, c):
                raise SystemExit(f'no exact source ROM identity for {local}')
            try:
                tid = SM.tile_identity(i, r, c)
            except ValueError:   # plan_qc52 binds carry the source tile strap as an instance PARAMETER (#(.S_..))
                m2 = re.findall(rf"\.(?:S|strap)_u_t_{r}_{c}_tile_id\((\d+)'([bdh])([0-9a-fA-F_]+)\)", i['text'][0])
                if len(m2) != 1 or m2[0][0] != '16':
                    raise SystemExit(f'{i["name"]}: tile {r},{c} source strap not found exactly once: {m2}')
                tid = int(m2[0][2].replace('_', ''), {'b': 2, 'd': 10, 'h': 16}[m2[0][1]])
            rid = (tid & ~15) + SM.SLOT[(r, c)]
            if rid in ids:
                raise SystemExit(f'duplicate ROM image {rid}')
            ids.add(rid)
            rom.append(f'defparam {rom_top}.{local}.ROM_TILE = {rid};')
    if ids != set(range(768)):
        raise SystemExit(f'expected 768 distinct ROM images, got {len(ids)}')
    return rom


def start_fn(bind, settle=None):
    """functional twin of start_stage_emit.emit's SV (same stages_of / start_ports / modules), one clock."""
    import start_stage_emit as E
    st = E.stages_of(bind)
    sp, reg = bind.get('start_ports') or {}, bind['regions']
    settle = int(settle or bind.get('root_settle_cycles', E.ROOT_SETTLE))
    ids = {x: 's%d' % k for k, x in enumerate(sorted(st, key=lambda q: (len(st[q]), st[q])))}
    into, outof = {}, {}
    for pid, c in sorted(sp.items()):
        if c['dst'] in into:
            raise SystemExit(f"start node {c['dst']} has two start ports")
        into[c['dst']] = pid
        outof.setdefault(c['src'], []).append(pid)
    roots = [x for x in st if reg[x].get('parent') is None]
    if len(roots) != 1:
        raise SystemExit(f'functional START: need exactly one virtual root, got {roots}')
    outs, ins = [], []
    for pid, c in sorted(sp.items()):
        a, b = c['src'] in st, c['dst'] in st
        if a and not b:
            outs.append((f"pst_{E.sv_name(c['dst'])}", ids[c['src']]))
        elif b and not a:
            ins.append(c['src'])
        elif not a and not b:
            raise SystemExit(f'functional START: direct region->region start port {pid} not supported')
    if ins:
        raise SystemExit(f'functional START: {len(ins)} start inputs from data regions (rs_*) not supported')
    sv = ['// GENERATED by qc_vehicle.py start_fn: functional twin of start_stage_emit (one clock, same stages/pads)',
          'module ot_die_start_stages_fn (input wire clk, input wire rst_raw_n,']
    sv.append(',\n'.join(f'    output wire {n}' for n, _ in outs) + ');')
    sv += [f'    wire st_{i}_start;' for i in ids.values()]
    for x, i in ids.items():
        r = reg[x]
        if r.get('parent') is None:
            sv.append(f'    wire st_{i}_start_d;')
            sv.append(f'    {E.ROOT_MODULE} #(.SETTLE({settle})) u_st_{i} (.clk(clk), .rst_raw_n(rst_raw_n), '
                      f'.start(st_{i}_start), .start_d(st_{i}_start_d));')
        else:
            sv.append(f"    {E.STAGE_MODULE} #(.PAD({int(r.get('pad', 0) or 0)}), .EDGE_FALL({int(bool(r.get('edge_fall')))})) "
                      f"u_st_{i} (.clk(clk), .rst_raw_n(rst_raw_n), .p_start(st_{ids[r['parent']]}_start), .start(st_{i}_start));")
    sv += [f'    assign {n} = st_{i}_start;' for n, i in outs]
    sv.append('endmodule')
    return '\n'.join(sv) + '\n', [n for n, _ in outs], dict(stages=len(ids), outputs=len(outs), settle=settle)


def pair_tb(kv, outs, inst, package_pads=False, code_roms=False):
    """The KV vehicle bench with the whole bound QC die as the compute end of the UCIe link (pads only, plus the two
    forwarded bumps the bound QC lacks as pads: driven from the KV die's bump pads + EPB package edges)."""
    # Match the cached KV children at 1ps precision while retaining every clock period.
    kv = kv.replace('`timescale 1ns/1fs', '`timescale 1ns/1ps')
    kv = kv.replace('always #0.416500 ck_core = ~ck_core;',
                    "always begin #0.416 ck_core=1'b1; #0.417 ck_core=1'b0; end")
    kv = kv.replace('always #0.521500 ck_phy  = ~ck_phy;',
                    "always begin #0.521 ck_phy=1'b1; #0.522 ck_phy=1'b0; end")
    sub = lambda t: (t.replace('(ck)', '(ck_core)').replace('.clk(ck)', '.clk(ck_core)').replace('(start)', '(qc_start)')
                     .replace('(far_v)', '(kv_link_v)').replace('(far_flit)', '(kv_link_flit)')
                     .replace('(fwd_ep)', '(qc_ep_pin)').replace('(fwd_lrst_n)', '(qc_lr_pin)'))
    m = re.search(r'\n(\s*)kvs_compute_end u_far \(.*?\);\n', kv, re.S)
    if not m or kv.count('kvs_compute_end u_far') != 1:
        raise SystemExit('refuse: KV tb has no single kvs_compute_end u_far instance')
    qc = '\n'.join([
        '    // TOK-QK-2 pair: the WHOLE bound QC die (qwen_compute_bound_top) is the compute end of the UCIe link.',
        '    wire qc_start = start_after_setup ? mission_start : rst_n;   // same START broadcast as the KV die',
        *[sub(o) for o in outs], sub(inst),
        '    assign c2k_v = o_ucie_kv_link_v; assign c2k_flit = o_ucie_kv_link_flit;',
        '    reg [31:0] qc_ep_sr = 0, qc_lr_sr = 0;',
        '    always @(posedge ck_core) begin',
        '        qc_ep_sr <= {qc_ep_sr[30:0], dut.u_bound.sys_c.d5_d2d_kv_fwd_epoch[0]};',
        '        qc_lr_sr <= {qc_lr_sr[30:0], dut.u_bound.sys_c.d5_d2d_kv_fwd_link_rst_n[0]};',
        '    end',
        '    wire qc_ep_pin = far_epb == 0 ? dut.u_bound.sys_c.d5_d2d_kv_fwd_epoch[0] : qc_ep_sr[far_epb - 1];',
        '    wire qc_lr_pin = far_epb == 0 ? dut.u_bound.sys_c.d5_d2d_kv_fwd_link_rst_n[0] : qc_lr_sr[far_epb - 1];',
        *([] if package_pads else ['    initial begin force u_qc.glue.u_bump_fwd_epoch.o = qc_ep_pin; force u_qc.glue.u_bump_fwd_lrst.o = qc_lr_pin; end']),
        '    integer qc_nlink = 0, qc_first = -1, qc_cyc = 0;',
        '    always @(posedge ck_core) begin',
        '        qc_cyc <= qc_cyc + 1;',
        '        if (o_ucie_kv_link_v === 1\'b1) begin if (qc_first < 0) begin qc_first <= qc_cyc; $display("PAIR_QC_LINK_FIRST cyc %0d", qc_cyc); end qc_nlink <= qc_nlink + 1; end',
        '        if (qc_cyc % 1000 == 0) $display("PAIR_QC_HB cyc %0d qc_link_v %0d", qc_cyc, qc_nlink);',
        '    end',
        '    // Native QC code-ROM binding is enabled only with --pair-code-roms. That runtime uses a merged',
        '    // KV+QC image directory: +OT_ROM_DIR is global, so the selected QC rank must accompany the KV ROMs.',
    ])
    kv = kv[:m.start()] + '\n' + qc + '\n' + kv[m.end():]
    kv = kv.replace('if (far_en) u_far.report();', '$display("PAIR_QC_SUMMARY qc_link_v %0d first %0d", qc_nlink, qc_first);')
    if 'u_far' in re.sub(r'//.*', '', kv):
        raise SystemExit('refuse: KV tb still references u_far')
    if code_roms:
        end = kv.rfind('endmodule')
        if end < 0:
            raise SystemExit('refuse: pair bench has no endmodule for ROM bindings')
        kv = kv[:end] + '\n`include "rom_bind.vh"\n' + kv[end:]
    return '// GENERATED by qc_vehicle.py --pair-kv-tb (TOK-QK-2): KV vehicle bench, far model -> whole bound QC die\n' + kv


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bound', type=Path, required=True)
    ap.add_argument('--top', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--rom-top', help='ROM binding hierarchy (default tb_qcdie.u_qc, or tb_kvslice.u_qc for a pair)')
    ap.add_argument('--start-bind', type=Path, help='count_align bind with the virtual START tree (functional provider)')
    ap.add_argument('--pair-kv-tb', type=Path, help='KV vehicle tb (tb_kvslice): emit tb_pair.sv with the whole bound QC '
                    'in place of the kvs_compute_end far model (rom paths then use --rom-top tb_kvslice.u_qc)')
    ap.add_argument('--pair-code-roms', action='store_true', help='Bind all 768 QC code tiles in the pair; runtime '
                    '+OT_ROM_DIR must contain both the selected QC rank masks and every KV ROM image')
    a = ap.parse_args()
    if a.pair_code_roms and not a.pair_kv_tb:
        ap.error('--pair-code-roms requires --pair-kv-tb')
    a.rom_top = a.rom_top or ('tb_kvslice.u_qc' if a.pair_kv_tb else 'tb_qcdie.u_qc')
    a.out.mkdir(parents=True, exist_ok=True)
    mod, ports = top_ports(a.top)
    conn, refused, pst, sinfo = {}, [], set(), None
    if a.start_bind:
        sv, pst_list, sinfo = start_fn(json.loads(a.start_bind.read_text()))
        (a.out / 'start_stages_fn.sv').write_text(sv)
        pst = set(pst_list)
    for n, p in ports.items():
        if p['direction'] == 'output':
            conn[n] = f'o_{n}'
        elif n in ('rst_n', 'start'):
            conn[n] = n
        elif n.startswith('clk_') or re.fullmatch(r't_st_\w+__clk', n):
            conn[n] = 'ck'
        elif n in pst:
            conn[n] = f'w_{n}'
        elif n == 'glue_bump_fwd_epoch_pad_i':
            conn[n] = 'fwd_ep'
        elif n == 'glue_bump_fwd_lrst_pad_i':
            conn[n] = 'fwd_lrst_n'
        elif n == 'ucie_kv_far_v':
            conn[n] = 'far_v'
        elif n == 'ucie_kv_far_flit':
            conn[n] = 'far_flit'
        else:
            refused.append(n)
    if refused:
        raise SystemExit(f'refuse: {len(refused)} undriven die inputs, e.g. {refused[:8]} (START provider missing?)')
    pad_names = {'glue_bump_fwd_epoch_pad_i', 'glue_bump_fwd_lrst_pad_i'}
    present_pads = pad_names & set(ports)
    if present_pads and present_pads != pad_names:
        raise SystemExit('refuse: forwarded epoch / link-reset package pad pair is incomplete')
    package_pads = present_pads == pad_names
    glue = (a.bound / 'rtl/qfd_qc_glue_part.sv').read_text()
    if not package_pads and (not re.search(r'\bqfd_qc_glue_part\s+glue\s*\(', a.top.read_text()) or \
            any(not re.search(rf'\bqfd_sigbump\s+{b}\s*\(', glue) for b in ('u_bump_fwd_epoch', 'u_bump_fwd_lrst'))):
        raise SystemExit('refuse: forwarded epoch / link-reset bumps not where the bench drives them (glue.u_bump_fwd_*)')
    names = json.loads((a.bound / 'bind_names.json').read_text())
    rom = rom_lines(a.bound / 'rtl', a.bound / 'rtl/qwen_compute_bound_top.sv', names, a.rom_top)
    (a.out / 'rom_bind.vh').write_text('// source-derived compute ROM image IDs (carve_pair.py law)\n' + '\n'.join(rom) + '\n')
    outs = [f"    wire {'[%d:0] ' % (p['width'] - 1) if p['width'] > 1 else ''}o_{n};" for n, p in ports.items()
            if p['direction'] == 'output']
    missing = sorted(pst - set(ports))
    if missing:
        raise SystemExit(f'START provider drives {len(missing)} nets the die top lacks, e.g. {missing[:5]}')
    if pst:
        outs.append('    wire ' + ', '.join(f'w_{n}' for n in sorted(pst)) + ';')
        outs.append('    ot_die_start_stages_fn u_start (.clk(ck), .rst_raw_n(rst_n), ' +
                    ', '.join(f'.{n}(w_{n})' for n in sorted(pst)) + ');')
    inst = f'    {mod} u_qc (\n' + ',\n'.join(f'        .{p}({s})' for p, s in conn.items()) + '\n    );'
    legacy_force = '' if package_pads else '''    initial begin
        force u_qc.glue.u_bump_fwd_lrst.o = fwd_lrst_n;
        force u_qc.glue.u_bump_fwd_epoch.o = fwd_ep;
    end'''
    tb = f'''// GENERATED by tools/qwen_tokfunc/current_path/qc_vehicle.py (TOK-QK-2): whole bound QC die, bench drives pads only.
`timescale 1ns/1ps
module tb_qcdie;
    reg ck = 0; always begin #0.416 ck = ~ck; #0.417 ck = ~ck; end // exact 833 ps, KV-cache precision
    reg rst_n = 0, start = 0;
    reg far_v = 0; reg [582:0] far_flit = '0;         // KV end idle (QC-only vehicle)
{chr(10).join(outs)}
{inst}
    // Drive the package epoch/reset pads when the bind exposes them. Historical binds use the explicit
    // package-boundary force emitted below; that override is absent for pad-enabled binds.
    reg fwd_lrst_n = 0, fwd_ep = 0;
{legacy_force}
    integer lrst_at = 300, epoch_at = 400;
    integer cyc = 0, ncyc = 20000, rst_at = 64, start_after = 130, nlink = 0, first_link = -1, xlink = 0;
    initial begin
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 20000;
        if (!$value$plusargs("START_AFTER=%d", start_after)) start_after = 130;
        if (!$value$plusargs("LRST_AT=%d", lrst_at)) lrst_at = 300;
        if (!$value$plusargs("EPOCH_AT=%d", epoch_at)) epoch_at = 400;
        $display("QCDIE_CFG top {mod} ncyc %0d rst_at %0d start_after %0d lrst_at %0d epoch_at %0d", ncyc, rst_at, start_after, lrst_at, epoch_at);
    end
    always @(posedge ck) begin
        cyc <= cyc + 1;
        if (cyc == rst_at) begin rst_n <= 1; $display("QCDIE_RST_RELEASE cyc %0d", cyc); end
        if (cyc == rst_at + start_after) begin start <= 1; $display("QCDIE_START cyc %0d", cyc); end
        if (cyc == lrst_at) begin fwd_lrst_n <= 1; $display("QCDIE_FWD_LRST_RELEASE cyc %0d", cyc); end
        if (cyc == epoch_at) begin fwd_ep <= 1; $display("QCDIE_FWD_EPOCH cyc %0d", cyc); end
        if ($isunknown(o_ucie_kv_link_v)) begin if (xlink == 0) $display("QCDIE_LINK_X first cyc %0d", cyc); xlink <= xlink + 1; end
        else if (o_ucie_kv_link_v) begin
            if (first_link < 0) begin first_link <= cyc; $display("QCDIE_LINK_FIRST cyc %0d flit %0h", cyc, o_ucie_kv_link_flit); end
            nlink <= nlink + 1;
        end
        if (cyc % 1000 == 0) $display("QCDIE_HB cyc %0d link_v %0d x %0d", cyc, nlink, xlink);
        if (cyc >= ncyc) begin
            $display("QCDIE_SUMMARY cyc %0d link_v_beats %0d first_link %0d link_x %0d", cyc, nlink, first_link, xlink);
            $finish;
        end
    end
`include "rom_bind.vh"
endmodule
'''
    (a.out / 'tb_qcdie.sv').write_text(tb)
    if a.pair_kv_tb:
        (a.out / 'tb_pair.sv').write_text(pair_tb(a.pair_kv_tb.read_text(), outs, inst, package_pads=package_pads, code_roms=a.pair_code_roms))
        print('QC_PAIR tb_pair.sv from', a.pair_kv_tb)
    json.dump(dict(schema='opentallas.tok_qk2.qc_vehicle.v1', top=str(a.top), module=mod, bound=str(a.bound),
                   ports=len(ports), forwarded_package_pads=package_pads, pair_code_roms=a.pair_code_roms, clock_inputs=sum(1 for s in conn.values() if s == 'ck'), rom_tiles=len(rom), start_provider=sinfo,
                   scope='QC-only vehicle: reset/START/clock/ROM bring-up of the whole bound die; KV end idle. '
                         'Token verdict needs the QC+KV pair.'),
              open(a.out / 'vehicle.json', 'w'), indent=1)
    print('QC_VEHICLE', mod, len(ports), 'ports', len(rom), 'rom tiles')


if __name__ == '__main__':
    main()
