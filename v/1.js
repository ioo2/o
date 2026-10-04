const cat = typeof js2Proxy === 'function' && typeof desX === 'function' && typeof getProxy !== 'function';
const C = {
    host: 'http://cms.lyyytv.cn',
    token: '',
    key: '',
    initUrl: '',
    keyTried: false,
    playCache: {},
    size: 12,
    searchSize: 10,
    homeCount: 60,
    resolveApi:"http://127.0.0.1:8000/resolve"
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
    let remark = String(it.vod_remarks || '');
    remark = remark.replace(/4K|蓝光|更新|高清/g, '').replace(/[★◆☆※#$■●]/g, '').replace(/\s+/g, ' ').trim();
    v.vod_remarks = remark;
    return v;
}
function splitEpisodeList(playStr) {
    const s = String(playStr || '').replace(/#+$/, '');
    const epsOut = [];
    const eps = s.split('#');
    for (const ep of eps) {
        const p = ep.indexOf('$');
        let epName = '';
        let rawUrl = ep;
        if (p >= 0) {
            epName = ep.slice(0, p);
            rawUrl = ep.slice(p + 1);
        }
        epName = epName.replace(/-?4K|-?蓝光|-?高清/g, '').replace(/[★◆☆※#$■●_-]/g, '').replace(/\s+/g, ' ').trim();
        epsOut.push({ epName: epName, rawUrl: rawUrl });
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
async function init(cfg) {
    try {
        const ext = cfg && (cfg.ext !== undefined ? cfg.ext : cfg);
        const e = parseExt(ext);
        if (e.host) C.host = String(e.host).replace(/\/+$/, '');
        if(e.resolveApi) C.resolveApi = e.resolveApi;
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
        "首页": "首页",
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
        let dr = String(d.vod_remarks || '');
        dr = dr.replace(/4K|蓝光|更新|高清/g, '').replace(/[★◆☆※#$■●_-]/g, '').replace(/\s+/g, ' ').trim();
        vod.vod_remarks = dr;
        vod._innerLines = [];
        if (Array.isArray(d.vod_url_with_player) && d.vod_url_with_player.length) {
            for (const it of d.vod_url_with_player) {
                if (!it) continue;
                const nm = it.name != null ? String(it.name) : '';
                const cd = it.code != null ? String(it.code) : '';
                const rawUrl = it.url != null ? it.url : '';
                vod._innerLines.push({ name: nm, code: cd, url: rawUrl });
            }
            const firstLine = vod._innerLines[0];
            vod.vod_play_from = "恒轩";
            vod.vod_play_url = firstLine ? firstLine.url : "";
        } else {
            const fromRaw = String(d.vod_play_from || '');
            const urlRaw = String(d.vod_play_url || '');
            const fromArr = fromRaw.split('$$$');
            const urlArr = urlRaw.split('$$$');
            for(let idx=0;idx<fromArr.length;idx++){
                vod._innerLines.push({name:fromArr[idx],code:'',url:urlArr[idx]||''});
            }
            vod.vod_play_from = "恒轩";
            vod.vod_play_url = vod._innerLines.length>0 ? vod._innerLines[0].url : "";
        }
        list.push(vod);
    }
    return JSON.stringify({ list: list });
}
const PLAY_CACHE_TTL = 120000;
async function play(flag, id, flags) {
    const rawInput = String(id || '').trim();
    const cacheKey = rawInput;
    const hit = C.playCache[cacheKey];
    if (hit && hit.url && (Date.now() - hit.ts) < PLAY_CACHE_TTL) {
        return JSON.stringify({ parse: 0, url: hit.url, header: PH });
    }
    let token = rawInput;
    if(flags && flags._innerLines && Array.isArray(flags._innerLines)){
        const eps = splitEpisodeList(flags._innerLines[0].url);
        const targetEp = eps.find(x=>x.rawUrl === rawInput);
        if(targetEp) token = targetEp.rawUrl;
    }
    let resp;
    try{
        resp = await req(C.resolveApi+"?token="+encodeURIComponent(token),{headers:PH});
    }catch(e){
        return JSON.stringify({ parse:0, url:"", header:PH });
    }
    if(!resp || !resp.content){
        return JSON.stringify({ parse:0, url:"", header:PH });
    }
    let obj;
    try{
        obj = JSON.parse(resp.content);
    }catch(e){
        return JSON.stringify({ parse:0, url:"", header:PH });
    }
    const finalUrl = obj.url||"";
    if(finalUrl){
        C.playCache[cacheKey]={url:finalUrl,ts:Date.now()};
    }
    return JSON.stringify({ parse:0, url:finalUrl, header: obj.header||PH });
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
