"""Generate exact512-bit reflected CRC32C parity logic; source model, no synthesis claim."""
from pathlib import Path
import hashlib,json,math
ROOT=Path(__file__).resolve().parents[3]

def crc(value, initial=0xffffffff):
    q=initial
    for i in range(512):
        b=(q^(value>>i))&1
        q=(q>>1)^(0x82f63b78 if b else 0)
    return q^0xffffffff

def main():
    constant=crc(0);columns=[crc(1<<i)^constant for i in range(512)]
    terms=[[i for i,c in enumerate(columns) if (c>>o)&1] for o in range(32)]
    lines=['// Generated GF(2) CRC32C: polynomial82f63b78, init/finalffffffff, bit0 first.',
           '//64raw bytes little endian; combinational result captured at body+1.',
           'module dsdv_hostb_crc512(input wire [511:0] d, output wire [31:0] q);']
    for o,row in enumerate(terms):
        expr=' ^ '.join(f'd[{i}]' for i in row)
        if (constant>>o)&1:expr+=" ^ 1'b1"
        lines.append(f'assign q[{o}] = {expr};')
    lines.append('endmodule')
    out=ROOT/'rtl/dsrom_sys/s81_dv/hostb/dsdv_hostb_crc512.sv';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text('\n'.join(lines)+'\n')
    model={'crc':'CRC32C reflected82f63b78/initffffffff/finalffffffff/512bits bit0first',
           'affine_constant_hex':hex(constant),'xor_terms_per_output':[len(x) for x in terms],
           'unshared_twoinput_xors':sum(len(x)-1 for x in terms),
           'balanced_source_depth_bound':max(math.ceil(math.log2(len(x))) for x in terms),
           'raw_crc_contacts_per_data_bit':[c.bit_count() for c in columns],
           'max_crc_contacts_per_data_bit':max(c.bit_count() for c in columns),
           'host_pipeline_payload_ff':1536,'crc_register_ff':32,'expected_crc_ff':32,
           'registered_body_to_legacy_emit_edges':2,'next_forward_merge_edges':2,'ordinary_payload_added_register_edges':0,'ordinary_payload_extra_muxes':1,'transit_rx_plus_tx_edges':3,'tx_payload_ff':2128,'tx_bank_select_ff':222,'tx_root_select_ff':9,
           'scope':'Source MODEL before build. Necessary unindexed pipe state; native/mapped area/clock/reset/physical stillOPEN. Separate realhostlanding edges notincluded.',
           'generated_rtl_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    dest=ROOT/'results/arch/s81_hostb_envelope_1021/crc_source_model.json';dest.write_text(json.dumps(model,indent=2)+'\n')
    print(json.dumps({k:v for k,v in model.items() if not isinstance(v,list)}))
if __name__=='__main__':main()
