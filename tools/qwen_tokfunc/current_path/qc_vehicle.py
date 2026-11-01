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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bound', type=Path, required=True)
    ap.add_argument('--top', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--rom-top', default='tb_qcdie.u_qc')
    ap.add_argument('--start-bind', type=Path, help='count_align bind with the virtual START tree (functional provider)')
    a = ap.parse_args()
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
        elif n == 'ucie_kv_far_v':
            conn[n] = 'far_v'
        elif n == 'ucie_kv_far_flit':
            conn[n] = 'far_flit'
        else:
            refused.append(n)
    if refused:
        raise SystemExit(f'refuse: {len(refused)} undriven die inputs, e.g. {refused[:8]} (START provider missing?)')
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
    tb = f'''// GENERATED by tools/qwen_tokfunc/current_path/qc_vehicle.py (TOK-QK-2): whole bound QC die, bench drives pads only.
`timescale 1ns/1fs
module tb_qcdie;
    reg ck = 0; always #0.416500 ck = ~ck;           // core 1.2 GHz (as KV vehicle)
    reg rst_n = 0, start = 0;
    reg far_v = 0; reg [582:0] far_flit = '0;         // KV end idle (QC-only vehicle)
{chr(10).join(outs)}
{inst}
    integer cyc = 0, ncyc = 20000, rst_at = 64, start_after = 130, nlink = 0, first_link = -1, xlink = 0;
    initial begin
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 20000;
        if (!$value$plusargs("START_AFTER=%d", start_after)) start_after = 130;
        $display("QCDIE_CFG top {mod} ncyc %0d rst_at %0d start_after %0d", ncyc, rst_at, start_after);
    end
    always @(posedge ck) begin
        cyc <= cyc + 1;
        if (cyc == rst_at) begin rst_n <= 1; $display("QCDIE_RST_RELEASE cyc %0d", cyc); end
        if (cyc == rst_at + start_after) begin start <= 1; $display("QCDIE_START cyc %0d", cyc); end
        if ($isunknown(o_ucie_kv_link_v)) begin if (xlink == 0) $display("QCDIE_LINK_X first cyc %0d", cyc); xlink <= xlink + 1; end
        else if (o_ucie_kv_link_v[0]) begin
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
    json.dump(dict(schema='opentallas.tok_qk2.qc_vehicle.v1', top=str(a.top), module=mod, bound=str(a.bound),
                   ports=len(ports), clock_inputs=sum(1 for s in conn.values() if s == 'ck'), rom_tiles=len(rom), start_provider=sinfo,
                   scope='QC-only vehicle: reset/START/clock/ROM bring-up of the whole bound die; KV end idle. '
                         'Token verdict needs the QC+KV pair.'),
              open(a.out / 'vehicle.json', 'w'), indent=1)
    print('QC_VEHICLE', mod, len(ports), 'ports', len(rom), 'rom tiles')


if __name__ == '__main__':
    main()
