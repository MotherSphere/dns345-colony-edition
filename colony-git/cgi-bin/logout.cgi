#!/ffp/bin/bash
# POST /colony-git/logout.cgi
# Destroys the session referenced by the cookie (if any) and tells the
# browser to clear it. Idempotent - safe to call even when not logged in.

set -u

. "$(dirname "$0")/lib-auth.sh"

TOKEN=$(cookie_token)
if [ -n "$TOKEN" ]; then
    delete_session "$TOKEN"
fi

# Cookie expiry in the past = browser clears it.
EXPIRED="${COOKIE_NAME}=; Path=/colony-git; HttpOnly; SameSite=Strict; Max-Age=0"

printf 'Content-Type: application/json; charset=utf-8\r\n'
printf 'Cache-Control: no-store\r\n'
printf 'Set-Cookie: %s\r\n' "$EXPIRED"
printf '\r\n'
printf '{"ok":true}\n'
