# Source me: `source tools/yosys_pin.sh || exit 2` sets YOSYS to a Yosys >= 0.68, else returns 2 (fail closed).  TOKc-YOSYS 2026-10-22.
# /usr/bin/yosys 0.52 (every fleet host) and 0.9 (localhost) dfflibmap map ASAP7 DFFASRHQNx1 with set/clear swapped:
# async-reset flops reset to the INVERTED value (HBMc k5 native lockstep 5/48).  Repro: python3 tools/yosys_pin.py --repro BIN
# Override with OT_YOSYS=<bin> (or YOSYS=<bin>); the override must itself be >= 0.68.
ot_yosys_pin() {
  local y=${OT_YOSYS:-${YOSYS:-${OPENTALLAS_TOOLS_ROOT:-$HOME/.local/opentallas-tools}/yosys-0.68/bin/yosys}} v
  v=$("$y" -V 2>/dev/null | sed -n 's/^Yosys \([0-9]*\)\.\([0-9]*\).*/\1 \2/p')
  if [ -z "$v" ] || [ "$(echo $v | awk '{print ($1>0 || $2>=68)}')" != 1 ]; then
    echo "yosys_pin.sh: '$y' is '$("$y" -V 2>&1 | head -1)', need Yosys >= 0.68 (async-flop dfflibmap set/clear swap in < 0.68)." \
         "Use \$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys (every fleet host) or the ORFS docker yosys." >&2
    return 2
  fi
  YOSYS=$y; export YOSYS
}
ot_yosys_pin || { return 2 2>/dev/null || exit 2; }
