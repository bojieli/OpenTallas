"""One static region map for Qwen ROM attached-HBM payload plus in-band SECDED.

Rows are physical PC/bank row indices, columns are 32-byte sectors. No
runtime aperture control, attestation or authentication is introduced.
"""
def region_map(row0=24427):
    regions = [dict(name='native_KV_payload', first_row=0,last_row=35,sectors_per_PC_row=1024),
               dict(name='native_KV_check_payload', first_row=64,last_row=99,sectors_per_PC_row=128),
               dict(name='embedding_payload',first_row=row0,last_row=row0+148,sectors_per_PC_row=1024),
               dict(name='embedding_check_payload',first_row=row0+149,last_row=row0+167,sectors_per_PC_row=1024)]
    for i,a in enumerate(regions):
        for b in regions[i+1:]:
            if max(a['first_row'],b['first_row']) <= min(a['last_row'],b['last_row']):
                raise ValueError('overlapping static payload regions')
    return dict(schema='opentallas.qwen.protected_phy.static_regions.v1',
                rows=regions, stacks=4,PCs_per_stack=32,physical_burst_bytes=32,
                check_payload_fraction=.125,
                embedding_row_padding_bytes=(19-149/8)*32768*128,
                ECC_sector_order='j={bank[4:2],col[4:0],bank[1:0]}; each sector packs8successive32bit check fields',
                integration='nativegenerator and bootloader must use this exactstaticmap; providerprototype implements same mapping',
                native_JEDEC_binding=False)
