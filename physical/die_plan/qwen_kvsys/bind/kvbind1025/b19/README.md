# KV strict bind b19 (bind of record for the TOK-QK MU833 image), committed for closure rule 3

- Bind: tools/die_plan/bind.py elab|bind --strict|verify physical/die_plan/qwen_kvsys/die_plan.json
  --asbuilt physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_position_2144.rom64.json (repo-relative, provenance_bind.json).
- Source: codex/kv-bind-r8-2144@1768d1f6f (plan b09d581c.., recipe e9d840bd.., bind.py a5f559d5.. byte-identical to the Codex run tree
  epyc1:/srv/opentallas-scratch2/claude/codex-kv-bind-bank-2144/tree, an rsync copy, hence provenance commit null).
- b19 (Codex 22:37): strict bind 160 parts / 51 types, 0 errors / unbound / tied / undriven / multiply-bound / TYPE_SPLIT; R8 check PASS (r8_check.json).
- b20 (Codex, finished 23:29): full verify on the 15a9 PC-wrapper localparam fix: 2552344/2552344 matched, lint 0 errors (verify_report_b20.json).
  The b19 verify itself had 4 lint errors (PC localparam override), fixed by 15a9; b20 bus_groups.json == b19 (md5 9f04c16c).
- bus_groups.json.gz = gzip of b19/bus_groups.json (sha256 77d98d60e2998e17a14436f076940f3f338f850ad434868d85e1116c826fd30e).
