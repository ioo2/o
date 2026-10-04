const cat = typeof js2Proxy === 'function' && typeof desX === 'function' && typeof getProxy !== 'function';
const C = {
    host: 'http://cms.lyyytv.cn',
    parseMap: {
        'lyyytv.cn': 'http://fys.lyyytv.cn/api/index?parsesId=3&appid=10001&videoUrl=',
        '*': 'http://fys.lyyytv.cn/api/index?parsesId=3&appid=10001&videoUrl='
    },
    token: '',
    key: '',
    initUrl: '',
    keyTried: false,
    playCache: {},
    size: 12,
    searchSize: 10,
    homeCount: 60
};
const H = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9'
};
const PH = {
    'User-Agent': 'okhttp/4.12.0',
    'Accept-Encoding': 'identity'
};
function parseExt(s) {
    if (!s) return {};
    if (typeof s === 'object') return s;
    try { return JSON.parse(s); } catch (e) { return {}; }
}
function mapItem(it) {
    const v = {};
    v.vod_id = String(it.vod_id != null ? it.vod_id : '');
    v.vod_name = String(it.vod_name || '').trim();
    v.vod_pic = it.vod_pic || '';
    v.vod_remarks = it.vod_remarks || '';
    return v;
}
function splitEpisodeList(playStr) {
    const s = String(playStr || '').replace(/#+$/, '');
    const epsOut = [];
    const eps = s.split('#');
    for (const ep of eps) {
        const p = ep.indexOf('$');
        if (p < 0) {
            epsOut.push({ epName: '', rawUrl: ep });
        } else {
            epsOut.push({ epName: ep.slice(0, p), rawUrl: ep.slice(p + 1) });
        }
    }
    return epsOut;
}
function joinEpisodeList(epList) {
    return epList.map(e => (e.epName || '') + '$' + e.rawUrl).join('#');
}
async function getApi(path, pairs) {
    let q = '';
    if (C.token) q = 'token=' + encodeURIComponent(C.token);
    let first = q.length === 0;
    for (const k in pairs) {
        if (pairs[k] === undefined || pairs[k] === null || pairs[k] === '') continue;
        q += (first ? '' : '&') + k + '=' + encodeURIComponent(String(pairs[k]));
        first = false;
    }
    const url = C.host + path + (q ? '?' + q : '');
    let resp = null;
    try { resp = await req(url, { headers: H }); } catch (e) { return null; }
    if (!resp || String(resp.code) !== '200' || !resp.content) return null;
    let j = null;
    try { j = JSON.parse(resp.content); } catch (e) { return null; }
    if (!j || j.code !== 1) return null;
    if (j && j.data && j.data.token) C.token = String(j.data.token);
    else if (j && j.token) C.token = String(j.token);
    return j;
}
async function getIndex() {
    const j = await getApi('/api.php/app/index_video', {});
    return j || { data: {} };
}
async function getNav() {
    const j = await getApi('/api.php/app/nav', {});
    return j || { list: [] };
}
const FILTER_DEFS = [
    { key: 'class', name: '类型' },
    { key: 'area', name: '地区' },
    { key: 'lang', name: '语言' },
    { key: 'year', name: '年份' }
];
function strToFilter(str) {
    const items = (str || '').split(',').map(s => s.trim()).filter(Boolean);
    const value = [{ n: '全部', v: 'all' }];
    for (const it of items) value.push({ n: it, v: it });
    return value;
}
function buildFilters(navList) {
    const filters = {};
    if (!Array.isArray(navList)) return filters;
    for (const c of navList) {
        const te = c.type_extend;
        if (!te) continue;
        const arr = [];
        for (const def of FILTER_DEFS) {
            if (te[def.key]) {
                arr.push({ key: def.key, name: def.name, init: 'all', value: strToFilter(te[def.key]) });
            }
        }
        if (arr.length) filters[String(c.type_id)] = arr;
    }
    return filters;
}
function decInitBody(body) {
    let s = String(body || '').replace(/\\/g, '').replace(/"/g, '');
    if (s.length <= 16) return '';
    const k = s.slice(0, 16);
    const cipher = s.slice(16);
    try {
        return aesX('AES/CBC/PKCS7', false, cipher, true, k, k, false);
    } catch (e) {
        return '';
    }
}
function pickMaccmsKey(plain) {
    if (!plain) return '';
    const m = plain.match(/"maccms_key"\s*:\s*"([^"]*)"/);
    if (m && m[1]) return m[1];
    try {
        const j = JSON.parse(plain);
        const sc = j && j.data && j.data.siteConfig;
        if (sc && sc.maccms_key) return String(sc.maccms_key);
    } catch (e) { }
    return '';
}
async function ensureKey() {
    if (C.key) return C.key;
    if (C.keyTried || !C.initUrl) return '';
    C.keyTried = true;
    try {
        const resp = await req(C.initUrl, { headers: PH });
        if (resp && resp.content) {
            const plain = decInitBody(resp.content);
            const k = pickMaccmsKey(plain);
            if (k) C.key = k;
        }
    } catch (e) { }
    return C.key;
}
function decUrlOne(u) {
    const s = String(u || '');
    if (s.indexOf('lvdou+') !== 0) return s;
    if (!C.key) return s;
    const cipher = s.slice('lvdou+'.length);
    const k = C.key.slice(0, 16);
    const iv = C.key.length >= 32 ? C.key.slice(16, 32) : k;
    try {
        const d = aesX('AES/CBC/PKCS7', false, cipher, true, k, iv, false);
        if (d && d.indexOf('http') === 0) return d.trim();
    } catch (e) { }
    return s;
}
function decPlayUrl(raw) {
    let s = String(raw || '').replace(/#+$/, '');
    if (!s) return '';
    const eps = s.split('#');
    const out = [];
    for (const ep of eps) {
        const p = ep.indexOf('$');
        if (p < 0) { out.push(decUrlOne(ep)); continue; }
        out.push(ep.slice(0, p + 1) + decUrlOne(ep.slice(p + 1)));
    }
    return out.join('#');
}
const DEC_PREFIX = 'https://baidu.con/';
function findUrl(j) {
    if (!j || typeof j !== 'object') return '';
    if (j.url) return j.url;
    if (j.data && j.data.url) return j.data.url;
    if (j.playUrl) return j.playUrl;
    if (j.link) return j.link;
    return '';
}
function resolveParse(body) {
    body = String(body || '').trim();
    if (!body) return '';
    let candidate = body;
    if (body.charAt(0) === '{') {
        try {
            const j = JSON.parse(body);
            const u = findUrl(j);
            if (u) candidate = String(u).trim();
        } catch (e) { }
    }
    if (candidate.indexOf(DEC_PREFIX) === 0) {
        const rest = candidate.slice(DEC_PREFIX.length);
        if (rest.length > 16) {
            const key = rest.slice(0, 16);
            const cipher = rest.slice(16);
            try {
                const dec = aesX('AES/CBC/PKCS7', false, cipher, true, key, key, false);
                if (dec && dec.indexOf('http') === 0) return dec.trim();
            } catch (e) { }
            try {
                const dec2 = aesX('AES/CBC/PKCS7', false, cipher, false, key, key, false);
                if (dec2 && dec2.indexOf('http') === 0) return dec2.trim();
            } catch (e) { }
        }
        return '';
    }
    return candidate;
}
function normParseBase(p) {
    let s = String(p || '').trim();
    if (!s) return '';
    if (s.indexOf('videoUrl=') < 0) {
        s = s.replace(/\/?$/, '') + (s.indexOf('?') < 0 ? '?videoUrl=' : '&videoUrl=');
    }
    return s;
}
function pickParses(raw) {
    const pm = C.parseMap;
    if (typeof pm === 'string') return [normParseBase(pm)];
    if (!pm || typeof pm !== 'object') return [];
    const host = (String(raw).match(/^https?:\/\/([^\/?#]+)/i) || [, ''])[1].toLowerCase();
    const hits = [];
    let fallback = null;
    for (const key in pm) {
        const rule = String(key).trim();
        if (rule === '' || rule === '*') { fallback = pm[key]; continue; }
        const frags = rule.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
        if (frags.some(f => host && host.indexOf(f) >= 0)) hits.push(pm[key]);
    }
    const chosen = hits.length ? hits : (fallback !== null ? [fallback] : []);
    const bases = [];
    for (const v of chosen) {
        if (Array.isArray(v)) {
            for (const x of v) { const b = normParseBase(x); if (b) bases.push(b); }
        } else {
            const b = normParseBase(v); if (b) bases.push(b);
        }
    }
    return bases;
}
async function init(cfg) {
    try {
        const ext = cfg && (cfg.ext !== undefined ? cfg.ext : cfg);
        const e = parseExt(ext);
        if (e.host) C.host = String(e.host).replace(/\/+$/, '');
        if (e.parse !== undefined && e.parse !== null && e.parse !== '') {
            C.parseMap = e.parse;
        }
        if (e.key) C.key = String(e.key).trim();
        if (e.init) C.initUrl = String(e.init).trim();
        C.keyTried = false;
        C.playCache = {};
    } catch (e) { }
}
async function home() {
    const j = await getNav();
    const classes = [];
    if (j && Array.isArray(j.list)) {
        for (let i = 0; i < j.list.length; i++) {
            const c = j.list[i];
            if (c && c.type_id != null) {
                classes.push({ type_id: String(c.type_id), type_name: String(c.type_name || '') });
            }
        }
    }
    if (cat) classes.unshift({ type_id: 'home', type_name: '首页' });

    const nameMap = {
        "最新电影": "电影",
        "热播国剧": "电视剧",
        "国漫": "动漫",
        "国综": "综艺"
    };
    let filteredClasses = classes.filter(item => nameMap.hasOwnProperty(item.type_name));
    filteredClasses = filteredClasses.map(item => {
        return {
            type_id: item.type_id,
            type_name: nameMap[item.type_name]
        }
    });

    const filters = buildFilters(j && j.list);
    return JSON.stringify({ class: filteredClasses, filters: filters });
}
async function homeVod() {
    const j = await getIndex();
    const list = [];
    const seen = {};
    if (j && Array.isArray(j.list)) {
        for (let i = 0; i < j.list.length && list.length < C.homeCount; i++) {
            const c = j.list[i];
            if (c && Array.isArray(c.vlist)) {
                for (let k = 0; k < c.vlist.length && list.length < C.homeCount; k++) {
                    const it = c.vlist[k];
                    const id = String(it.vod_id != null ? it.vod_id : '');
                    if (id && seen[id]) continue;
                    if (id) seen[id] = 1;
                    list.push(mapItem(it));
                }
            }
        }
    }
    return JSON.stringify({ list: list });
}
async function category(tid, pg, filter, extend) {
    pg = parseInt(pg) || 1;
    if (String(tid) === 'home') {
        const d = JSON.parse(await homeVod());
        return JSON.stringify({ list: d.list || [], page: 1, pagecount: 1 });
    }
    const params = { tid: String(tid), pg: String(pg) };
    if (extend && typeof extend === 'object') {
        for (const def of FILTER_DEFS) {
            const v = extend[def.key];
            if (v && v !== 'all') params[def.key] = String(v);
        }
    }
    const j = await getApi('/api.php/app/video', params);
    if (j && Array.isArray(j.list)) {
        const list = [];
        for (let i = 0; i < j.list.length; i++) list.push(mapItem(j.list[i]));
        let pagecount = parseInt(j.pagecount) || 0;
        if (!pagecount) pagecount = list.length >= C.size ? pg + 1 : pg;
        return JSON.stringify({ list: list, page: pg, pagecount: pagecount });
    }
    return JSON.stringify({ list: [], page: pg, pagecount: 1 });
}
async function search(wd, quick, pg = 1) {
    pg = parseInt(pg) || 1;
    const j = await getApi('/api.php/app/search', { text: wd, pg: String(pg) });
    const list = [];
    if (j && Array.isArray(j.list)) {
        for (let i = 0; i < j.list.length; i++) list.push(mapItem(j.list[i]));
    }
    const pagecount = list.length >= C.searchSize ? pg + 1 : pg;
    return JSON.stringify({ list: list, page: pg, pagecount: pagecount });
}
async function detail(id) {
    const j = await getApi('/api.php/app/video_detail', { id: String(id) });
    const list = [];
    if (j && j.data) {
        const d = j.data;
        const vod = {};
        vod.vod_id = String(d.vod_id != null ? d.vod_id : id);
        vod.vod_name = String(d.vod_name || '').trim();
        vod.vod_pic = d.vod_pic || '';
        vod.vod_content = String(d.vod_content || '');
        vod.vod_actor = d.vod_actor || '';
        vod.vod_director = d.vod_director || '';
        vod.vod_area = d.vod_area || '';
        vod.vod_lang = d.vod_lang || '';
        const yr = parseInt(d.vod_year);
        vod.vod_year = isNaN(yr) ? '' : yr;
        vod.vod_class = d.vod_class || '';
        vod.vod_remarks = d.vod_remarks || '';
        vod._innerLines = [];
        if (Array.isArray(d.vod_url_with_player) && d.vod_url_with_player.length) {
            const needKey = d.vod_url_with_player.some(it => it && String(it.url || '').indexOf('lvdou+') >= 0);
            if (needKey) await ensureKey();
            for (const it of d.vod_url_with_player) {
                if (!it) continue;
                const nm = it.name != null ? String(it.name) : '';
                const cd = it.code != null ? String(it.code) : '';
                const rawUrl = decPlayUrl(it.url != null ? it.url : '');
                vod._innerLines.push({ name: nm, code: cd, url: rawUrl });
            }
            const firstLine = vod._innerLines[0];
            vod.vod_play_from = "恒轩";
            vod.vod_play_url = firstLine ? firstLine.url : "";
        } else {
            if (String(d.vod_play_url || '').indexOf('lvdou+') >= 0) await ensureKey();
            const fromRaw = String(d.vod_play_from || '');
            const urlRaw = String(d.vod_play_url || '');
            const fromArr = fromRaw.split('$$$');
            const urlArr = urlRaw.split('$$$');
            for(let idx=0;idx<fromArr.length;idx++){
                vod._innerLines.push({name:fromArr[idx],code:'',url:decPlayUrl(urlArr[idx]||'')});
            }
            vod.vod_play_from = "恒轩";
            vod.vod_play_url = vod._innerLines.length>0 ? vod._innerLines[0].url : "";
        }
        list.push(vod);
    }
    return JSON.stringify({ list: list });
}
const PLAY_ROUNDS = 3;
const PLAY_BACKOFF = 350;
const PLAY_CACHE_TTL = 120000;
function sleep(ms) {
    return new Promise(resolve => { try { setTimeout(resolve, ms); } catch (e) { resolve(); } });
}
async function play(flag, id, flags) {
    const rawInput = String(id || '').trim();
    if (!flags || !flags._innerLines || !Array.isArray(flags._innerLines)) {
        let url = '';
        const cacheKey = rawInput;
        const hit = C.playCache[cacheKey];
        if (hit && hit.url && (Date.now() - hit.ts) < PLAY_CACHE_TTL) {
            return JSON.stringify({ parse: 0, url: hit.url, header: PH });
        }
        const bases = pickParses(rawInput);
        if (bases.length > 0) {
            for (let round = 0; round < PLAY_ROUNDS && !url; round++) {
                if (round > 0) await sleep(round * PLAY_BACKOFF);
                for (let i = 0; i < bases.length; i++) {
                    try {
                        const resp = await req(bases[i] + encodeURIComponent(rawInput), { headers: PH });
                        if (resp && resp.content) {
                            const u = resolveParse(resp.content);
                            if (u && u.indexOf('http') === 0) { url = u; break; }
                        }
                    } catch (e) { }
                }
            }
        }
        if(url) C.playCache[cacheKey]={url:url,ts:Date.now()};
        return JSON.stringify({ parse:0, url:url||'', header:PH });
    }
    const innerLines = [...flags._innerLines];
    let priorityList = [];
    let backupList = [];
    for(const line of innerLines){
        const fullName = (line.name||'') + '-' + (line.code||'');
        if(fullName.includes("联通云")){
            priorityList.push(line);
        }else{
            backupList.push(line);
        }
    }
    const tryLines = priorityList.concat(backupList);
    let finalUrl = '';
    for(const line of tryLines){
        if(!line.url) continue;
        const eps = splitEpisodeList(line.url);
        const targetEp = eps.find(x=>x.rawUrl === rawInput);
        if(!targetEp) continue;
        const cacheKey = rawInput;
        const hit = C.playCache[cacheKey];
        if (hit && hit.url && (Date.now() - hit.ts) < PLAY_CACHE_TTL) {
            finalUrl = hit.url;
            break;
        }
        const bases = pickParses(targetEp.rawUrl);
        if(!bases.length) continue;
        let tmpUrl = '';
        for (let round = 0; round < PLAY_ROUNDS && !tmpUrl; round++) {
            if (round > 0) await sleep(round * PLAY_BACKOFF);
            for (let i = 0; i < bases.length; i++) {
                try {
                    const resp = await req(bases[i] + encodeURIComponent(targetEp.rawUrl), { headers: PH });
                    if (resp && resp.content) {
                        const u = resolveParse(resp.content);
                        if (u && u.indexOf('http') === 0) { tmpUrl = u; break; }
                    }
                } catch (e) { }
            }
        }
        if(tmpUrl){
            finalUrl = tmpUrl;
            C.playCache[cacheKey]={url:finalUrl,ts:Date.now()};
            break;
        }
    }
    return JSON.stringify({ parse:0, url:finalUrl||'', header:PH });
}
export function __jsEvalReturn() {
    return {
        init: init,
        home: home,
        homeVod: homeVod,
        category: category,
        categoryContent: category,
        search: search,
        detail: detail,
        play: play
    };
}
