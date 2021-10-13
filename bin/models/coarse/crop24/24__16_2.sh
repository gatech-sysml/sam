#!/bin/sh

gpu=0
dp=16
wd=2

cr=24
kr=$((cr / 4))
pd=$((cr / 8))


log_path="logs/model/coarse/all/crop${cr}_kernel${kr}_padding${pd}/depth${dp}_width${wd}/"
mkdir -p $log_path
python -u src/train.py --gpu $gpu \
  --coarse_classes \
  --crop_size $cr --depth $dp --width_factor $wd |
  tee "${log_path}model_coarse_all_crop${cr}_kernel${kr}_depth${dp}_width${wd}.log"
