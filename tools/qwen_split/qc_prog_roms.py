#!/usr/bin/env python3
"""DIE-QC-59P 2026-11-01: QC (qwen_compute) programme ROM image set for a bound-die simulation (+OT_ROM_DIR).

The bound QC die (plan_qc52 / bindC) reads these non-code mask ROMs through the generic ROM model
(<+OT_ROM_DIR>/<INSTANCE>.viamap.hex, physical/asap7_memory_macros*/ot_rom_*.v):

  sys_face_cfg        glue u_sys_face (qfd_sys_face_lctx3_wrapped L_CONTEXTS 1) u_rom, ot_rom_4096x72_m8
                      generator tools/qwen_split/sys_face_image.py (build + viamap), program from
                      tools/qwen_layerbench/ctlm_image.py, events = tools/qwen_layerbench/layer_compile.py
                      sys_face_events() law on the PAIR link calendar (the one the KV die boots)
  ovl_c_tx/ovl_c_rx   (--ovl only) u_sys_face u_cseq (qfd_d2d_cal_seq_ovl_rope) list ROMs: with +OT_ROM_DIR set the model reads
                      them from OT_ROM_DIR, not from the ROM_DIR parameter, so the released lists are copied byte-exact
  calendar_m0/m1      TT u_gi.u_cal.g_calrom (qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_{1,2}), ot_rom_4096x266_m8
                      (copied from --calendar-dir when given; otherwise declared BLOCKED)
  table_s0_m0..m3     every DV slice qfd_dv_table_rom_loader (SLICE defaults to 0 on every bound slice),
                      generator tools/qwen_layerbench/programme_store.py; its input (the G-C4 per-slice PROG/BTAB/CROM
                      lowering manifest) has no producer on main -> declared-empty images (all words invalid: the
                      loader writes nothing and raises no fault), status BLOCKED

Nothing here qualifies a programme.  Every image carries its status in manifest.json:
  COMPILED_NOT_QUALIFIED  real compiler output on the recorded inputs, with the listed gaps
  RELEASED_COPY           byte copy of a committed release image
  BLOCKED_EMPTY           an explicit all-zero image standing in for an image no tool on main can produce
qc_prog_rom_guard.sv (also written) is a sim-only module: instantiate it in the bench; with +OT_ROM_DIR it $fatal()s
on any missing image (the ROM model itself only warns and reads zero), and it prints the manifest digest.

usage: qc_prog_roms.py --pair-calendar CAL.json --d2d-image d2d_cal_image.svh --out DIR
                       [--ctlm-dir DIR] [--calendar-dir DIR] [--n59-land-edges 8] [--ovl-dir DIR]
"""
import argparse, hashlib, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/qwen_split'), str(ROOT / 'tools/qwen_layerbench')]
import sys_face_image as SFI  # noqa: E402

OVL_DIR = 'rtl/qwen_sys/d2d_static_20261015/ovl_release_rope'
ROW266 = 266 * 8 // 4      # hex digits per 4096x266_m8 row (512 rows)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def l_pattern(msgs, seg, start, S, n59):
    """layer_compile.sys_face_events dual-L law (QSLOT empty): KVSLOT before each x3 slot, VIS / complete after the
    last RESULT lands, relative to the L calendar start edge of that segment."""
    kv = sorted((m for m in msgs if m.get('seg', 0) == seg and m['src'] == 'C' and m['tx_port'] == 3), key=lambda m: m['cyc'])
    r = sorted((m for m in msgs if m.get('seg', 0) == seg and m['src'] == 'K' and m['tx_port'] == 0 and m['kind'] == 3),
               key=lambda m: m['beat'])
    if len(kv) != 4 or len(r) != 32:
        raise ValueError(f'seg {seg}: 4 KVN + 32 RESULT messages expected, got {len(kv)} / {len(r)}')
    vis = r[-1]['arrive'] + 2 + S['CS_RXV'] + 4 + n59 + 2 - start
    pat = sorted([[m['cyc'] + S['CS_X3S'] - 3 - start, 3, i] for i, m in enumerate(kv)] + [[vis, 4, 0], [vis + 2, 4, 1]])
    if pat[0][0] < 2 or len({e[0] for e in pat}) != len(pat):
        raise ValueError(f'seg {seg}: L pattern starts before start + 2 or has an edge collision: {pat}')
    return pat


