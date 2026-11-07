"""Build one finite actual-eight-page issuer packet, without compiling a die."""
import argparse
from copy import deepcopy
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools/s81_dv'))
from layer_prog.native_csr_image import decode_image, encode_image, compatibility
from layer_prog.native_markers import rebook


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--kit', type=int, required=True)
    p.add_argument('--end', type=int, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    images = []; reports = []; controls = []
    calendar = json.loads((ROOT/'tools/s81_dv/native_reload_1106/fixtures/calendar.json').read_text())
    for j in range(8):
        path = ROOT/f'results/token_pass/ds_native_csr_1106/input/job{j}/host_boot.memh'
        image = decode_image([int(x,16) for x in path.read_text().split()])
        changed, report = rebook(image, kit_issue=a.kit, end_issue=a.end)
        for name, ki, en in [('KIT_before_command_done', 0, a.end),
                             ('END_at_KIT', a.kit, a.kit),
                             ('negative_KIT', -1, a.end)]:
            try:
                rebook(image, kit_issue=ki, end_issue=en)
            except ValueError as exc:
                controls.append(dict(job=j, case=name, rejected=str(exc)))
            else:
                raise AssertionError('accepted '+name)
        # Independent semantic comparison, keyed by old command row, includes
        # actual template/CF objects. No expected command is taken from DUT output.
        for item in report['row_tag_map']:
            if item['engine'] < 14:
                assert image['rows'][item['old']] == changed['rows'][item['new']]
        assert image['templates'] == changed['templates'] and image['CF'] == changed['CF']
        assert decode_image(encode_image(changed))['rows'] == changed['rows']
        images.append(changed); reports.append(dict(job=j, input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), **report))
        old_rows = deepcopy(calendar['job'][j]['rows'])
        rebuilt = [None]*len(old_rows)
        for item in report['row_tag_map']:
            r = old_rows[item['old']]
            decoded = changed['rows'][item['new']]
            assert int(r['row76'],16) == sum(image['rows'][item['old']][key] << shift for key,shift in [('done',52),('issue',28),('engine',24),('arg',0)])
            r.update(decoded, i=item['new'], source_row_i=item['old'])
            r['row76'] = f"{(r['done']<<52)|(r['issue']<<28)|(r['engine']<<24)|r['arg']:019x}"
            rebuilt[item['new']] = r
        calendar['job'][j].update(rows=rebuilt, end_age=a.end,
                                  sealed_programme_held=True,
                                  marker_candidate_report=report)
        words = encode_image(changed)
        (a.out/f'job{j}.host.memh').write_text(''.join(f'{w:0129x}\n' for w in words))
        # Literal PW input to the SRAM walker; unrelated HOST bodies stay out.
        pw = [(w>>1) for w in words if ((w>>1)&255) == 0x10]
        (a.out/f'job{j}.pw.memh').write_text(''.join(f'{((w>>96)&127)<<28 | ((w>>32)&((1<<28)-1)):09x}\n' for w in pw))
        rows = changed['rows']
        packed = [(r['done']<<52)|(r['issue']<<28)|(r['engine']<<24)|r['arg'] for r in rows]
        (a.out/f'job{j}.rows.memh').write_text(''.join(f'{r:019x}\n' for r in packed))
        reverse = {x['new']:x['old'] for x in report['row_tag_map']}
        (a.out/f'job{j}.oldtags.memh').write_text(''.join(f'{reverse[i]:02x}\n' for i in range(len(rows))))
    sizes = [image['nops'] for image in images]
    calendar.update(rows=calendar['job'][0]['rows'], end_age=a.end,
                    sealed_programme_held=True, production_enabled=False,
                    marker_candidate=True)
    (a.out/'calendar.json').write_text(json.dumps(calendar,indent=2)+'\n')
    (a.out/'sizes.svh').write_text('localparam integer SIZE[8] = \''+'{'+','.join(map(str,sizes))+'};\n')
    summary = dict(scope='candidate issuer/row-tag repair only; row-done bound is not consumer retirement',
                   source_commands_changed=0, hardware_pin_cycles_added=0,
                   common_KIT=a.kit, common_END=a.end, pages=reports,
                   invalid_marker_controls=controls,
                   compatibility=compatibility(images),
                   production_enabled=False, lifetime_qualified=False, full_token=False)
    (a.out/'candidate.json').write_text(json.dumps(summary,indent=2)+'\n')
    for name in ('tb.sv', 'run.sh', 'tb47.sv', 'run47.sh'):
        shutil.copyfile(Path(__file__).parent/name, a.out/name)
    shutil.copyfile(ROOT/'rtl/dsrom_sys/s81_dv/unit/ot_dsdv_walk_issue.sv',
                    a.out/'ot_dsdv_walk_issue.sv')
    for name in ('rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hslot.sv',
                 'rtl/lib/ot_rst_relay.sv',
                 'rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv',
                 'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v'):
        shutil.copyfile(ROOT/name, a.out/Path(name).name)


if __name__ == '__main__':
    main()
