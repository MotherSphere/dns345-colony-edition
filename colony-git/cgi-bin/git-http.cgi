#!/ffp/bin/bash
# /colony-git/repos/* CGI wrapper around git-http-backend.
#
# Why a wrapper instead of lighttpd auth.backend ?
#   The lighttpd 1.4.28 build that ships on this D-Link DNS-345 has a broken
#   mod_auth password-verify path. crypt(3) returns correct hashes via perl
#   and openssl, but lighttpd reports "password doesn't match" for every
#   stored format ($apr1$, $1$, DES, {SHA}, plaintext). Rather than fight a
#   patched binary, we authenticate here and unconditionally exec
#   git-http-backend on success.
#
# Accepted credential forms in the Basic password field:
#   - the user's plain password (verified against the $1$ htpasswd entry)
#   - a Personal Access Token (40 hex chars, looked up in $TOKEN_DIR)
#
# The username MUST match the credential's owner in both cases.

set -u

. "$(dirname "$0")/lib-auth.sh"

GIT_HTTP_BACKEND=/ffp/libexec/git-core/git-http-backend
REALM="Colony Git"

deny() {
    printf 'Status: 401 Unauthorized\r\n'
    printf 'WWW-Authenticate: Basic realm="%s"\r\n' "$REALM"
    printf 'Content-Type: text/plain; charset=utf-8\r\n'
    printf '\r\n'
    printf '%s\n' "$1"
    exit 0
}

AUTH=${HTTP_AUTHORIZATION:-}
case "$AUTH" in
    Basic\ *) ;;
    *) deny "authentication required" ;;
esac
B64=${AUTH#Basic }
DECODED=$(printf '%s' "$B64" | /ffp/bin/base64 -d 2>/dev/null)
if [ -z "$DECODED" ] || [ "${DECODED#*:}" = "$DECODED" ]; then
    deny "malformed Authorization header"
fi
USER=${DECODED%%:*}
PASS=${DECODED#*:}

case "$USER" in
    ''|*[!A-Za-z0-9_-]*) deny "invalid username" ;;
esac

# Password check (htpasswd) first - the cheap path for interactive users.
VERIFIED=$(verify_password "$USER" "$PASS")
if [ -z "$VERIFIED" ]; then
    # Fallback: treat the password as a PAT. The token's owner must match
    # the supplied username (defence in depth).
    TU=$(token_user "$PASS")
    if [ -n "$TU" ] && [ "$TU" = "$USER" ]; then
        VERIFIED=$TU
    fi
fi
[ -n "$VERIFIED" ] || deny "invalid credentials"

export REMOTE_USER=$VERIFIED
exec "$GIT_HTTP_BACKEND"
