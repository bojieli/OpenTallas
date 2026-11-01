#!/usr/bin/env python3
"""KV-KITS-21 (ASK-C, DIE-KV-27 plan event27, KV-007): qkd_ahub with seven co-timed clock entries, 0 added cycles.

ck[0] centre (u_rr, u_core except am, zh relays, zh_err_q, recip loop), ck[1]/ck[2] south/north zh pairs (unchanged from
Codex ck3), and four new face entries (event27.json rtl_delta; pin census of qkd_ahub_pins_r27.json):
  ck[3] S-W (150,50):  ap_q[94:0]  = ap0, ap1, ap2[8:0] pin flops;  u_core am[143:0] output pin registers (am0..am3)
  ck[4] S-E (450,50):  ap_q[171:95] = ap2[42:9], ap3 pin flops;     u_io whole (hs pin flops, start/epoch/T, hf fault)
  ck[5] E-S (580,110): u_rw_s = fr_epoch[15:0] + fr_rz[55:0] output relay flops (pins y < 220)
  ck[6] E-N (580,330): u_rw_n = fr_rz[127:56] + fr_valid output relay flops    (pins y >= 220)
Only clock pins change.  Every substitution is listed in SUBS and the reverse substitution must restore the original
module text byte-for-byte (collapse check below); the split always/instance forms are proven edge-exact by the tied-clock
bench (tb_qkd_ahub_static_dw with every entry = ck) and the per-entry stopped-clock mutants (CKMUT 1..5).

usage: clock_split7.py REPO OUT    (REPO = repo root; writes OUT/{qkd_ahub.sv, qkd_ahub_static_dw.sv, core.json})
"""
import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---- qkd_ahub_static_core_la -> _ck7: am output pin registers on their own clock (clk_am) ----
CORE_SUBS = [
    ("module qkd_ahub_static_core_la #(", "module qkd_ahub_static_core_la_ck7 #("),
    ("    input wire clk,rst_n,start,active_layer_parity,",
     "    input wire clk,rst_n,start,active_layer_parity,\n    input wire clk_am,   // KV-KITS-21 ck7: am pin registers (S-W entry)"),
    ("        if(!rn[1])begin ma_v<=0;mb_v<=0;mo_v<=0;for(integer a=0;a<4;a=a+1)am[36*a+35]<=0;end\n"
     "        else begin ma_v<=m_issue&&!start;mb_v<=ma_v&&!start;mo_v<=mb_v&&!start;\n"
     "            for(integer a=0;a<4;a=a+1)am[36*a+35]<=mo_v;end\n",
     "        if(!rn[1])begin ma_v<=0;mb_v<=0;mo_v<=0;end\n"
     "        else begin ma_v<=m_issue&&!start;mb_v<=ma_v&&!start;mo_v<=mb_v&&!start;end\n"
     "    always @(posedge clk_am or negedge rn[1])\n"
     "        if(!rn[1])begin for(integer a=0;a<4;a=a+1)am[36*a+35]<=0;end\n"
     "        else begin for(integer a=0;a<4;a=a+1)am[36*a+35]<=mo_v;end\n"),
    ("        mb_x<={m23[31:0],m01[31:0]};mb_a<={m23[32],m01[32]};mo_data<=mfin[31:0];\n"
     "        for(integer a=0;a<4;a=a+1)am[36*a+:35]<={1'b0,mo_h,mo_data};\n    end\n",
     "        mb_x<={m23[31:0],m01[31:0]};mb_a<={m23[32],m01[32]};mo_data<=mfin[31:0];\n    end\n"
     "    always @(posedge clk_am)begin\n"
     "        for(integer a=0;a<4;a=a+1)am[36*a+:35]<={1'b0,mo_h,mo_data};\n    end\n"),
]

