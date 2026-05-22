#!/ffp/bin/bash
# GET /colony-git/whoami.cgi
# Returns {"user":"<name>"} when the caller is authenticated by either
#   - a valid colony_session cookie (web SPA after /login.cgi), or
#   - HTTP Basic auth (legacy / programmatic access)
# Returns 200 with {"user":null} when anonymous (used by the topbar to
# decide whether to show "Sign in" or "Hi, <user>"). The 401 + WWW-Auth
# response that previously was returned here is no longer needed now that
# the SPA uses a real login form instead of the browser popup.

set -u

. "$(dirname "$0")/lib-auth.sh"

USER=$(current_user)

printf 'Content-Type: application/json; charset=utf-8\r\n'
printf 'Cache-Control: no-store\r\n'
printf '\r\n'

if [ -n "$USER" ]; then
    printf '{"user":"%s"}\n' "$USER"
else
    printf '{"user":null}\n'
fi
