"""Source-owned native F20 target allocation and encoding contract."""
import json
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[2] / 'results/arch/hbm_vm_calendar_1015/program_target_map.json'


def target_contract(target):
    table = json.loads(REGISTRY.read_text())
    try:
        return table['external_targets'][str(target)]
    except KeyError as error:
        raise ValueError(f'Unallocated external programme target {target}') from error


def raw_control256(image):
    """Validate actual two-controls/512b SRAM transport without protected-word alias."""
    target = int(image['target'])
    contract = target_contract(target)
    if contract.get('encoding') != 'raw_control256':
        raise ValueError('Target does not own native raw control256 encoding')
    programme = image['programme']
    start = {key: int(programme['start'][key]) for key in ('base', 'limit', 'loops')}
    if not (0 <= start['base'] < start['limit'] <= contract['capacity_cycles']):
        raise ValueError('Raw control range exceeds actual19-bank capacity')
    if start['base'] % 2 or start['loops'] != 1:
        raise ValueError('Raw control256 requires even cycle base and loops1')
    words = {}
    for item in programme['configuration_writes']:
        address = int(item['addr'])
        word = int(item['data'], 16) if isinstance(item['data'], str) else int(item['data'])
        if address in words or not 0 <= address < contract['capacity_cycles']:
            raise ValueError('Duplicate/out-of-range raw256 frame')
        if not 0 <= word < 1 << contract['payload_bits']:
            raise ValueError('Raw control256 upper18 reserved bits must be zero')
        words[address] = word
    # Actual SRAM writes assemble complete pairs, including an unused odd tail.
    required = set(range(start['base'], (start['limit'] + 1) // 2 * 2))
    if not required <= words.keys():
        raise ValueError('Raw control256 programme lacks a complete executing SRAM pair')
    return start, words, contract


def raw_engram_fetch(image):
    """Pack seven actual32-bit ENGRAM_FETCH_ROWS8 operations per raw SRAM word."""
    contract = target_contract(int(image['target']))
    if contract.get('encoding') != 'raw_engram_fetch7x32':
        raise ValueError('Target does not own ENGRAM_FETCH_ROWS8 encoding')
    programme = image['programme']
    start = {key: int(programme['start'][key]) for key in ('base', 'limit', 'loops')}
    if not (0 <= start['base'] < start['limit'] <= 896 and start['base'] % 7 == 0 and start['loops'] == 1):
        raise ValueError('Engram fetch requires seven-aligned base, <=896 cycles and loops1')
    words = {}
    for item in programme['configuration_writes']:
        address = int(item['addr'])
        word = int(item['data'], 16) if isinstance(item['data'], str) else int(item['data'])
        if address in words or not 0 <= address < 128:
            raise ValueError('Duplicate/out-of-range Engram fetch SRAM word')
        if not 0 <= word < 1 << 224:
            raise ValueError('Engram fetch raw word upper32 reserved bits must be zero')
        if any(((word >> (32*slot)) & 0xffffffff) not in (0, 1, 2, 3) for slot in range(7)):
            raise ValueError('Engram fetch opcode/reserved bits invalid')
        words[address] = word
    if not set(range(start['base']//7, (start['limit']+6)//7)) <= words.keys():
        raise ValueError('Engram fetch programme contains an executing SRAM hole')
    events = [(words[pc//7] >> (32*(pc%7))) & 0xffffffff
              for pc in range(start['base'], start['limit'])]
    if [event for event in events if event] != [1, 2, 3]:
        raise ValueError('Engram fetch requires exactly EPOCH, HASH, FETCH_START in order')
    return start, words, contract