# ---- qkd_ahub_static_dw -> _ck7 ----
DW_SUBS = [
    ("module qkd_ahub_static_dw #(", "module qkd_ahub_static_dw_ck7 #("),
    ("    input  wire          ck,\n    input  wire          rst_n,",
     "    input  wire          ck,\n    input  wire [1:0]    ck_zh,   // zh S pair / N pair (Codex ck3)\n"
     "    input  wire [3:0]    ck_ent,  // KV-KITS-21 event27 face entries: S-W, S-E, E-S, E-N\n"
     "    input  wire          rst_n,"),
    ("    always @(posedge ck) ap_q <= {ap3, ap2, ap1, ap0};",
     "    always @(posedge ck_ent[0]) ap_q[94:0] <= {ap2[8:0], ap1, ap0};\n"
     "    always @(posedge ck_ent[1]) ap_q[171:95] <= {ap3, ap2[42:9]};"),
    ("    ot_qkd_drly #(.W(145), .N((MUT == 6) ? 0 : WF_RLY)) u_rw (.clk(ck), .d({fr_rz_i, fr_epoch_i, fr_valid_i}),\n"
     "        .q({fr_rz, fr_epoch, fr_valid}));",
     "    ot_qkd_drly #(.W(72), .N((MUT == 6) ? 0 : WF_RLY)) u_rw_s (.clk(ck_ent[2]), .d({fr_rz_i[55:0], fr_epoch_i}),\n"
     "        .q({fr_rz[55:0], fr_epoch}));\n"
     "    ot_qkd_drly #(.W(73), .N((MUT == 6) ? 0 : WF_RLY)) u_rw_n (.clk(ck_ent[3]), .d({fr_rz_i[127:56], fr_valid_i}),\n"
     "        .q({fr_rz[127:56], fr_valid}));"),
    ("    qkd_ahub_static_io #(.AP_OFS(AP_OFS), .FR_OFS(FR_OFS), .WF_RLY(WF_RLY), .MUT(MUT)) u_io (\n        .ck(ck),",
     "    qkd_ahub_static_io #(.AP_OFS(AP_OFS), .FR_OFS(FR_OFS), .WF_RLY(WF_RLY), .MUT(MUT)) u_io (\n        .ck(ck_ent[1]),"),
    ("    qkd_ahub_static_core_la #(.Z_IN_STRIDE(Z_IN_STRIDE), .Z_LEVEL_GAP(10), .RS_RLY(RS_RLY), .MUT(MUT)) u_core (",
     "    qkd_ahub_static_core_la_ck7 #(.Z_IN_STRIDE(Z_IN_STRIDE), .Z_LEVEL_GAP(10), .RS_RLY(RS_RLY), .MUT(MUT)) u_core (\n"
     "        .clk_am(ck_ent[0]),"),
    ("ot_nhb_zh u_zh (.clk(ck),", "ot_nhb_zh u_zh (.clk(ck_zh[(a < 2) ? 0 : 1]),"),
]


def module(src, name):
    m = re.findall(r"^module %s\b.*?^endmodule\b" % name, src, re.M | re.S)
    if len(m) != 1:
        raise ValueError(f"exactly one module {name} required")
    return m[0]


def apply(orig, subs):
    out = orig
    for old, new in subs:
        if out.count(old) != 1:
            raise ValueError(f"substitution anchor not unique/absent: {old[:60]!r}")
        out = out.replace(old, new, 1)
    back = out
    for old, new in reversed(subs):
        if back.count(new) != 1:
            raise ValueError(f"reverse anchor not unique: {new[:60]!r}")
        back = back.replace(new, old, 1)
    if back != orig:
        raise ValueError("the transformation changed a non-clock token")
    return out


def wrapper(src):
    if src.count("input wire [0:0] ck,") != 1 or src.count(".ck(ck[0]),") != 1 or src.count("qkd_ahub_static_dw #(") != 1:
        raise ValueError("unexpected source wrapper clock declaration/connection")
    src = src.replace("input wire [0:0] ck,", "input wire [6:0] ck,", 1)
    src = src.replace("qkd_ahub_static_dw #(", "qkd_ahub_static_dw_ck7 #(", 1)
    return src.replace(".ck(ck[0]),", ".ck(ck[0]), .ck_zh(ck[2:1]), .ck_ent(ck[6:3]),", 1)


def age_next_register(src):
    """Opt-in parallel lookahead counter: remove increment/mux logic from the decoder path, no added edge.

    Its invariant is edge_age_q == the original e_next. Both counters use the
    same reset/start and saturation, including the existing MUT4 late control.
    Canonical RTL remains in the generated file as the independent reference.
    """
    old = "    wire [16:0] e_next=(MUT==4)?{1'b0,age}+17'd1:(active && age!=16'hffff)?{1'b0,age}+17'd2:{1'b0,age}+17'd1;"
    new = """    // AHUB lookahead recurrence: parallel state, same edge_age value on every cycle.
    (* keep *) reg [16:0] edge_age_q;
    always @(posedge clk or negedge rn[0])
        if (!rn[0]) edge_age_q <= 17'd1;
        else if (start) edge_age_q <= (MUT == 4) ? 17'd1 : 17'd2;
        else if (active && age != 16'hffff && ((MUT == 4) || age != 16'hfffe))
            edge_age_q <= edge_age_q + 17'd1;
    wire [16:0] e_next = edge_age_q;"""
    if src.count(old) != 1:
        raise ValueError('AHUB lookahead counter requires one exact canonical e_next expression')
    return src.replace(old, new, 1)



