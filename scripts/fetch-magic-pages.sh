#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/frontend/public/magic-pages"
mkdir -p "$OUT_DIR/時鐘"
BASE="https://y053731023-sys.github.io/magic.github.io"

curl -fsSL "$BASE/%E7%84%A1%E6%95%B5%E9%A0%90%E8%A8%80%E8%A1%93.html" -o "$OUT_DIR/無敵預言術.html"
curl -fsSL "$BASE/%E8%AE%80%E5%BF%83%E8%A1%93.html" -o "$OUT_DIR/讀心術.html"
curl -fsSL "$BASE/%E5%A5%A7%E8%A1%93%E8%AE%80%E5%BF%83.html" -o "$OUT_DIR/奧術讀心.html"
curl -fsSL "$BASE/mindreading.html" -o "$OUT_DIR/mindreading.html"
curl -fsSL "$BASE/calculmagic.html" -o "$OUT_DIR/calculmagic.html"
curl -fsSL "$BASE/giftlist.html" -o "$OUT_DIR/giftlist.html"
curl -fsSL "$BASE/eyestest.html" -o "$OUT_DIR/eyestest.html"
curl -fsSL "$BASE/%E6%99%82%E9%90%98/%E7%A2%BC%E8%A1%A8.html" -o "$OUT_DIR/時鐘/碼表.html"

echo "Fetched magic HTML pages into $OUT_DIR"
