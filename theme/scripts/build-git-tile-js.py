#!/usr/bin/env python3
"""Build patched application.js that injects a "Git" tile into the Applications page.

Takes the D-Link stock application.js (from extracted/web/pages/function/) and
appends a self-contained patch that:

  1. Monkey-patches applications_list_show() to append a <li id="git"> tile
     after the original render. The tile uses inline data: URIs for icons,
     so no server-side new file is needed (the squashfs is read-only).
  2. Wires hover/click directly on the injected <li> (bypasses APP_INFO so
     mouse_event_init / context menus stay out of git's way).
  3. Defines show_git_panel() that opens a jQuery UI dialog with the SSH
     clone URL pattern and an "Open gitweb" button.

Output: theme/assets/pages/function/application.js (overlay-ready - colony.sh
will bind-mount it over /usr/local/modules/web/pages/function/application.js).
"""

from __future__ import annotations
import base64
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SRC_JS = REPO / "extracted" / "web" / "pages" / "function" / "application.js"
ICON_OFF = REPO / "theme" / "assets" / "pages" / "images" / "management" / "git_off.png"
ICON_ON = REPO / "theme" / "assets" / "pages" / "images" / "management" / "git_on.png"
OUT_JS = REPO / "theme" / "assets" / "pages" / "function" / "application.js"


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def build_patch(icon_off_b64: str, icon_on_b64: str) -> str:
    return f"""

/* =====================================================================
 * COLONY EDITION - Git tile
 *
 * Adds a "Git" tile to the Applications page. Click opens a panel with
 * the SSH clone URL pattern and a link to gitweb at /git/gitweb.cgi.
 *
 * Implementation: monkey-patches applications_list_show() to inject a
 * <li> after the original render. Icons are inlined as data: URIs since
 * the firmware squashfs is read-only and bind-mounts only work for paths
 * that already exist.
 *
 * Source: github.com/MotherSphere/dns345-colony-edition
 * ===================================================================== */
(function(){{
    var GIT_ICON_OFF = "data:image/png;base64,{icon_off_b64}";
    var GIT_ICON_ON  = "data:image/png;base64,{icon_on_b64}";

    var RED  = "#7d2333";   // Colony burgundy
    var INK  = "#2e1a14";   // Colony ink
    var SOFT = "#f7edd9";   // Colony parchment soft

    var _orig_apps_list_show = applications_list_show;
    applications_list_show = function(){{
        _orig_apps_list_show.apply(this, arguments);
        if ($('#git').length > 0) return;  // idempotent

        var html = '<li id="git" style="cursor:pointer">'
                 + '<img id="icon_git" src="' + GIT_ICON_OFF + '">'
                 + '<div class="desc" id="desc_git">Git</div>'
                 + '</li>';
        $('#Menu_List').append(html);

        $('#git').mouseover(function(){{
            $('#icon_git').attr('src', GIT_ICON_ON);
            $('#desc_git').css('color', RED);
        }}).mouseout(function(){{
            $('#icon_git').attr('src', GIT_ICON_OFF);
            $('#desc_git').css('color', INK);
        }}).click(function(){{
            if (typeof chk_timeout === 'function' && !chk_timeout()) return;
            colony_show_git_panel();
        }}).on('contextmenu', function(e){{
            e.preventDefault();
        }});
    }};

    window.colony_show_git_panel = function(){{
        var nas_host = window.location.hostname || 'dns345';
        var ssh_url  = 'ssh://' + nas_host + '/mnt/HD/HD_a2/git/&lt;repo&gt;.git';
        var http_url = 'http://' + nas_host + '/git/gitweb.cgi';

        var body =
            '<div style="font-family:JetBrainsMono,Consolas,monospace;font-size:13px;color:' + INK + ';">'
          + '  <p style="margin:0 0 14px 0;">'
          + '    Bare repos live in <code>/mnt/HD/HD_a2/git/</code> on the NAS.'
          + '    Push / pull over SSH (root-key auth), browse over HTTP.'
          + '  </p>'
          + '  <div style="margin:0 0 6px 0;font-weight:bold;color:' + RED + ';">Clone a repo</div>'
          + '  <pre style="background:' + SOFT + ';border:1px solid ' + RED + ';'
                       + 'padding:8px 10px;margin:0 0 14px 0;border-radius:4px;'
                       + 'font-size:12px;white-space:pre-wrap;word-break:break-all;">'
                       + 'git clone ' + ssh_url + '</pre>'
          + '  <div style="margin:0 0 6px 0;font-weight:bold;color:' + RED + ';">Initialize a new bare repo</div>'
          + '  <pre style="background:' + SOFT + ';border:1px solid ' + RED + ';'
                       + 'padding:8px 10px;margin:0 0 14px 0;border-radius:4px;'
                       + 'font-size:12px;white-space:pre-wrap;word-break:break-all;">'
                       + 'ssh ' + nas_host + ' "cd /mnt/HD/HD_a2/git &amp;&amp; '
                       + 'git init --bare &lt;repo&gt;.git"</pre>'
          + '  <div style="margin:0 0 6px 0;font-weight:bold;color:' + RED + ';">Browse all repos</div>'
          + '  <p style="margin:0;"><a href="' + http_url + '" target="_blank" '
          + '   style="color:' + RED + ';text-decoration:underline;">'
          + '    ' + http_url + '</a></p>'
          + '</div>';

        if ($('#colony_git_panel').length === 0) {{
            $('body').append('<div id="colony_git_panel"></div>');
        }}
        $('#colony_git_panel').attr('title', 'Git Server')
                              .html(body);
        $('#colony_git_panel').dialog({{
            modal: true,
            width: 560,
            resizable: false,
            buttons: {{
                "Open gitweb": function(){{
                    window.open(http_url, '_blank');
                }},
                "Close": function(){{
                    $(this).dialog("close");
                }}
            }}
        }});
    }};
}})();
"""


def main():
    if not SRC_JS.exists():
        raise SystemExit(f"missing source application.js: {SRC_JS}")
    if not ICON_OFF.exists() or not ICON_ON.exists():
        raise SystemExit("missing git icons - run build-assets.py first")

    src = SRC_JS.read_text(encoding="utf-8")
    patch = build_patch(b64(ICON_OFF), b64(ICON_ON))

    OUT_JS.parent.mkdir(parents=True, exist_ok=True)
    OUT_JS.write_text(src + patch, encoding="utf-8")
    sz = OUT_JS.stat().st_size
    print(f"wrote {OUT_JS} ({sz} bytes; +{sz - len(src.encode('utf-8'))} from patch)")


if __name__ == "__main__":
    main()
