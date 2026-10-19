#!/usr/bin/env python3
"""Isolated actual-ODB fixed clock row/PDN candidate. No timing/admission.

An optional addon builds literal followpins against an existing supply grid.
This does not run STA; native whole-grid continuity remains a separate gate.
"""
import argparse,hashlib,json
from pathlib import Path
from openroad import Tech,Design


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main(a):
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads(Path(a.manifest).read_text());names=[r[0] for r in manifest['cells']]
    if not manifest.get('clock_power_site_model'):raise ValueError('actual PG-safe topology model required')
    if any(any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in n) for n in names):
        raise ValueError('unsupported explicit clock identifier')
    t=Tech();d=Design(t);d.readDb(a.odb);b=d.getBlock()
    before={i.getName():(tuple(i.getLocation()),str(i.getOrient())) for i in b.getInsts()}
    record=dict(schema='opentallas.qwen.fixed_clock_pg_candidate.v1',tool_source=a.tool_source,
                input_odb_sha256=sha(a.odb),input_manifest_sha256=sha(a.manifest),
                row_policy_sha256=sha(a.policy),driver_sha256=sha(__file__),clock_cells=len(names),
                actual_pdn_addon_requested=a.pdn_addon,power_qualified=False,continuity_qualified=False,
                timing_qualified=False,production_admitted=False,steps=[])
    def command(code,expected=0):
        # OpenROAD evalTclString swallows Tcl errors: always inspect catch.
        status=d.evalTclString('set candidate_code [catch {'+code+'} candidate_message]; set candidate_code')
        message=d.evalTclString('set candidate_message');status=int(status)
        record['steps'].append(dict(command=code,status=status,message=message,expected=expected))
        (out/'record.json').write_text(json.dumps(record,indent=1)+'\n')
        print(json.dumps(record['steps'][-1]),flush=True)
        if status!=expected:raise ValueError('actual Tcl command status mismatch: '+str(record['steps'][-1]))
        return message
    command('source {'+a.policy+'}')
    command('set candidate_clocks {'+' '.join(names)+'}')
    command('ot_clock_rows_candidate $candidate_clocks')
    if before!={i.getName():(tuple(i.getLocation()),str(i.getOrient())) for i in b.getInsts()}:
        raise ValueError('row candidate changed actual cell coordinates/orientations')
    record['all_cell_coordinates_unchanged']=True
    record['physical_rows_created']=True;record['physical_rows']=len(b.getRows())
    # Bound PG pins and legal rows alone cannot pass this contact guard.
    command('ot_clock_pg_contact_check $candidate_clocks',expected=1)
    d.writeDb(str(out/'rows_candidate.odb'))
    if a.pdn_addon:
        for code in (
            'set_voltage_domain -name CORE -power VDD -ground VSS',
            'define_pdn_grid -name clock_existing -existing',
            'define_pdn_grid -name clock_followpins -voltage_domains CORE -starts_with GROUND',
            'add_pdn_stripe -grid clock_followpins -layer M1 -width .018 -followpins',
            'add_pdn_stripe -grid clock_followpins -layer M2 -width .018 -followpins',
            'add_pdn_connect -grid clock_followpins -layers {M1 M2}',
            'add_pdn_connect -grid clock_followpins -layers {M2 M9}',
            'pdngen -dont_add_pins -failed_via_report {'+str(out/'failed_vias.rpt')+'}',
            'ot_clock_pg_contact_check $candidate_clocks',
            'ot_tie_rows_verify 8.64 .48',
        ):command(code)
        if before!={i.getName():(tuple(i.getLocation()),str(i.getOrient())) for i in b.getInsts()}:
            raise ValueError('PDN candidate changed actual cell coordinates/orientations')
        record['literal_clock_contacts_and_stack_short_check_pass']=True
        d.writeDb(str(out/'pdn_candidate.odb'))
    manifest['clock_pg_candidate']=record
    (out/'manifest.json').write_text(json.dumps(manifest)+'\n')
    (out/'record.json').write_text(json.dumps(record,indent=1)+'\n')
    print('CLOCK_PG_CANDIDATE_DONE continuity_qualified=0 timing_qualified=0',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('odb','manifest','policy','out','tool-source'):p.add_argument('--'+n,required=True)
    p.add_argument('--pdn-addon',action='store_true')
    main(p.parse_args())
