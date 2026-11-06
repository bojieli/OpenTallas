cd /p
./run.sh new    "adv_x" "{19{_229667_}}" "take_x" "{31{_229719_}}"
./run.sh m_inv  "adv_x" "{19{_229667_}}" "~take_x" "{31{_229719_}}"
./run.sh m_bit  "adv_x" "{{18{_229667_}},1'b0}" "take_x" "{31{_229719_}}"
./run.sh m_swap "take_x" "{19{_229667_}}" "take_x" "{31{_229719_}}"
./run.sh m_noreg "adv_x" "{19{adv_x}}" "take_x" "{31{_229719_}}"
./run.sh m_noreg2 "adv_x" "{19{_229667_}}" "take_x" "{31{take_x}}"
