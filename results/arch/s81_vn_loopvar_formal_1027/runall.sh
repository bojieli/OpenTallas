cd /fv
./gen.sh ot_s81sl_vn_rf8 "-set W 128" rf8 &
./gen.sh ot_s81sl_vn_b "-set HW_STAGE 0" vnb_hw0 &
./gen.sh ot_s81sl_vn_b "-set HW_STAGE 1" vnb_hw1 &
./gen.sh ot_s81sl_vn_a "" vna &
wait
