#!/bin/bash
set -e

SUPABASE_URL="https://wbnjgrkuzozymurnzhob.supabase.co"
# Read ANON_KEY from .env or hardcode for testing
ANON_KEY=$(grep SUPABASE_ANON_KEY .env 2>/dev/null | cut -d= -f2- || echo "")
if [ -z "$ANON_KEY" ]; then
  echo "Set SUPABASE_ANON_KEY in .env"
  exit 1
fi

BASE="http://localhost:8000"
EMAIL="test@counselai.in"
PASS="test1234!"

echo "=== Getting token ==="
TOKEN=$(curl -s -X POST "$SUPABASE_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo "Token: ${TOKEN:0:20}..."

echo "=== List documents ==="
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/documents" && echo ""

echo "=== Upload PDF ==="
if [ -n "$1" ]; then
  curl -s -X POST "$BASE/api/v1/documents" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$1" && echo ""
else
  echo "Skipped (pass a PDF path as argument)"
fi