def nblk_zmask_register(src):
    """Separate wide Z-tree write-mask fanout from the calendar slot decoder, without an edge change."""
    old = """    reg [19:0] nblk_q;
    always @(posedge clk)
        for(integer s=0;s<4;s=s+1)
            nblk_q[5*s+:5]<=(T>14'(128*s))?5'(((T-14'(128*s)-14'd1)>>9)+14'd1):5'd0;
"""
    new = old.replace('reg [19:0] nblk_q;', '(* keep *) reg [19:0] nblk_q;')
    new += """    // Same D and same edge as nblk_q; isolate the physically wide Z write-mask consumers.
    (* keep *) reg [19:0] nblk_zmask_q;
    always @(posedge clk)
        for(integer s=0;s<4;s=s+1)
            nblk_zmask_q[5*s+:5]<=(T>14'(128*s))?5'(((T-14'(128*s)-14'd1)>>9)+14'd1):5'd0;
"""
    assert src.count(old) == 1, 'unexpected nblk register recipe'
    mask = 'if(k<nblk_q[5*s+:5])zmask[4*k+s]=1\'b1;'
    assert src.count(mask) == 1, 'unexpected zmask consumers'
    return src.replace(old, new, 1).replace(mask, mask.replace('nblk_q', 'nblk_zmask_q'), 1)


def prepare(core, out):
    """Restore the approved seven co-timed roles on a freshly extracted AHUB, preserving its current parameters."""
    import copy
    core = copy.deepcopy(core)
    if core.get('clock_split', {}).get('native_roles') == 7:
        return core
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    wrap = next(Path(f) for f in core['files'] if Path(f).name == 'qkd_ahub.sv')
    dw = next(Path(f) for f in core['files'] if Path(f).name == 'qkd_ahub_static_dw.sv')
    txt, original = wrap.read_text(), dw.read_text()
    assert txt.count('input wire [6:0] ck,') == 1, 'current planned AHUB must expose all seven entries'
    assert txt.count('qkd_ahub_static_dw #(') == 1 and txt.count('.ck(ck[0]),') == 1
    txt = txt.replace('qkd_ahub_static_dw #(', 'qkd_ahub_static_dw_ck7 #(', 1)
    txt = txt.replace('.ck(ck[0]),', '.ck(ck[0]), .ck_zh(ck[2:1]), .ck_ent(ck[6:3]),', 1)
    core7 = apply(module(original, 'qkd_ahub_static_core_la'), CORE_SUBS)
    if core.get('ahub_age_next_counter'):
        core7 = age_next_register(core7)
        core['physical_transforms'] = dict(core.get('physical_transforms', {}),
            age_next_counter=dict(extra_flops=17, cycles_added=0,
                invariant='edge_age_q equals canonical e_next; same reset/start/saturation/MUT4'))
    if core.get('ahub_nblk_zmask_split'):
        core7 = nblk_zmask_register(core7)
        core['physical_transforms'] = dict(core.get('physical_transforms', {}),
            nblk_zmask_split=dict(extra_flops=20, cycles_added=0,
                clock_role='ck[0]: identical u_core clk as nblk_q',
                input_source='same-cycle u_io T pin/held-word mux; check copy-D reach after GPL',
                output_consumers='zmask only; nblk_q retains both calendar decoders',
                invariant='both nblk registers sample the identical T expression on the identical edge'))
    dw7 = apply(module(original, 'qkd_ahub_static_dw'), DW_SUBS)
    new_wrap, new_dw = out / wrap.name, out / dw.name
    new_wrap.write_text(txt)
    new_dw.write_text(original + '\n// Existing KV-KITS-21 seven-role physical clock form, no added cycles.\n' + core7 + '\n\n' + dw7 + '\n')
    core['files'] = [str(new_wrap.resolve()) if Path(f) == wrap else str(new_dw.resolve()) if Path(f) == dw else f
                     for f in core['files']]
    for i in range(7):
        core['pin_class'][f'ck[{i}]'] = 'clk'
    core['classes']['clk'] = 7
    core['classes']['stale_in'] = sum(v == 'stale_in' for v in core['pin_class'].values())
    core['report']['stale'] = [v for v in core['report'].get('stale', []) if not v['pin'].startswith('ck[')]
    core['report']['clock_nets'] = {'clk': 'ck[6:0]'}
    core['boundary_role'] = {'ck': 'clk', 'rst_n': 'reset'}
    core['clock_split'] = dict(native_roles=7, cycles_added=0,
        source='Existing KV-KITS-21 clock_split7 CORE_SUBS/DW_SUBS; reverse restores current canonical RTL byte-exact')
    return core


