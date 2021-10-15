#!/bin/sh

gpu=0
cr=16
kr=4
dp=28
wd=10

mkdir -p "logs/model/last_minute/"
python -u src/train_multiclass.py --gpu $gpu \
  --coarse_classes \
  --crop_size $cr --kernel_size $kr \
  --depth $dp --width_factor $wd |
  tee "logs/model/last_minute/multiclass_crop${cr}_depth${dp}_width${wd}.log"