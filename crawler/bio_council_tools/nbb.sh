for p in "$@"; do n=${p%%|*}; q=${p#*|}; echo "=== $n"; python3 /tmp/nb.py "$n" "$q" 3 2>&1 | cut -c1-330; done
