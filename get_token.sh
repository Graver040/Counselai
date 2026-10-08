#!/bin/bash
export SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())")

# Read config from backend/.env so keys stay in one place (no hardcoded/stale keys)
ENV_FILE="$(dirname "$0")/backend/.env"
SUPABASE_URL=$(grep '^SUPABASE_URL=' "$ENV_FILE" | cut -d= -f2-)
ANON_KEY=$(grep '^SUPABASE_ANON_KEY=' "$ENV_FILE" | cut -d= -f2-)

curl -s -X POST "$SUPABASE_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@counselai.in","password":"test1234!"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token']) if 'access_token' in d else sys.exit('Auth failed: '+str(d))"