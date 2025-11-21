#!/usr/bin/env bash
set -euo pipefail

echo "Running tests..."
python -m pytest -q

echo
echo "Running self-contained demo (dry-run, verbose) and saving output to demo-output.txt"
mkdir -p demo-output
python scripts/demo_demo.py 2>&1 | tee demo-output/demo-output.txt

echo
echo "Also run a rule-filtered dry-run (Spam/Promo)"
python main.py --dry-run --verbose --rule "Spam/Promo" 2>&1 | tee -a demo-output/demo-output.txt

echo
echo "Demo complete. Output saved to demo-output/demo-output.txt"