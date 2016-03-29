#!/bin/bash

# Calls pyspread from top level folder of extracted tarball

export PYTHONPATH=$PYTHONPATH:/home/mn/prog/pyspread/pyspread:/home/mn/prog/phoenix-2016-01-15
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/mn/prog/phoenix-2016-01-15/build/wxbld/libmn@Fuddel
echo $PYTHONPATH
python3.5 ./pyspread/src/pyspread.py $@
