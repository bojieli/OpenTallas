"""Join immutable source-produced descriptor/payload bytes; no hardware service credit."""
import hashlib,json,struct,subprocess
from pathlib import Path
PATH='results/rtl/deepseek_hbm_complete_20261001/index-tagged-producer-gate-r1.json'
REV='6682c49a7'

def load():
    b=subprocess.check_output(['git','show',REV+':'+PATH]);return b,json.loads(b)

def join():
    b,d=load();pins={}
    for p,sha in d['source_pins'].items():
        actual=hashlib.sha256(subprocess.check_output(['git','show',d['source_commit']+':'+p])).hexdigest()
        if actual!=sha:raise ValueError('source pin mismatch '+p)
        pins[p]=sha
    rows=[]
    for w in d['witnesses']:
        desc=bytes.fromhex(w['descriptor_sector_hex']);payload=bytes.fromhex(w['initialized_payload_sector_hex'])
        if len(desc)!=32 or desc[:4]!=b'IKD1':raise ValueError('descriptor')
        fmt=desc[4];flags=desc[5];length=int.from_bytes(desc[6:8],'little');epoch=int.from_bytes(desc[8:16],'little')
        if fmt!=w['format'] or length!=w['payload_bytes'] or (fmt,length) not in [(1,68),(2,512)]:raise ValueError('format/length')
        if len(payload)!=(96 if fmt==1 else 512):raise ValueError('initialized sector size')
        if fmt==1 and any(payload[68:]):raise ValueError('padding not initialized')
        produced=struct.pack('<128I',*w['actual_produced_F32_bits']);sha=hashlib.sha256(produced).hexdigest()
        if sha!=w['retained_reference_F32_sha256'] or sha!=w['actual_returned_F32_sha256']:raise ValueError('producer/return')
        if fmt==2 and payload!=produced:raise ValueError('fallback is not actual produced bits')
        sectors=len(payload)//32+1
        rows.append({'name':w['name'],'format':fmt,'flags':flags,'valid_length':length,'epoch':epoch,
            'descriptor_sector_hex':desc.hex(),'payload_sector_sha256':hashlib.sha256(payload).hexdigest(),
            'produced_F32_sha256':sha,'payload_sectors':len(payload)//32,'descriptor_sectors':1,
            'writer_and_reader_sector_transfers':2*sectors,'production_command_count':None,'software_payload_request_length_sectors':len(payload)//32,'physical_command_grouping_bound':False,'writer_and_reader_port_bytes':64*sectors,
            'software_bit_exact':w['bit_exact'],'ordinary_GPU_producer_lowered':w['producer_receipt'].get('ordinary_GPU_producer_lowered'),
            'actual_controller_addresses':None,'stack_PC_distribution':None,'physical_visible_ACK':None})
    return {'schema':'w13.index-descriptor-byte-join.v2','producer_evidence_pin':{'source_git':REV,'path':PATH,'sha256':hashlib.sha256(b).hexdigest()},
      'producer_source_git':d['source_commit'],'verified_source_pins':pins,'rows':rows,
      'actual_software_row_events':d['actual_software_row_events'],'software_outstanding_leases':d['outstanding_row_leases'],
      'software_outstanding_publications':d['outstanding_publications'],'checkpoint_data_reads':d['checkpoint_data_reads'],
      'descriptor_schema':'IKD1 magic4,formatU8,flagsU8,lengthLE16,epochLE64 then16initialized padding bytes',
      'old_screen_descriptor_superseded':'89c proposed address/owner/hash descriptor fields were candidate-only; actual descriptor does not contain them',
      'routing_metadata_gate':'owner/global-key/base-address/source provenance must be bound separately; not inferred from descriptor',
      'scope':'eight source-produced software microfixture rows; not full checkpoint callbacks or physical transactions',
      'superseded_label':'a104421d4 writer_and_reader_commands meant sector transfers; not production commands; old bytes preserved','physical_calendar':None,'nonfinite_score_consumer':'reference-only; ordinary hardware unresolved',
      'physical_admission':'FAIL_CLOSED','rate_credit':0,'hardware_launch':False,'baseline_066_preserved':True}

if __name__=='__main__':
    import sys
    Path(sys.argv[1]).write_text(json.dumps(join(),indent=2)+'\n')