def events(cal, svh, n59):
    import layer_compile as LC
    S = cal['die_stages']
    ev = LC.sys_face_events(cal, svh, S, None, None, n59)
    l0_start = cal['program']['layers'][0]['start']          # token run: L0 starts l0 after the token-run cal start
    ev['L0'] = l_pattern(cal['messages'], 1, l0_start, S, n59)   # STAGE 1 -> source segment 0 = paired seg 1
    ev['L1'] = l_pattern(cal['messages'], 0, 0, S, n59)          # STAGE 2..36 -> segment-1 base = paired seg 0
    if ev['L1'] != sorted([list(e) for e in ev['L_compiled']]):
        raise ValueError('decode L pattern differs from layer_compile.sys_face_events L_compiled')
    ev.pop('L_compiled')
    return ev, S


def program_words(ctlm_dir, calendar_dir=None):
    w = [int(x, 16) for x in (Path(ctlm_dir) / 'program.memh').read_text().split()]
    if len(w) != SFI.PW + SFI.DW:
        raise ValueError('ctlm program.memh must be PW1024 + DW8')
    if calendar_dir:
        # The bound TT (hp13 rrloc cpub39, PRIVATE_CALR 1) plays its slice-command calendar from calendar_m0/m1 and takes
        # DW0..7 = the calendar image's dw.hex (DW0 'CALR' | nent, DW6 = the CTX_SRC empty boot record 0x4D43 << 48),
        # installed through the sys_face program replay; ctlm_image's CALD DW words belong to the ROM-less cmd_cal.
        dw = [int(x, 16) for x in (Path(calendar_dir) / 'dw.hex').read_text().split()]
        if len(dw) != SFI.DW or dw[0] >> 32 != 0x43414C52 or dw[6] != 0x4D43 << 48:
            raise ValueError('calendar dw.hex must be 8 words, DW0 CALR, DW6 0x4D43<<48')
        w[SFI.PW:] = dw
        return w, 'DW0..7 = calendar dw.hex (CALR; DW6 CTX_SRC empty boot record)'
    if w[1029] or w[1030]:
        raise ValueError('ctlm DW5/DW6 already set')
    # tools/qwen_split/gc3_payload/build.py: mu_opcal.ctx_words({}, mask=set()) = (0, 0x4D43 << 48), the source ABI's
    # tagged empty CTX_SRC boot record; runtime CTX_SRC supplies the filler identities.
    w[1029], w[1030] = 0, 0x4D43 << 48
    return w, 'DW = ctlm_image CALD words, DW5/DW6 = 0 / 0x4D43<<48'


