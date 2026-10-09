"""Static bank-distinct DATA/check map, unchanged row reservations and capacity."""
def sidecar_location(embedding, row, bank, col, row0=24427, mutant=False):
    j=((bank>>2)<<7)|(col<<2)|(bank&3)
    bh=(bank>>2) ^ (0 if mutant else 4)
    if embedding:
        offset=row-row0
        if not 0<=offset<149:raise ValueError('embedding row')
        erow=row0+149+(offset>>3)
        ebank=(bh<<2)|((offset>>1)&3)
        ecol=((offset&1)<<4)|((j>>3)&15)
    else:
        if not 0<=row<36:raise ValueError('KV row')
        erow=64+row;ebank=bh<<2;ecol=(j>>3)&15
    return erow,ebank,ecol,j&7

def model():
    from tools.qwen_protected_phy_pair_model import model as pair
    r=pair()
    r.update(schema='opentallas.qwen.protected_phy.bank_pair.v1',
        static_map='tools/qwen_protected_phy_bank_map.py',
        ECC_bank_hi='DATA bank[4:2] XOR4 (distinctSID/bank); no new bank orcapacity',
        ECC_KV_bank_lo=0,ECC_KV_col='j[6:3]',
        ECC_EMB_bank_lo='row_offset[2:1]',ECC_EMB_col='{row_offset[0],j[6:3]}',
        added_register_bits=0,added_area='3constantXOR bankbits +wiremapping; actual netlist/CTSdelta pending',
        read_latency='parallel max(actualDATA,ECC) +paircapturepublication; sharedPCtwo-burst andtRRD/tCCD/arbitration costs real, no zero native service claim',
        geometry_change=False,capacity_change=False,
        gate='exhaustive149x1024EMB and36x1024KV mappingbijection andbankdisjoint; mapmutantFAIL; actual256modeltags/stalls/outoforder/CE/UE andbootfences')
    return r
