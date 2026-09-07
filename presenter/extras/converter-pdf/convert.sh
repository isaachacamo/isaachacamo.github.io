#!/usr/bin/env bash
# Convenience wrapper: ./convert.sh talk.pdf [talk.tex] [paper.pdf]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
pdf="$1"; tex="${2:-}"; paper="${3:-}"
args=("$pdf")
[ -n "$tex" ]   && args+=(--tex "$tex")
[ -n "$paper" ] && args+=(--paper "$paper")
python3 "$here/src/converter/convert.py" "${args[@]}" \
        -o "$here/decks/$(basename "${pdf%.*}")-presenter.html"
