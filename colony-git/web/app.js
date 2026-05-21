/* Colony Git - SPA (v2)
 *
 * Routes (hash-based):
 *   #/                          home (repo grid)
 *   #/<repo>                    repo home (Code tab, root tree + README)
 *   #/<repo>/tree/<path>        tree at <path>
 *   #/<repo>/blob/<path>        file content
 *   #/<repo>/commits            commits log
 *   #/<repo>/refs               branches + tags
 */

(function () {
    'use strict';

    var API = 'api/';
    var $ = function (sel) { return document.querySelector(sel); };

    // -----------------------------------------------------------------
    // Utilities
    // -----------------------------------------------------------------

    function el(tag, attrs, children) {
        var n = document.createElement(tag);
        if (attrs) {
            for (var k in attrs) {
                if (k === 'class') n.className = attrs[k];
                else if (k === 'html') n.innerHTML = attrs[k];
                else if (k === 'text') n.textContent = attrs[k];
                else if (k.indexOf('on') === 0 && typeof attrs[k] === 'function') {
                    n.addEventListener(k.slice(2), attrs[k]);
                } else if (attrs[k] !== null && attrs[k] !== undefined) {
                    n.setAttribute(k, attrs[k]);
                }
            }
        }
        if (children) {
            if (!Array.isArray(children)) children = [children];
            for (var i = 0; i < children.length; i++) {
                var c = children[i];
                if (c == null) continue;
                if (typeof c === 'string') n.appendChild(document.createTextNode(c));
                else n.appendChild(c);
            }
        }
        return n;
    }

    function esc(s) {
        if (s == null) return '';
        return String(s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function fmtBytes(n) {
        if (!n) return '0 B';
        var u = ['B', 'KB', 'MB', 'GB'];
        var i = 0;
        while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
        return n.toFixed(i === 0 ? 0 : 1) + ' ' + u[i];
    }

    function parseGitDate(s) {
        if (!s) return null;
        var iso = s.replace(' ', 'T').replace(/ ([+-]\d{2})(\d{2})$/, '$1:$2');
        var d = new Date(iso);
        return isNaN(d.getTime()) ? null : d;
    }

    function relTime(input) {
        var d;
        if (typeof input === 'number') {
            d = new Date(input * 1000);  // unix seconds
        } else {
            d = parseGitDate(input);
        }
        if (!d) return '';
        var sec = Math.floor((Date.now() - d.getTime()) / 1000);
        if (sec < 60)       return sec + 's ago';
        if (sec < 3600)     return Math.floor(sec / 60) + 'm ago';
        if (sec < 86400)    return Math.floor(sec / 3600) + 'h ago';
        if (sec < 604800)   return Math.floor(sec / 86400) + 'd ago';
        if (sec < 2592000)  return Math.floor(sec / 604800) + 'w ago';
        if (sec < 31536000) return Math.floor(sec / 2592000) + 'mo ago';
        return Math.floor(sec / 31536000) + 'y ago';
    }

    function copyText(text, button) {
        try {
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed'; ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
        } catch (e) { /* ignore */ }
        if (button) {
            var old = button.textContent;
            button.textContent = 'Copied';
            button.classList.add('copied');
            setTimeout(function () {
                button.textContent = old;
                button.classList.remove('copied');
            }, 1200);
        }
    }

    function api(endpoint, params) {
        var qs = [];
        if (params) for (var k in params) {
            if (params[k] != null && params[k] !== '') {
                qs.push(encodeURIComponent(k) + '=' + encodeURIComponent(params[k]));
            }
        }
        var url = API + endpoint + '.cgi' + (qs.length ? '?' + qs.join('&') : '');
        return fetch(url, { cache: 'no-store' }).then(function (r) {
            if (!r.ok) return r.json().then(function (j) {
                var e = new Error(j.error || ('HTTP ' + r.status));
                e.code = j.code || r.status;
                throw e;
            }, function () { throw new Error('HTTP ' + r.status); });
            var ct = r.headers.get('Content-Type') || '';
            return ct.indexOf('application/json') >= 0 ? r.json() : r.text();
        });
    }

    function showError(err) {
        $('#app').innerHTML = '';
        $('#app').appendChild(el('div', { class: 'error-box', text: 'Error: ' + (err.message || err) }));
    }
    function showLoading() {
        $('#app').innerHTML = '<div class="loading">Loading...</div>';
    }

    // -----------------------------------------------------------------
    // Tiny markdown renderer (block + inline)
    // -----------------------------------------------------------------
    function renderMarkdown(src) {
        if (!src) return '';
        src = src.replace(/\r\n/g, '\n');
        var codeBlocks = [];
        src = src.replace(/```([a-zA-Z0-9_+-]*)\n([\s\S]*?)```/g, function (_, lang, body) {
            codeBlocks.push({ lang: lang, body: body });
            return ' CB' + (codeBlocks.length - 1) + ' ';
        });
        var html = esc(src);
        html = html.replace(/^###### (.+)$/gm, '<h6>$1</h6>');
        html = html.replace(/^##### (.+)$/gm,  '<h5>$1</h5>');
        html = html.replace(/^#### (.+)$/gm,   '<h4>$1</h4>');
        html = html.replace(/^### (.+)$/gm,    '<h3>$1</h3>');
        html = html.replace(/^## (.+)$/gm,     '<h2>$1</h2>');
        html = html.replace(/^# (.+)$/gm,      '<h1>$1</h1>');
        html = html.replace(/^---+$/gm, '<hr>');
        html = html.replace(/(^&gt; .+(?:\n&gt; .+)*)/gm, function (m) {
            return '<blockquote>' + m.replace(/^&gt; /gm, '') + '</blockquote>';
        });
        html = html.replace(/(^[*-] .+(?:\n[*-] .+)*)/gm, function (m) {
            return '<ul>' + m.split('\n').map(function (l) {
                return '<li>' + l.replace(/^[*-] /, '') + '</li>';
            }).join('') + '</ul>';
        });
        html = html.replace(/(^\d+\. .+(?:\n\d+\. .+)*)/gm, function (m) {
            return '<ol>' + m.split('\n').map(function (l) {
                return '<li>' + l.replace(/^\d+\. /, '') + '</li>';
            }).join('') + '</ol>';
        });
        html = html.replace(/`([^`\n]+?)`/g, '<code>$1</code>');
        html = html.replace(/\*\*([^*\n]+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\b_([^_\n]+?)_\b/g, '<em>$1</em>');
        html = html.replace(/\*([^*\n]+?)\*/g, '<em>$1</em>');
        html = html.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, function (_, txt, href) {
            return '<a href="' + href + '" target="_blank" rel="noopener">' + txt + '</a>';
        });
        html = html.split(/\n{2,}/).map(function (block) {
            block = block.trim();
            if (!block) return '';
            if (/^<(h\d|ul|ol|blockquote|hr|pre| CB)/.test(block)) return block;
            return '<p>' + block.replace(/\n/g, '<br>') + '</p>';
        }).join('\n');
        html = html.replace(/ CB(\d+) /g, function (_, i) {
            var cb = codeBlocks[parseInt(i, 10)];
            return '<pre><code' + (cb.lang ? ' class="language-' + cb.lang + '"' : '') + '>'
                 + esc(cb.body) + '</code></pre>';
        });
        return html;
    }

    // -----------------------------------------------------------------
    // Language taxonomy (extension -> {name, color})
    // -----------------------------------------------------------------
    var LANG_MAP = {
        '.rs':       { name: 'Rust',       color: '#ce422b' },
        '.ts':       { name: 'TypeScript', color: '#3178c6' },
        '.tsx':      { name: 'TypeScript', color: '#3178c6' },
        '.js':       { name: 'JavaScript', color: '#f1e05a' },
        '.jsx':      { name: 'JavaScript', color: '#f1e05a' },
        '.mjs':      { name: 'JavaScript', color: '#f1e05a' },
        '.py':       { name: 'Python',     color: '#3572a5' },
        '.go':       { name: 'Go',         color: '#00add8' },
        '.c':        { name: 'C',          color: '#555555' },
        '.cpp':      { name: 'C++',        color: '#f34b7d' },
        '.cc':       { name: 'C++',        color: '#f34b7d' },
        '.cxx':      { name: 'C++',        color: '#f34b7d' },
        '.h':        { name: 'C Header',   color: '#7d2333' },
        '.hpp':      { name: 'C++ Header', color: '#7d2333' },
        '.java':     { name: 'Java',       color: '#b07219' },
        '.kt':       { name: 'Kotlin',     color: '#a97bff' },
        '.rb':       { name: 'Ruby',       color: '#701516' },
        '.php':      { name: 'PHP',        color: '#4f5d95' },
        '.sh':       { name: 'Shell',      color: '#89e051' },
        '.bash':     { name: 'Shell',      color: '#89e051' },
        '.cgi':      { name: 'Shell',      color: '#89e051' },
        '.html':     { name: 'HTML',       color: '#e34c26' },
        '.htm':      { name: 'HTML',       color: '#e34c26' },
        '.css':      { name: 'CSS',        color: '#563d7c' },
        '.scss':     { name: 'SCSS',       color: '#c6538c' },
        '.sass':     { name: 'SCSS',       color: '#c6538c' },
        '.md':       { name: 'Markdown',   color: '#83341f' },
        '.markdown': { name: 'Markdown',   color: '#83341f' },
        '.json':     { name: 'JSON',       color: '#cbb44d' },
        '.yaml':     { name: 'YAML',       color: '#cb171e' },
        '.yml':      { name: 'YAML',       color: '#cb171e' },
        '.toml':     { name: 'TOML',       color: '#9c4221' },
        '.xml':      { name: 'XML',        color: '#0060ac' },
        '.sql':      { name: 'SQL',        color: '#336791' },
        '.swift':    { name: 'Swift',      color: '#ffac45' },
        '.lua':      { name: 'Lua',        color: '#000080' },
        '.dart':     { name: 'Dart',       color: '#00b4ab' },
        '.gd':       { name: 'GDScript',   color: '#355570' },
        '.cs':       { name: 'C#',         color: '#178600' },
        '.vue':      { name: 'Vue',        color: '#41b883' },
        '.svelte':   { name: 'Svelte',     color: '#ff3e00' },
        '.nim':      { name: 'Nim',        color: '#ffc200' },
        '.zig':      { name: 'Zig',        color: '#ec915c' },
        '.elm':      { name: 'Elm',        color: '#60b5cc' },
        '.ex':       { name: 'Elixir',     color: '#6e4a7e' },
        '.exs':      { name: 'Elixir',     color: '#6e4a7e' },
        '.erl':      { name: 'Erlang',     color: '#b83998' },
        '.clj':      { name: 'Clojure',    color: '#db5855' },
        '.scala':    { name: 'Scala',      color: '#c22d40' },
        '.r':        { name: 'R',          color: '#198ce7' },
        '.txt':      { name: 'Text',       color: '#a08560' },
        '.cfg':      { name: 'Config',     color: '#8c6b52' },
        '.conf':     { name: 'Config',     color: '#8c6b52' },
        '.ini':      { name: 'Config',     color: '#8c6b52' },
        '.dockerfile':{ name: 'Dockerfile',color: '#384d54' }
    };
    function langInfo(ext) {
        if (LANG_MAP[ext]) return LANG_MAP[ext];
        return { name: ext ? ext.replace(/^\./, '') : 'Other', color: '#8c6b52' };
    }

    // -----------------------------------------------------------------
    // Popover (floating dropdown) primitives
    // -----------------------------------------------------------------
    var popoverDismissHandler = null;
    var currentAnchor = null;

    function openPopover(anchorEl, contentEl) {
        // Toggle: clicking the same anchor that opened the current popover closes it.
        if (currentAnchor === anchorEl) {
            closePopover();
            return;
        }
        if (currentAnchor) closePopover();

        currentAnchor = anchorEl;
        var pop = $('#popover');
        pop.innerHTML = '';
        pop.appendChild(contentEl);
        pop.classList.remove('hidden');

        var rect = anchorEl.getBoundingClientRect();
        var top  = rect.bottom + window.scrollY + 4;
        var left = rect.left   + window.scrollX;
        var maxLeft = window.scrollX + window.innerWidth - pop.offsetWidth - 8;
        if (left > maxLeft) left = maxLeft;
        if (left < 8) left = 8;
        pop.style.top  = top  + 'px';
        pop.style.left = left + 'px';

        // Dismiss on outside click / Escape. Clicks on the popover content
        // and on the anchor itself are ignored (anchor handles its own toggle).
        setTimeout(function () {
            popoverDismissHandler = function (e) {
                if (e.type === 'keydown' && e.key !== 'Escape') return;
                if (e.type === 'mousedown') {
                    if (pop.contains(e.target)) return;
                    if (currentAnchor && currentAnchor.contains(e.target)) return;
                }
                closePopover();
            };
            document.addEventListener('mousedown', popoverDismissHandler);
            document.addEventListener('keydown', popoverDismissHandler);
        }, 0);
    }

    function closePopover() {
        currentAnchor = null;
        var pop = $('#popover');
        pop.classList.add('hidden');
        pop.innerHTML = '';
        if (popoverDismissHandler) {
            document.removeEventListener('mousedown', popoverDismissHandler);
            document.removeEventListener('keydown', popoverDismissHandler);
            popoverDismissHandler = null;
        }
    }

    function openOverlay(contentEl, onDismiss) {
        var ov = $('#overlay');
        ov.innerHTML = '';
        ov.appendChild(contentEl);
        ov.classList.remove('hidden');
        var dismiss = function (e) {
            if (e.type === 'keydown' && e.key !== 'Escape') return;
            if (e.type === 'mousedown' && contentEl.contains(e.target)) return;
            ov.classList.add('hidden');
            ov.innerHTML = '';
            document.removeEventListener('mousedown', dismiss);
            document.removeEventListener('keydown', dismiss);
            if (onDismiss) onDismiss();
        };
        document.addEventListener('mousedown', dismiss);
        document.addEventListener('keydown', dismiss);
        return dismiss;
    }

    // -----------------------------------------------------------------
    // Components
    // -----------------------------------------------------------------

    function renderCodeToolbar(repo, info, ref) {
        var bar = el('div', { class: 'code-toolbar' });

        // Branch picker
        var branchBtn = el('button', { class: 'tb-btn', title: 'Switch branches/tags' }, [
            el('span', { class: 'icon-glyph', text: '⊢' }),  // ⊢
            ref || info.default_branch,
            el('span', { class: 'caret', text: '▼' })  // ▼
        ]);
        branchBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            openBranchPopover(repo, info, ref, branchBtn);
        });
        bar.appendChild(branchBtn);

        // Branches button (count)
        var bcount = (info.branches || []).length;
        var branchesLink = el('a', {
            class: 'tb-btn',
            href: '#/' + encodeURIComponent(repo) + '/refs',
            title: 'View all branches'
        }, [
            el('span', { class: 'icon-glyph', text: '⊢' }),
            'Branches',
            el('span', { class: 'count', text: bcount })
        ]);
        bar.appendChild(branchesLink);

        // Tags button (count)
        var tcount = (info.tags || []).length;
        var tagsLink = el('a', {
            class: 'tb-btn',
            href: '#/' + encodeURIComponent(repo) + '/refs',
            title: 'View all tags'
        }, [
            el('span', { class: 'icon-glyph', text: '#' }),
            'Tags',
            el('span', { class: 'count', text: tcount })
        ]);
        bar.appendChild(tagsLink);

        // Go to file search
        var gotofileWrap = el('div', { class: 'tb-search' });
        var gotofileInput = el('input', { type: 'text', placeholder: 'Go to file', readonly: true });
        gotofileInput.addEventListener('mousedown', function (e) {
            e.preventDefault();
            openGoToFile(repo, ref || info.default_branch);
        });
        gotofileWrap.appendChild(gotofileInput);
        bar.appendChild(gotofileWrap);

        // Code dropdown (clone URLs)
        var codeBtn = el('button', { class: 'tb-btn primary' }, [
            el('span', { class: 'icon-glyph', text: '<>' }),
            'Code',
            el('span', { class: 'caret', text: '▼' })
        ]);
        codeBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            openCodePopover(repo, codeBtn);
        });
        bar.appendChild(codeBtn);

        return bar;
    }

    function openBranchPopover(repo, info, currentRef, anchorEl) {
        var pop = el('div');
        var filter = el('div', { class: 'popover-filter' },
            el('input', { type: 'text', placeholder: 'Filter branches and tags', autofocus: 'true' })
        );
        var hdrB = el('div', { class: 'popover-header', text: 'Branches' });
        var listB = el('div', { class: 'popover-list' });
        var hdrT = el('div', { class: 'popover-header', text: 'Tags' });
        var listT = el('div', { class: 'popover-list' });

        function mkItem(refName) {
            var isActive = (refName === currentRef) ||
                (!currentRef && refName === info.default_branch);
            var item = el('div', { class: 'item' + (isActive ? ' active' : ''), text: refName });
            item.addEventListener('click', function () {
                closePopover();
                location.hash = '#/' + encodeURIComponent(repo);
                // We always navigate to root tree; the SPA reads default_branch
                // (full ref switching across views is a v3 feature).
            });
            return item;
        }

        (info.branches || []).forEach(function (b) { listB.appendChild(mkItem(b.name)); });
        if (!(info.branches || []).length) listB.appendChild(el('div', { class: 'empty', text: 'no branches' }));
        (info.tags || []).forEach(function (t) { listT.appendChild(mkItem(t.name)); });
        if (!(info.tags || []).length) listT.appendChild(el('div', { class: 'empty', text: 'no tags' }));

        // Filter on type
        var filterInput = filter.querySelector('input');
        filterInput.addEventListener('input', function () {
            var q = filterInput.value.toLowerCase();
            [listB, listT].forEach(function (list) {
                list.querySelectorAll('.item').forEach(function (it) {
                    it.style.display = (it.textContent.toLowerCase().indexOf(q) >= 0) ? '' : 'none';
                });
            });
        });

        pop.appendChild(filter);
        pop.appendChild(hdrB);
        pop.appendChild(listB);
        pop.appendChild(hdrT);
        pop.appendChild(listT);
        openPopover(anchorEl, pop);
        setTimeout(function () { filterInput.focus(); }, 50);
    }

    function openCodePopover(repo, anchorEl) {
        var host = location.hostname;
        var sshUrl = 'ssh://' + host + '/mnt/HD/HD_a2/git/' + repo;
        var webUrl = location.origin + '/git/gitweb.cgi?p=' + repo + ';a=summary';

        function row(label, url) {
            var input = el('input', { type: 'text', value: url, readonly: 'true',
                                      onclick: function () { input.select(); } });
            var btn = el('button', { type: 'button', text: 'Copy' });
            btn.addEventListener('click', function () { copyText(url, btn); });
            return el('div', { class: 'row' }, [
                el('div', { class: 'label', text: label }),
                el('div', { class: 'url-input' }, [input, btn])
            ]);
        }
        var body = el('div', { class: 'code-dropdown' }, [
            row('Clone with SSH', sshUrl),
            el('div', { class: 'row' }, [
                el('div', { class: 'label', text: 'Browse' }),
                el('a', { href: webUrl, target: '_blank', class: 'tb-btn', style: 'display:inline-flex;' },
                  'Open in gitweb (legacy)')
            ])
        ]);
        openPopover(anchorEl, body);
    }

    function openGoToFile(repo, ref) {
        api('search', { name: repo, ref: ref }).then(function (res) {
            var paths = res.paths || [];
            var modal = el('div', { class: 'gtf-modal' });
            var input = el('input', { type: 'text', placeholder: 'Type to filter (' + paths.length + ' files)', autofocus: 'true' });
            modal.appendChild(el('div', { class: 'gtf-header' }, input));
            var list = el('div', { class: 'gtf-list' });
            modal.appendChild(list);
            modal.appendChild(el('div', { class: 'gtf-footer', text: '↵ to open  -  ESC to close' }));

            var activeIdx = 0;
            function render(filtered) {
                list.innerHTML = '';
                if (!filtered.length) {
                    list.appendChild(el('div', { class: 'gtf-item', text: 'no matches' }));
                    return;
                }
                activeIdx = Math.min(activeIdx, filtered.length - 1);
                filtered.slice(0, 200).forEach(function (p, i) {
                    var lastSlash = p.lastIndexOf('/');
                    var fname = lastSlash >= 0 ? p.slice(lastSlash + 1) : p;
                    var dir   = lastSlash >= 0 ? p.slice(0, lastSlash) : '';
                    var item = el('div', { class: 'gtf-item' + (i === activeIdx ? ' active' : ''), 'data-idx': i }, [
                        el('span', { class: 'matched', text: fname }),
                        dir ? el('span', { class: 'path', text: dir + '/' }) : null
                    ]);
                    item.addEventListener('click', function () {
                        $('#overlay').classList.add('hidden');
                        $('#overlay').innerHTML = '';
                        location.hash = '#/' + encodeURIComponent(repo) + '/blob/' + encodeURI(p);
                    });
                    list.appendChild(item);
                });
            }

            var filtered = paths.slice();
            render(filtered);

            input.addEventListener('input', function () {
                var q = input.value.trim().toLowerCase();
                activeIdx = 0;
                if (!q) { filtered = paths.slice(); render(filtered); return; }
                // Simple substring filter; prioritize basename matches.
                filtered = paths.filter(function (p) { return p.toLowerCase().indexOf(q) >= 0; });
                filtered.sort(function (a, b) {
                    var aBase = a.split('/').pop().toLowerCase();
                    var bBase = b.split('/').pop().toLowerCase();
                    var ai = aBase.indexOf(q), bi = bBase.indexOf(q);
                    if (ai !== bi) return ai - bi;
                    return a.length - b.length;
                });
                render(filtered);
            });

            input.addEventListener('keydown', function (e) {
                if (e.key === 'ArrowDown') {
                    activeIdx = Math.min(activeIdx + 1, filtered.length - 1);
                    render(filtered);
                    var act = list.querySelector('.gtf-item.active');
                    if (act) act.scrollIntoView({ block: 'nearest' });
                    e.preventDefault();
                } else if (e.key === 'ArrowUp') {
                    activeIdx = Math.max(activeIdx - 1, 0);
                    render(filtered);
                    var act = list.querySelector('.gtf-item.active');
                    if (act) act.scrollIntoView({ block: 'nearest' });
                    e.preventDefault();
                } else if (e.key === 'Enter') {
                    if (filtered[activeIdx]) {
                        $('#overlay').classList.add('hidden');
                        $('#overlay').innerHTML = '';
                        location.hash = '#/' + encodeURIComponent(repo) + '/blob/' + encodeURI(filtered[activeIdx]);
                    }
                    e.preventDefault();
                }
            });

            openOverlay(modal);
            setTimeout(function () { input.focus(); }, 50);
        }).catch(function (err) {
            alert('Search failed: ' + (err.message || err));
        });
    }

    function renderLatestCommitStrip(repo, head, totalCommits) {
        if (!head || !head.hash) return null;
        var initial = (head.author || '?').trim().charAt(0).toUpperCase();
        var strip = el('div', { class: 'latest-commit' }, [
            el('span', { class: 'avatar', text: initial }),
            el('span', { class: 'author', text: head.author || '' }),
            el('span', { class: 'msg', text: head.subject || '' }),
            el('span', { class: 'hash-pill', text: (head.hash || '').slice(0, 7) }),
            el('span', { class: 'time', text: relTime(head.date) }),
            el('a', {
                class: 'commits-link',
                href: '#/' + encodeURIComponent(repo) + '/commits',
                text: (totalCommits || 0) + ' Commits'
            })
        ]);
        return strip;
    }

    function renderTreeV2(repo, ref, path, entries, opts) {
        opts = opts || {};
        var wrap = el('div');

        // path crumbs
        var crumbs = el('div', { class: 'path-crumbs' });
        crumbs.appendChild(el('a', { href: '#/' + encodeURIComponent(repo) }, repo.replace(/\.git$/, '')));
        if (path) {
            var so_far = '';
            path.split('/').forEach(function (seg) {
                if (!seg) return;
                so_far = so_far ? so_far + '/' + seg : seg;
                crumbs.appendChild(el('span', { class: 'sep', text: '/' }));
                crumbs.appendChild(el('a', {
                    href: '#/' + encodeURIComponent(repo) + '/tree/' + encodeURI(so_far)
                }, seg));
            });
        }
        var toolbar = el('div', { class: 'tree-toolbar' }, [
            crumbs,
            el('span', { class: 'count-pill', text: entries.length + ' items' })
        ]);
        wrap.appendChild(toolbar);

        var tree = el('div', { class: 'tree' });

        entries.sort(function (a, b) {
            if (a.type !== b.type) return a.type === 'tree' ? -1 : 1;
            return a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
        });

        if (path) {
            var parent = path.split('/').slice(0, -1).join('/');
            var parentHref = '#/' + encodeURIComponent(repo)
                + (parent ? '/tree/' + encodeURI(parent) : '');
            tree.appendChild(renderTreeRow({
                name: '..', type: 'tree', size: null, last_commit: null,
                href: parentHref
            }));
        }
        entries.forEach(function (e) {
            var entryPath = path ? path + '/' + e.name : e.name;
            var action = e.type === 'tree' ? 'tree' : 'blob';
            var href = '#/' + encodeURIComponent(repo) + '/' + action + '/' + encodeURI(entryPath);
            e.href = href;
            tree.appendChild(renderTreeRow(e));
        });
        wrap.appendChild(tree);
        return wrap;
    }

    function renderTreeRow(entry) {
        var iconCls = entry.type === 'tree' ? 'icon dir' : 'icon';
        var iconChar = entry.type === 'tree' ? '▸' : ' ';  // ▸
        var icon = el('span', { class: iconCls, text: iconChar });

        var name = el('div', { class: 'name' },
            el('a', { href: entry.href, text: entry.name })
        );

        var lastMsg;
        if (entry.last_commit && entry.last_commit.subject) {
            lastMsg = el('div', { class: 'last-msg' }, [
                el('span', { text: entry.last_commit.subject })
            ]);
        } else {
            lastMsg = el('div', { class: 'last-msg', text: entry.size != null ? fmtBytes(entry.size) : '' });
        }

        var timeText = entry.last_commit && entry.last_commit.ts
            ? relTime(entry.last_commit.ts)
            : '';
        var time = el('div', { class: 'time', text: timeText });

        return el('div', { class: 'row' }, [icon, name, lastMsg, time]);
    }

    function renderAboutSidebar(repo, info, langs) {
        var aside = el('aside', { class: 'repo-sidebar' });

        // About section
        var about = el('div', { class: 'about-section' });
        about.appendChild(el('h3', { text: 'About' }));
        if (info.description) {
            about.appendChild(el('p', { class: 'desc', text: info.description }));
        } else {
            about.appendChild(el('p', { class: 'desc', html: '<em style="color:var(--ink-faint);">No description provided</em>' }));
        }
        if (info.readme) {
            about.appendChild(el('div', { class: 'about-badge' }, [
                el('span', { class: 'glyph', text: '§' }),  // §
                el('a', {
                    href: '#/' + encodeURIComponent(repo) + '/blob/' + encodeURI(info.readme.path),
                    text: info.readme.path
                })
            ]));
        }
        if (info.license_path) {
            about.appendChild(el('div', { class: 'about-badge' }, [
                el('span', { class: 'glyph', text: '©' }),  // ©
                el('a', {
                    href: '#/' + encodeURIComponent(repo) + '/blob/' + encodeURI(info.license_path),
                    text: info.license_path
                })
            ]));
        }
        about.appendChild(el('div', { class: 'about-badge' }, [
            el('span', { class: 'glyph', text: '⧖' }),  // hourglass-ish
            el('a', {
                href: '#/' + encodeURIComponent(repo) + '/commits',
                text: (info.total_commits || 0) + ' commits'
            })
        ]));
        if (info.head && info.head.date) {
            about.appendChild(el('div', { class: 'about-badge' }, [
                el('span', { class: 'glyph', text: '⧗' }),
                el('span', { text: 'Updated ' + relTime(info.head.date) })
            ]));
        }
        aside.appendChild(about);

        // Languages section
        if (langs && langs.total > 0) {
            var langSection = el('div', { class: 'about-section' });
            langSection.appendChild(el('h3', { text: 'Languages' }));

            var entries = [];
            for (var k in langs.extensions) {
                entries.push({ ext: k, bytes: langs.extensions[k] });
            }
            entries.sort(function (a, b) { return b.bytes - a.bytes; });
            // collapse small slices into "Other"
            var visible = [];
            var otherBytes = 0;
            entries.forEach(function (e) {
                var pct = e.bytes / langs.total * 100;
                if (visible.length < 6 && pct >= 0.5) {
                    visible.push(e);
                } else {
                    otherBytes += e.bytes;
                }
            });
            if (otherBytes > 0) {
                visible.push({ ext: '__other', bytes: otherBytes, _other: true });
            }

            var bar = el('div', { class: 'lang-bar' });
            visible.forEach(function (e) {
                var info = e._other ? { name: 'Other', color: '#8c6b52' } : langInfo(e.ext);
                var pct = e.bytes / langs.total * 100;
                var seg = el('div', { class: 'seg' });
                seg.style.width      = pct + '%';
                seg.style.background = info.color;
                seg.title = info.name + ' - ' + pct.toFixed(1) + '%';
                bar.appendChild(seg);
            });
            langSection.appendChild(bar);

            var legend = el('div', { class: 'lang-legend' });
            visible.forEach(function (e) {
                var info = e._other ? { name: 'Other', color: '#8c6b52' } : langInfo(e.ext);
                var pct = e.bytes / langs.total * 100;
                var dot = el('span', { class: 'dot' });
                dot.style.background = info.color;
                legend.appendChild(el('div', { class: 'item' }, [
                    dot,
                    el('span', { class: 'name', text: info.name }),
                    el('span', { class: 'pct', text: pct.toFixed(1) + '%' })
                ]));
            });
            langSection.appendChild(legend);
            aside.appendChild(langSection);
        }

        return aside;
    }

    // -----------------------------------------------------------------
    // Router
    // -----------------------------------------------------------------

    function parseRoute() {
        var hash = location.hash || '#/';
        if (hash.charAt(0) !== '#') hash = '#' + hash;
        var path = hash.slice(1);
        if (path.charAt(0) !== '/') path = '/' + path;
        var parts = path.slice(1).split('/').map(decodeURIComponent);
        if (parts.length === 0 || parts[0] === '') return { view: 'home' };
        var repo = parts[0];
        var action = parts[1] || 'home';
        var rest = parts.slice(2).join('/');
        return { view: action, repo: repo, path: rest };
    }

    function renderCrumbs(route) {
        var c = $('#crumbs');
        c.innerHTML = '';
        if (route.view === 'home' && !route.repo) return;
        c.appendChild(el('span', { class: 'sep', text: '/' }));
        c.appendChild(el('a', { href: '#/' + encodeURIComponent(route.repo) }, route.repo));
        if (route.view !== 'home' && route.view) {
            c.appendChild(el('span', { class: 'sep', text: '/' }));
            c.appendChild(el('span', null, route.view));
        }
    }

    // -----------------------------------------------------------------
    // Views
    // -----------------------------------------------------------------

    function viewHome() {
        showLoading();
        api('repos').then(function (repos) {
            $('#app').innerHTML = '';
            if (!repos.length) {
                $('#app').appendChild(el('div', { class: 'empty', text: 'No repos found.' }));
                return;
            }
            repos.sort(function (a, b) {
                return (parseGitDate(b.last_commit_at) || 0) - (parseGitDate(a.last_commit_at) || 0);
            });
            var grid = el('div', { class: 'repo-grid' });
            repos.forEach(function (r) {
                var card = el('div', { class: 'repo-card', 'data-name': r.name, 'data-desc': r.description || '' });
                card.appendChild(el('a', {
                    class: 'title',
                    href: '#/' + encodeURIComponent(r.name)
                }, r.name.replace(/\.git$/, '')));
                card.appendChild(el('div', { class: 'desc' }, r.description || el('em', { text: 'no description' })));
                var meta = el('div', { class: 'meta' });
                meta.appendChild(el('div', { class: 'commit-info', text:
                    r.last_commit_subject
                        ? r.last_commit_author + ' - ' + relTime(r.last_commit_at)
                        : 'no commits' }));
                meta.appendChild(el('span', { class: 'badge', text: r.commit_count + ' commits' }));
                meta.appendChild(el('span', { class: 'badge', text: fmtBytes(r.size_bytes) }));
                card.appendChild(meta);
                grid.appendChild(card);
            });
            $('#app').appendChild(grid);
            applySearchFilter();
        }).catch(showError);
    }

    function applySearchFilter() {
        var q = ($('#search-input').value || '').toLowerCase().trim();
        document.querySelectorAll('.repo-card').forEach(function (card) {
            var name = (card.getAttribute('data-name') || '').toLowerCase();
            var desc = (card.getAttribute('data-desc') || '').toLowerCase();
            card.style.display = (!q || name.indexOf(q) >= 0 || desc.indexOf(q) >= 0) ? '' : 'none';
        });
    }

    function renderRepoHeader(repo, info, activeTab) {
        $('#app').innerHTML = '';

        var header = el('div', { class: 'repo-header' });
        header.appendChild(el('h1', { text: repo.replace(/\.git$/, '') }));
        if (info.description) {
            header.appendChild(el('p', { class: 'repo-desc', text: info.description }));
        }
        $('#app').appendChild(header);

        var nB = (info.branches || []).length, nT = (info.tags || []).length;
        function tab(name, label, count) {
            var a = el('a', {
                href: '#/' + encodeURIComponent(repo) + (name === 'code' ? '' : '/' + name),
                class: name === activeTab ? 'active' : ''
            }, [label]);
            if (count != null) a.appendChild(el('span', { class: 'count', text: '(' + count + ')' }));
            return a;
        }
        var tabs = el('nav', { class: 'tabs' }, [
            tab('code', 'Code'),
            tab('commits', 'Commits'),
            tab('refs', 'Branches', nB + nT)
        ]);
        $('#app').appendChild(tabs);
    }

    // ---- Code tab (repo home or any tree path) ----
    function viewCode(route, isRoot) {
        showLoading();
        var path = route.path || '';

        // Single fast fetch first: repo metadata + (optionally) README content.
        // Tree-with-last-commits and languages are slow on ARMv5 — defer them
        // and overlay incrementally so the header/toolbar/README appear immediately.
        api('repo', { name: route.repo, include_readme: isRoot ? 1 : '' })
        .then(function (info) {
            renderRepoHeader(route.repo, info, 'code');

            var layout = el('div', { class: 'repo-layout' });
            var main   = el('div', { class: 'repo-main' });
            var aside  = renderAboutSidebar(route.repo, info, null);  // langs added later

            main.appendChild(renderCodeToolbar(route.repo, info, info.default_branch));

            if (!path && info.head) {
                var strip = renderLatestCommitStrip(route.repo, info.head, info.total_commits);
                if (strip) main.appendChild(strip);
            }

            // Tree placeholder - swapped in once treelog.cgi returns.
            var treeSlot = el('div', { class: 'loading', text: 'Loading files...' });
            main.appendChild(treeSlot);

            // README only rendered when content was included (= isRoot path).
            if (!path && info.readme && info.readme.content) {
                main.appendChild(renderReadme(info.readme));
            }

            layout.appendChild(main);
            layout.appendChild(aside);
            $('#app').appendChild(layout);

            // Tree + per-file last commit (heaviest of the two slow fetches).
            api('treelog', { name: route.repo, ref: '', path: path })
                .then(function (tree) {
                    var treeEl = renderTreeV2(route.repo, info.default_branch, path, tree.entries);
                    treeSlot.replaceWith(treeEl);
                })
                .catch(function (err) {
                    treeSlot.replaceWith(el('div', { class: 'error-box',
                        text: 'Failed to load files: ' + (err.message || err) }));
                });

            // Languages chart (cached server-side keyed on HEAD - hits are fast).
            if (isRoot) {
                api('languages', { name: route.repo })
                    .then(function (langs) {
                        var newAside = renderAboutSidebar(route.repo, info, langs);
                        aside.replaceWith(newAside);
                        aside = newAside;  // keep handle in case we re-replace
                    })
                    .catch(function () { /* ignore: sidebar still works without langs */ });
            }
        })
        .catch(showError);
    }

    function viewRepo(route) { viewCode(route, true); }
    function viewTree(route) { viewCode(route, false); }

    function renderReadme(readme) {
        var wrap = el('div', { class: 'readme' });
        wrap.appendChild(el('div', { class: 'readme-title', text: readme.path }));
        wrap.appendChild(el('div', { class: 'readme-body', html: renderMarkdown(readme.content) }));
        return wrap;
    }

    function viewBlob(route) {
        showLoading();
        var path = route.path || '';
        api('repo', { name: route.repo }).then(function (info) {
            renderRepoHeader(route.repo, info, 'code');

            var layout = el('div', { class: 'repo-layout' });
            var main = el('div', { class: 'repo-main' });
            var aside = renderAboutSidebar(route.repo, info, null);
            main.appendChild(renderCodeToolbar(route.repo, info, info.default_branch));

            var qs = '?name=' + encodeURIComponent(route.repo)
                   + '&ref=' + encodeURIComponent(info.default_branch)
                   + '&path=' + encodeURIComponent(path);
            fetch(API + 'blob.cgi' + qs, { cache: 'no-store' }).then(function (r) {
                var ct = r.headers.get('Content-Type') || '';
                if (ct.indexOf('application/json') >= 0) {
                    return r.json().then(function (j) {
                        var msg = j.error === 'binary blob'
                            ? 'Binary file (' + fmtBytes(j.size) + ') - cannot display inline.'
                            : ('Error: ' + j.error);
                        main.appendChild(el('div', { class: 'error-box', text: msg }));
                    });
                }
                return r.text().then(function (text) {
                    var pathCrumbs = el('div', { class: 'path-crumbs' });
                    pathCrumbs.appendChild(el('a', { href: '#/' + encodeURIComponent(route.repo), text: route.repo.replace(/\.git$/, '') }));
                    var sofar = '';
                    var segs = path.split('/');
                    segs.forEach(function (seg, i) {
                        sofar = sofar ? sofar + '/' + seg : seg;
                        pathCrumbs.appendChild(el('span', { class: 'sep', text: '/' }));
                        if (i === segs.length - 1) {
                            pathCrumbs.appendChild(el('span', { text: seg }));
                        } else {
                            pathCrumbs.appendChild(el('a', {
                                href: '#/' + encodeURIComponent(route.repo) + '/tree/' + encodeURI(sofar),
                                text: seg
                            }));
                        }
                    });
                    main.appendChild(el('div', { class: 'blob-toolbar' }, [
                        pathCrumbs,
                        el('span', { class: 'blob-meta', text: fmtBytes(text.length) + ' - ' + text.split('\n').length + ' lines' })
                    ]));
                    main.appendChild(el('pre', { class: 'blob-content', text: text }));
                });
            }).then(function () {
                layout.appendChild(main);
                layout.appendChild(aside);
                $('#app').appendChild(layout);
            });
        }).catch(showError);
    }

    function viewCommits(route) {
        showLoading();
        Promise.all([
            api('repo',    { name: route.repo }),
            api('commits', { name: route.repo, ref: '', limit: 100 })
        ]).then(function (results) {
            var info = results[0], res = results[1];
            renderRepoHeader(route.repo, info, 'commits');

            var layout = el('div', { class: 'repo-layout' });
            var main = el('div', { class: 'repo-main' });
            main.appendChild(renderCodeToolbar(route.repo, info, info.default_branch));

            var list = el('div', { class: 'commit-list' });
            if (!res.commits.length) {
                list.appendChild(el('div', { class: 'commit', text: 'no commits' }));
            } else {
                res.commits.forEach(function (c) {
                    var subj = el('div', { class: 'subject' });
                    subj.appendChild(el('div', { class: 'line1', text: c.subject }));
                    subj.appendChild(el('div', { class: 'line2',
                        text: c.author + ' - ' + relTime(c.date) + ' (' + (c.date || '?') + ')' }));
                    list.appendChild(el('div', { class: 'commit' }, [
                        subj,
                        el('span', { class: 'hash-pill', text: c.short })
                    ]));
                });
            }
            main.appendChild(list);

            layout.appendChild(main);
            layout.appendChild(renderAboutSidebar(route.repo, info, null));
            $('#app').appendChild(layout);
        }).catch(showError);
    }

    function viewRefs(route) {
        showLoading();
        api('repo', { name: route.repo }).then(function (info) {
            renderRepoHeader(route.repo, info, 'refs');

            var layout = el('div', { class: 'repo-layout' });
            var main = el('div', { class: 'repo-main' });
            main.appendChild(renderCodeToolbar(route.repo, info, info.default_branch));

            var section = function (title, refs, isBranch) {
                var box = el('div');
                box.appendChild(el('h3', {
                    text: title,
                    style: 'color:var(--ink-dim);font-size:13px;margin:20px 0 8px;'
                }));
                if (!refs.length) {
                    box.appendChild(el('div', { class: 'empty', text: 'none' }));
                    return box;
                }
                var list = el('div', { class: 'ref-list' });
                refs.forEach(function (r) {
                    var nameEl = el('div', {
                        class: 'name' + (isBranch && r.name === info.default_branch ? ' default' : ''),
                        text: r.name
                    });
                    list.appendChild(el('div', { class: 'ref-row' }, [
                        nameEl,
                        el('div', { class: 'commit-info', text: r.subject + ' - ' + r.author + ' - ' + relTime(r.date) }),
                        el('span', { class: 'hash-pill', text: r.hash.slice(0, 7) })
                    ]));
                });
                box.appendChild(list);
                return box;
            };
            main.appendChild(section('Branches', info.branches || [], true));
            main.appendChild(section('Tags',     info.tags     || [], false));

            layout.appendChild(main);
            layout.appendChild(renderAboutSidebar(route.repo, info, null));
            $('#app').appendChild(layout);
        }).catch(showError);
    }

    // -----------------------------------------------------------------
    // Dispatch
    // -----------------------------------------------------------------

    var ROUTES = {
        'home':    viewRepo,
        'tree':    viewTree,
        'blob':    viewBlob,
        'commits': viewCommits,
        'refs':    viewRefs
    };

    function dispatch() {
        closePopover();
        var route = parseRoute();
        renderCrumbs(route);
        if (route.view === 'home' && !route.repo) {
            viewHome();
        } else {
            var fn = ROUTES[route.view];
            if (fn) fn(route);
            else showError(new Error('unknown route: ' + route.view));
        }
        window.scrollTo(0, 0);
    }

    document.addEventListener('DOMContentLoaded', function () {
        $('#search-input').addEventListener('input', function () {
            var route = parseRoute();
            if (route.view !== 'home' || route.repo) location.hash = '#/';
            applySearchFilter();
        });

        // Global keyboard shortcut: "t" opens Go-to-file when viewing a repo.
        document.addEventListener('keydown', function (e) {
            if (e.key === 't' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                var route = parseRoute();
                if (route.repo) {
                    e.preventDefault();
                    openGoToFile(route.repo, '');
                }
            }
        });
    });

    window.addEventListener('hashchange', dispatch);
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', dispatch);
    } else {
        dispatch();
    }
})();
