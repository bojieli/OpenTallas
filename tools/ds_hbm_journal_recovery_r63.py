"""Read-only failed-run schema inventory, never a restore or arithmetic oracle."""
from pathlib import Path
import json,sqlite3


def inspect_failed_run(output):
    root=Path(output).resolve()
    receipt=json.loads((root/'receipt.json').read_bytes())
    db=root/'actual-prefix-journal/dictionary.sqlite'
    con=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True)
    descriptors={};rows=0
    try:
        for raw, in con.execute('select value from dictionary order by id'):
            rows+=1;value=json.loads(raw)
            if not isinstance(value,dict) or 'paths' not in value or not isinstance(value.get('value'),dict):continue
            body=value['value'];event=body.get('event')
            if not isinstance(event,str):continue
            entry=descriptors.setdefault(event,{'fields':set(),'descriptor_count':0})
            entry['fields'].update(body)
            if value.get('checksum'):entry['fields'].add('payload_sha256')
            if value.get('metadata'):entry['fields'].add('allocation_identity')
            entry['descriptor_count']+=1
    finally:con.close()
    for entry in descriptors.values():entry['fields']=sorted(entry['fields'])
    checkpoint=root/'actual-PC9-producer-checkpoint'
    return dict(status='EVIDENCE_AVAILABLE_NO_CHECKPOINT_RESTORE',
        output_root=str(root),terminal_status=receipt['status'],retired_PCs=receipt['retired_PCs'],
        observed_outputs=receipt['observed_outputs'],dictionary_rows=rows,event_schemas=descriptors,
        checkpoint_directory_exists=checkpoint.exists(),
        live_producer_state_available=False,
        missing_restore_state=['cached actual producer arrays','sector bytes and partial validity',
            'RF/state location versions','complete future-use retained values',
            'generation/lease/credit/port counters and ownership snapshot','V3 sealed state/payload and source contract'],
        recovery_from_payload_hashes=False,recovery_from_golden_or_witness=False,
        numerical_reexecution_performed=False,journal_open_mode='read-only',
        qualification='event schema inventory only; no full framed-event hash or lifecycle audit')