def stage_anchors(kd, cfg, core=None):
    """Retain the existing actual-connectivity AHUB internal FF plan through DPL."""
    import shutil
    kd = Path(kd)
    src = HERE / 'ahub_internal_anchors.json'
    doc = json.loads(src.read_text())
    if (core or {}).get('ahub_nblk_zmask_split'):
        # N actual GPL placed these beside the ZH pins (>500um from T).
        # The reviewed local copy island keeps BOTH D and Q legs below405um.
        doc['anchors'] += [dict(name=f'u_leaf.u_core.nblk_zmask_q\\[{i}\\]$_DFF_P_',
                               xy_um=[280.8 + 2.16 * (i % 5), 22.14 + .54 * (i // 5)],
                               source='N actual T-source/D-reach locality, zero-cycle kept copy')
                           for i in range(20)]
        (kd / src.name).write_text(json.dumps(doc, indent=1) + '\n')
    else:
        shutil.copyfile(src, kd / src.name)
    lines = ['# Existing AHUB data-reach plan; legally release face registers and anchor internal stages before DPL.',
             'source /work/face_flops_release.tcl',
             'set b [ord::get_db_block]', 'set u [[ord::get_db_tech] getDbUnitsPerMicron]',
             'set rows {}', 'foreach r [$b getRows] {dict set rows [lindex [$r getOrigin] 1] [$r getOrient]}',
             # Standard face_flops_release lets DPL clear physical edge TAPCELLs.
             # Re-fixing those cells recreated161 actual overlap/padding failures.
             # Only the explicitly planned internal stages below remain FIRM.
             'set n 0']
    for a in doc['anchors']:
        x, y = a['xy_um']
        lines += ['set c [$b findInst {' + a['name'] + '}]',
                  'if {$c eq "NULL" || $c eq ""} {error "AHUB planned internal register not found"}',
                  '$c setPlacementStatus PLACED', f'set ay [expr {{round({y:.6f} * $u)}}]',
                  'if {![dict exists $rows $ay]} {error "AHUB anchor is not on a legal row"}',
                  '$c setOrient [dict get $rows $ay]',
                  f'$c setLocation [expr {{round({x:.6f} * $u)}}] $ay',
                  '$c setPlacementStatus FIRM', 'incr n']
    lines += ['puts "OT_AHUB_ANCHORS $n existing internal stages"']
    (kd / 'ahub_pre_dpl.tcl').write_text('\n'.join(lines) + '\n')
    before = 'export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl'
    assert cfg.count(before) == 1, 'AHUB native role recipe must retain the standard face-flop DPL hook'
    return [x if x != before else 'export PRE_DETAIL_PLACE_TCL = /work/ahub_pre_dpl.tcl' for x in cfg]


def stage_child_intrinsics(kd, tool):
    """Prototype optimizer inputs only; never a signed clock contract or pair-coverage proof."""
    import hashlib
    import sys
    sys.path.insert(0, str(tool))
    import cores as C
    import core_clock_contract as CC
    repo = HERE.parents[4]
    registry = json.loads((HERE / 'qkd_ahub_hard_children.json').read_text())
    rows = []
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    for block in registry['blocks']:
        master = block['master']
        view = repo / registry['children'][master]
        vals, hashes = {}, {}
        for corner in ('tt', 'ff'):
            lib = view / f'{master}_{corner}.lib'
            consumed = kd / 'macros' / lib.name
            if digest(lib) != digest(consumed):
                raise ValueError('AHUB child clock input differs from consumed library')
            hashes[corner] = digest(lib)
            if master == 'ot_nhb_zh':
                clocks = C.lib_clocks(lib)
                if set(clocks) != {'clk'} or clocks['clk']['rise'] <= 0:
                    raise ValueError('ZH exact rising clock-path upper bound missing')
                vals[corner] = dict(ps=clocks['clk']['rise'],
                    basis='ETM_MAX_CLOCK_TREE_PATH_UPPER_BOUND_NOT_MEAN', source=str(lib))
        if master == 'ot_qkh_recip_leaf':
            means = CC.load(dict(inst=block['inst'], lib=str(view / f'{master}_tt.lib')),
                            require_signed=False)
            if set(means) != {'clk'}:
                raise ValueError('RECIP exact clock mean mapping differs')
            for corner in ('tt', 'ff'):
                stat = means['clk']['corners'][corner]
                vals[corner] = dict(ps=stat['mean_ps'], basis=stat['basis'], source=stat['source'])
        elif master != 'ot_nhb_zh':
            raise ValueError('unapproved AHUB diagnostic intrinsic master')
        rows.append(dict(inst='u_leaf.' + block['inst'], master=master, pin='clk',
                         corners=vals, library_sha256=hashes, unit='ps', active_edge='rise'))
    (kd / 'ahub_child_clock_diagnostic.json').write_text(json.dumps(dict(
        schema='opentallas.ahub.child_clock_optimizer_diagnostic.v1', prototype_only=True,
        release_qualified=False, expanded_child_pair_coverage='NOT RUN', rows=rows,
        ruling='COORD 11-01 prototype: RECIP measured mean; ZH consumed-Lib upper bound explicitly not a mean'), indent=1) + '\n')
    lines = ['# Prototype clock optimizer inputs only; not SIGNED/mean/expanded-pair evidence.',
             'set cb [ord::get_db_block]']
    for corner in ('tt', 'ff'):
        lines += [f'set cf [open /work/ahub_child_latency_{corner}.txt w]',
                  'puts $cf {# prototype optimizer inputs; exact basis/corner/unit/hash in ahub_child_clock_diagnostic.json}']
        for row in rows:
            lines += ['set expected {' + row['inst'] + '}',
                      'set ci [$cb findInst $expected]',
                      r'set escaped [string map [list {[} {\[} {]} {\]}] $expected]',
                      'set ce [$cb findInst $escaped]',
                      'if {$ci ne "NULL" && $ce ne "NULL" && $ci ne $ce} {error "ambiguous AHUB child identity"}',
                      'if {$ci eq "NULL"} {set ci $ce}',
                      'if {$ci eq "NULL"} {error "AHUB declared child missing"}',
                      'if {[[$ci getMaster] getName] ne {' + row['master'] + '}} {error "AHUB child master differs"}',
                      'if {[$ci findITerm clk] eq "NULL"} {error "AHUB child clock pin missing"}',
                      'puts $cf [list [$ci getName] clk ' + str(row['corners'][corner]['ps']) + ']']
        lines += ['close $cf']
    (kd / 'ahub_child_intrinsics.tcl').write_text('\n'.join(lines) + '\n')


def stage_tap_balance(kd, cfg, tool, profile):
    """Stage the existing measured E/F entry-balance form for an explicit AHUB profile."""
    import shutil
    kd = Path(kd)
    target, window = float(profile['target_ps']), float(profile.get('window_ps', 40))
    if target <= 0 or window <= 0:
        raise ValueError('AHUB tap balance requires positive target/window')
    child_hook = ''
    if profile.get('child_intrinsics'):
        if profile['child_intrinsics'] != 'prototype':
            raise ValueError('AHUB child intrinsic compensation is prototype-only')
        stage_child_intrinsics(kd, tool)
        child_hook = 'source /work/ahub_child_intrinsics.tcl\n'
    shutil.copyfile(Path(tool) / 'tap_balance.tcl', kd / 'tap_balance.tcl')
    (kd / 'post_cts_tapbal.tcl').write_text(
        '# Existing DIE-KV-60 E/F entry balance, then the normal setup repair hook.\n'
        + child_hook + 'source /work/tap_balance.tcl\nsource /work/post_cts_setup.tcl\n')
    return cfg + [
        'override export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5 '
        '-sink_clustering_size 12 -sink_clustering_max_diameter 35 -distance_between_buffers 80',
        'override export POST_CTS_TCL = /work/post_cts_tapbal.tcl',
        r'export OT_TAP_PORT = ck\[[0-9]\]', 'export OT_TAP_CLOCK = clk',
        f'export OT_TAP_TARGET_PS = {target:g}', f'export OT_TAP_WINDOW_PS = {window:g}',
        *(['export OT_CORE_LAT = /work/ahub_child_latency_tt.txt'] if child_hook else [])]
