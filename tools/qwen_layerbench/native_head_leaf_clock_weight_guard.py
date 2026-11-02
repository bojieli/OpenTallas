import hashlib,json,pathlib,re,shutil
p=pathlib.Path(__file__).resolve().parent
s=(p/'selected_parent.sv').read_text();a=s.index('qfd_tile_nk_rp2_romleaf_rr u_u_t_0_0 (');b=s.index('\n    );',a)
clks=dict(re.findall(r'\.(ck\w*)\(([^)]+)\)',s[a:b]));r=json.loads((p/'selected_clock_bindings.json').read_text())
assert len(clks)==39 and clks==r['bindings'] and set(clks.values())=={'clk'}
assert hashlib.sha256(s.encode()).hexdigest()==r['parent_sha256']
cut=(p/'native_tile0_cut.sv').read_text();assert all(f'.{n}(clk)'in cut for n in clks)
# Mutant has a fresh directory; preserve every baseline physical mask byte.
shutil.copytree(p/'rom',p/'rom_wrong_weight')
f=p/'rom_wrong_weight/qtile_t0_b4_c0.viamap.hex';lines=f.read_text().splitlines();values=[int(x,16)for x in lines]
def word(rows,adr):return sum(((rows[adr//8]>>(8*b+adr%8))&1)<<b for b in range(256))
assert word(values,2048)&255==0xd6
values[256]^=1
assert word(values,2048)&255==0xd7
lines[256]=f'{values[256]:0{len(lines[256])}x}'
f.write_text('\n'.join(lines)+'\n')
print('SELECTED_39_CLOCK_BINDINGS_PASS WRONG_WEIGHT_CODE_D6_TO_D7')
