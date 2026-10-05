"""Prepare the focused ORIGINAL R128 publication/capture/VM/C8 source gate.

Copy actual selected cones verbatim. No replacement arithmetic, new authority,
ledger, native model or behavioral ACK. The VM executes surviving writes.
"""
from pathlib import Path
import hashlib,json,re
import dsrom_s81_capture_parent as C
from dsrom_s81_spine_publication import bind_spine
ROOT=Path(__file__).resolve().parents[1]


def prepare(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    selected=ROOT/'rtl/dsrom_sys/s81_capture_parent/ot_v41_spine_w17w10.sv'
    s=bind_spine(selected.read_text())
    publication=s[s.index('    wire [R-1:0] pub_r_v'):s.index('    localparam integer CW')]
    # Use the original capture instance, with the emitted paired references.
    instance=s[s.index('    ot_dsrom_rd64_vm_capture #'):s.index('    always @(posedge clk or negedge rst_n)begin',s.index('    ot_dsrom_rd64_vm_capture #'))]
    die=C.hook('die',(ROOT/'rtl/dsrom_sys/c8/ot_chip_v41x_die_owner_safe_c8.sv').read_text().replace(
        '    parameter integer C8_PUBLICATION=0,','    parameter integer IDX_DRAIN_LOOKAHEAD=0,\n    parameter integer C8_PUBLICATION=0,'))
    quiet=re.search(r'wire capture_visibility_quiet=.*?;',die).group(0)
    quiet_assign=re.search(r'assign c8_write_quiet=.*?;',die).group(0)
    fault_assign=re.search(r'assign c8_write_quarantine=.*?;assign c8_write_fault=.*?;',die).group(0)
    # Exact ROM and later-writer assignment order from the selected tile.
    tile=(ROOT/'rtl/chip/ckvsel/ot_chip_v41x_tile.sv').read_text()
    rom=re.search(r'for \(q = 0; q < ROM_R;.*?;',tile).group(0)
    rom=rom.replace('if (rom_we[q])','if (rom_we[q] && (!S81_CAPTURE || capture_vm_accept[q]))')
    me=tile[tile.index('        for (q = 0; q < G; q = q + 1)\n            if (vw_me_we[q])'):tile.index('        // the vector unit (X_SU):')]
    xs=tile[tile.index('        for (q = 0; q < SUN; q = q + 1) if (xs_vm_we[q])'):tile.index('        // QE streamer: fetch list')]
    collective=tile[tile.index('        for (e = 0; e < 16; e = e + 1) begin\n            if (xa_we)'):tile.index('            if (xa_re)')]
    writes=rom+'\n'+me+xs+collective+'\n        end\n'
    text=(ROOT/'rtl/test/spine_publication/tb_s81_publication_r128.sv').read_text()
    replacements={'ACTUAL_PUBLICATION':publication,'ACTUAL_CAPTURE':instance,
                  'ACTUAL_ACCEPT_LOGIC':C.VM_ACCEPT,'ACTUAL_RETIREMENT_PREDICATE':quiet+'\n'+quiet_assign+'\n'+fault_assign,
                  'ACTUAL_VM_WRITES':writes}
    for token,content in replacements.items():
        if text.count(token)!=1:raise ValueError('nonunique source gate anchor '+token)
        text=text.replace(token,content)
    (out/'gate.sv').write_text(text)
    deps=['rtl/dsrom_sys/spine_publication/ot_v41_rom_publication_capture.sv',
          'rtl/dsrom_sys/rd64_capture/ot_dsrom_rd64_vm_capture.sv',
          'rtl/dsrom_sys/rd64_capture/ot_dsrom_s81_phase_capture_profile.sv',
          'rtl/dsrom_sys/c8/ot_dsrom_c8_stage_context.sv',
          'rtl/dsrom_sys/c8/ot_dsrom_c8_write_journal.sv']
    for name in deps:(out/Path(name).name).write_bytes((ROOT/name).read_bytes())
    pins=deps+['tools/dsrom_s81_spine_publication_gate.py','tools/dsrom_s81_spine_publication.py',
               'tools/dsrom_s81_capture_parent.py',str(selected.relative_to(ROOT)),
               'rtl/dsrom_sys/c8/ot_chip_v41x_die_owner_safe_c8.sv',
               'rtl/chip/ckvsel/ot_chip_v41x_tile.sv','rtl/test/spine_publication/tb_s81_publication_r128.sv']
    (out/'source.json').write_text(json.dumps(dict(scope='Original capture R128 literal publication/VM writer/finite capture/C8 fault+quiet component source gate only; no field arithmetic, token, clock/physical qualification',
        source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in pins},
        generated_gate_sha256=hashlib.sha256(text.encode()).hexdigest(),
        copies=['publication and quarantine join from bind_spine output','full unchanged R128 capture','VM_ACCEPT and surviving VM assignment order','die capture quiet/quarantine/fault predicate','actual C8 stage context consumer/retire and native journals']),indent=2)+'\n')
    return out

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    print(prepare(p.parse_args().out))
