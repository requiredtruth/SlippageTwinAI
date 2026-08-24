#!/usr/bin/env sh
set -eu
python -m unittest discover -s tests -v
python -m compileall -q slippagetwinai tests
./run.sh >/dev/null
echo "SlippageTwinAI verification complete"
