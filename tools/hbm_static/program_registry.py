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
