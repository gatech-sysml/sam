#!/bin/sh

gpu=1
cr=24
kr=6
dp=8
wd=2

mkdir -p "logs/model/last_minute/"
python -u src/train_multiclass.py --gpu $gpu \
  --coarse_classes \
  --crop_size $cr --kernel_size $kr \
  --depth $dp --width_factor $wd |
  tee "logs/model/last_minute/multiclass_crop${cr}_depth${dp}_width${wd}.log"