def guard_sv(names, digest):
    lines = ['// GENERATED by tools/qwen_split/qc_prog_roms.py (DIE-QC-59P): sim-only programme-ROM presence guard.',
             '// The ROM models only WARN on a missing +OT_ROM_DIR image and read zero; this module makes it fatal.',
             f'// manifest digest {digest}',
             'module qc_prog_rom_guard;',
             '`ifndef SYNTHESIS',
             '    string d;',
             '    task automatic need(input string n);',
             '        string f; integer fd;',
             '        begin',
             '            f = {d, "/", n, ".viamap.hex"};',
             '            fd = $fopen(f, "r");',
             '            if (fd == 0) $fatal(1, "QC_PROG_ROM_MISSING %s", f);',
             '            $fclose(fd);',
             '        end',
             '    endtask',
             '    initial if ($value$plusargs("OT_ROM_DIR=%s", d)) begin']
    lines += [f'        need("{n}");' for n in names]
    lines += [
             f'        $display("QC_PROG_ROM_GUARD OK {len(names)} images in %s (manifest {digest[:16]})", d);',
             '    end',
             '`endif',
             'endmodule', '']
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pair-calendar', required=True, help='program/calendar.json of the pair image the KV die boots')
    ap.add_argument('--d2d-image', required=True, help='d2d_cal_image.svh of the same pair image')
    ap.add_argument('--ctlm-dir', required=True, help='ctlm_image.py --out DIR (program.memh + ctlm_image.json)')
    ap.add_argument('--calendar-dir', help='DIR with calendar_m0/m1.viamap.hex + their receipt (TT calendar ROM)')
    ap.add_argument('--calendar-status', default='COMPILED_NOT_QUALIFIED')
    ap.add_argument('--calendar-note', default='')
    ap.add_argument('--calendar-generator', default='')
    ap.add_argument('--n59-land-edges', type=int, default=8, help='layer_compile.py default (native59 dr_o landing)')
    ap.add_argument('--ovl', action='store_true', help='also copy the 10-21 OVL list ROMs (only for a face that still '
                    'binds qfd_d2d_cal_seq_ovl_rope; DIE-QC-59Q single-seq cseq has none)')
    ap.add_argument('--ovl-dir', default=OVL_DIR)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    work = out / 'compile'; work.mkdir(exist_ok=True)
    images = []

    # ---- sys_face_cfg
    cal = json.loads(Path(a.pair_calendar).read_text())
    ev, S = events(cal, a.d2d_image, a.n59_land_edges)
    prog, dw_note = program_words(a.ctlm_dir, a.calendar_dir)
    rows, rec = SFI.build(ev, prog, a.d2d_image)        # enforces first_token + GO_OFS == D2D_FIRST_TOKEN, END == period
    (out / 'sys_face_cfg.viamap.hex').write_text(SFI.viamap(rows))
    (work / 'sys_face_events.json').write_text(json.dumps(ev, indent=1) + '\n')
    (work / 'sys_face_cfg.logical.memh').write_text(''.join(f'{rows.get(i, 0):018x}\n' for i in range(4096)))
    (work / 'program.memh').write_text(''.join(f'{w:016x}\n' for w in prog))
    rec['events'] = ev
    (work / 'sys_face_image.json').write_text(json.dumps(rec, indent=1) + '\n')
    ctlm = json.loads((Path(a.ctlm_dir) / 'ctlm_image.json').read_text())
    images.append(dict(
        instance='sys_face_cfg', macro='ot_rom_4096x72_m8', loads_into='u_glue.u_sys_face (qfd_sys_face_lctx3_wrapped '
        'L_CONTEXTS 1) .u_core.u_rom (default ROM_INSTANCE)', status='COMPILED_NOT_QUALIFIED',
        generator='tools/qwen_split/sys_face_image.py build()/viamap() via tools/qwen_split/qc_prog_roms.py',
        inputs=dict(pair_calendar=dict(path=str(Path(a.pair_calendar).resolve()), sha256=sha(a.pair_calendar)),
                    d2d_image=dict(path=str(Path(a.d2d_image).resolve()), sha256=sha(a.d2d_image)),
                    ctlm_program=dict(path=str((Path(a.ctlm_dir) / 'program.memh').resolve()),
                                      sha256=sha(Path(a.ctlm_dir) / 'program.memh'), ctlm_inputs=ctlm.get('inputs'),
                                      ctlm_digest=ctlm.get('digest'))),
        parameters=dict(first_token=ev['first_token'], go_ofs=ev['go_ofs'], d2d_first_token=ev['d2d_first_token'],
                        token_period=[e[0] for e in ev['T'] if e[1] == 1 and e[2] & 4][0], die_stages=S,
                        n59_land_edges=a.n59_land_edges, T_entries=len(rec['calendars']['T']),
                        L_entries=len(rec['calendars']['L']), E_entries=len(rec['calendars']['E']),
                        l_contexts=rec.get('l_contexts'), boot_records=rec['boot_records'],
                        program_digest=rec['program_digest'], dw=dw_note),
        gaps=['E calendar (EMBW/FILL) not compiled on main (layer_compile E_missing): no embedding-slot events',
              'L QSLOT (class 2) not compiled: no qualified Q-ready booking contract (layer_compile L_missing)',
              'program = ctlm_image.py main defaults (layer L1 on the 10-18 compiled token path + relay table, ISA '
              'die0 fused layer 0), not recompiled on the current bound QC relay table; its not_compiled list: '
              + '; '.join(ctlm.get('not_compiled', [])),
              'n59 landing 8 = layer_compile default, not re-measured on bindC',
              'HEAD_PREP: user0 prepare/HOST publication still unqualified (head_prepare_age.py BLOCKED by design); '
              'the pair image carries HP 21 (QC HEAD min measured 10-29) through d2d_cal_image_production '
              'D2D_HEAD_PREPARE_EDGES, which this image only inherits through D2D_FIRST_TOKEN / D2D_TOKEN_PERIOD']))

    # ---- OVL list ROMs (released copies)
    for n in (('ovl_c_tx', 'ovl_c_rx') if a.ovl else ()):
        src = (ROOT / a.ovl_dir / f'{n}.viamap.hex') if not Path(a.ovl_dir).is_absolute() else Path(a.ovl_dir) / f'{n}.viamap.hex'
        shutil.copyfile(src, out / f'{n}.viamap.hex')
        images.append(dict(instance=n, macro='ot_rom_4096x72_m8', status='RELEASED_COPY',
                           loads_into='u_glue.u_sys_face.u_core.u_cseq (qfd_d2d_cal_seq_ovl_rope) ' +
                                      ('u_tx_rom' if n.endswith('tx') else 'u_rx_rom'),
                           generator='tools/qwen_split/d2d_ovl_release.py (10-21 release, committed)',
                           inputs=dict(source=str(Path(a.ovl_dir) / f'{n}.viamap.hex'), sha256=sha(src)), parameters={},
                           gaps=['10-21 OVL release (OVL_TXDP_K 32h03030416, token 293376-form differs from the current '
                                 'KV pair calendar, TOK-QK-2 04:50/04:57); unused when the vehicle selects the '
                                 'single-seq cseq (DIE-QC-59Q)']))

    # ---- TT calendar ROMs
    for n in ('calendar_m0', 'calendar_m1'):
        loads = ('u_tt_ctlm*.u_core (qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1/_2) \\u_gi.u_cal.g_calrom.u_rom.' + n[-2:])
        if a.calendar_dir:
            src = Path(a.calendar_dir) / f'{n}.viamap.hex'
            shutil.copyfile(src, out / f'{n}.viamap.hex')
            images.append(dict(instance=n, macro='ot_rom_4096x266_m8', status=a.calendar_status, loads_into=loads,
                               generator=a.calendar_generator, inputs=dict(source=str(src.resolve()), sha256=sha(src),
                                                                            dw=sha(Path(a.calendar_dir) / 'dw.hex')),
                               parameters={}, gaps=[a.calendar_note] if a.calendar_note else []))
        else:
            (out / f'{n}.viamap.hex').write_text(('0' * ROW266 + '\n') * 512)
            images.append(dict(instance=n, macro='ot_rom_4096x266_m8', status='BLOCKED_EMPTY', loads_into=loads,
                               generator=None, inputs={}, parameters={}, gaps=[a.calendar_note or 'no generator input']))

    # ---- DV slice table ROMs (declared empty)
    for m in range(4):
        n = f'table_s0_m{m}'
        (out / f'{n}.viamap.hex').write_text(('0' * ROW266 + '\n') * 512)
        images.append(dict(instance=n, macro='ot_rom_4096x266_m8', status='BLOCKED_EMPTY',
                           loads_into='every bound DV slice stm u_core ... u_tload.u_ld.m%d (qfd_dv_table_rom_loader; '
                                      'TSLICE/SLICE = 0 on all 12 slices, so all slices share this name)' % m,
                           generator='tools/qwen_layerbench/programme_store.py (packer only)', inputs={}, parameters={},
                           gaps=['programme_store.py needs an opentallas.qwen.mu-table-input.v1 manifest (lowered '
                                 'per-slice PROG/BTAB/CROM for 36 stages x 12 slices x 4 users); no tool on main produces '
                                 'it (ctlm_image.py not_compiled G-C4 DV slice lowering)',
                                 'all-zero = every word invalid: the loader writes nothing and raises no fault',
                                 'the bound RTL names every slice table_s0_*: per-slice images need TSLICE passed per '
                                 'instance in the plan/binder']))

    for im in images:
        im['file'] = f"{im['instance']}.viamap.hex"
        im['sha256'] = sha(out / im['file'])
    body = json.dumps(images, sort_keys=True).encode()
    digest = hashlib.sha256(body).hexdigest()
    names = [im['instance'] for im in images]
    (out / 'qc_prog_rom_guard.sv').write_text(guard_sv(names, digest))
    manifest = dict(schema='opentallas.qwen.qc-programme-roms.v1', lane='DIE-QC-59P', status='COMPILED_NOT_QUALIFIED',
                    die='qwen_compute bindC (plan_qc52)', images=images, images_digest=digest,
                    plusarg='+OT_ROM_DIR=' + str(out.resolve()),
                    code_roms='not here: qtile_t*_b*_c* (768-tile code masks) load from the Codex cohort dirs '
                              '(+OT_QC_CODE_ROM_DIR with the Codex overlay models, or a hardlink union with this dir)',
                    guard='qc_prog_rom_guard.sv: instantiate once in the bench (sim only)',
                    tool=dict(path='tools/qwen_split/qc_prog_roms.py', sha256=sha(__file__)),
                    argv=sys.argv[1:] if argv is None else argv)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    (out / '.keep').write_text('DIE-QC-59P programme ROM images: keep (TOK-QK-2 loads them).\n')
    print(json.dumps({im['instance']: im['status'] for im in images}))
    print('IMAGES_DIGEST ' + digest)
    return 0


if __name__ == '__main__':
    sys.exit(main())
