#!/bin/sh

../../../litani init --project test-1
if [ "$?" != 0 ]; then kill $$; exit 1; fi

make -B
if [ "$?" != 0 ]; then kill $$; exit 1; fi

../../../litani run-build
if [ "$?" != 0 ]; then kill $$; exit 1; fi
