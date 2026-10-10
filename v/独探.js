const host = 'https://api.dbokutv.com';
const headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.duboku.tv/"
};
const CC_HOST = "http://cms.lyyytv.cn";
const C = {
    parseMap: {
        'lyyytv.cn': 'http://fys.lyyytv.cn/api/index?parsesId=3&appid=10001&videoUrl=',
        '*': 'http://fys.lyyytv.cn/api/index?parsesId=3&appid=10001&videoUrl='
    },
    playCache: {},
    PLAY_CACHE_TTL: 120000,
    PLAY_ROUNDS:3,
    PLAY_BACKOFF:350,
    ccToken:""
};
const H_CC = {
    'User-Agent':'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0 Mobile Safari/537.36',
    'Accept':'application/json, text/plain, */*'
};
const PH = {
    'User-Agent': 'okhttp/4.12.0',
    'Accept-Encoding': 'identity'
};
function sleep(ms) {
    return new Promise(resolve => { try { setTimeout(resolve, ms); } catch (e) { resolve(); } });
}
function splitEpisodeList(s) {
    s = String(s || '').replace(/#+$/, '');
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
        epName = epName.trim();
        epsOut.push({ epName: epName, rawUrl: rawUrl });
    }
    return epsOut;
}
function joinEpisodeList(epList) {
    return epList.map(e => (e.epName || '') + '$' + e.rawUrl).join('#');
}
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
async function ccApi(path,params){
    let q = C.ccToken?"token="+encodeURIComponent(C.ccToken):"";
    let first = !q;
    for(let k in params){
        if(params[k]==null||params[k]==="")continue;
        q += (first?"":"&")+k+"="+encodeURIComponent(String(params[k]));
        first=false;
    }
    const url = CC_HOST+path+(q?"?"+q:"");
    let resp;
    try{ resp = await req(url,{headers:H_CC}); }catch(e){return null;}
    if(!resp||String(resp.code)!=='200'||!resp.content) return null;
    let jo;
    try{ jo = JSON.parse(resp.content); }catch(e){return null;}
    if(!jo||jo.code!==1) return null;
    if(jo.data&&jo.data.token) C.ccToken=String(jo.data.token);
    else if(jo.token) C.ccToken=String(jo.token);
    return jo;
}
async function getCcVodDetail(keyword){
    const searchRes = await ccApi("/api.php/app/search",{text:keyword,pg:1});
    if(!searchRes||!Array.isArray(searchRes.list)||searchRes.list.length===0) return null;
    const vid = searchRes.list[0].vod_id;
    const detailRes = await ccApi("/api.php/app/video_detail",{id:vid});
    if(!detailRes||!detailRes.data) return null;
    const d = detailRes.data;
    let innerLines = [];
    if(Array.isArray(d.vod_url_with_player)&&d.vod_url_with_player.length>0){
        for(const it of d.vod_url_with_player){
            innerLines.push({name:String(it.name||""),code:String(it.code||""),url:String(it.url||"")});
        }
    }else{
        const fromArr = String(d.vod_play_from||"").split("$$$");
        const urlArr = String(d.vod_play_url||"").split("$$$");
        for(let i=0;i<fromArr.length;i++){
            innerLines.push({name:fromArr[i]||"",code:"",url:urlArr[i]||""});
        }
    }
    return innerLines;
}
async function parseCcPlayUrl(rawInput,innerLines){
    if(!innerLines||!Array.isArray(innerLines)||innerLines.length===0) return "";
    const cacheKey = rawInput;
    const hit = C.playCache[cacheKey];
    if(hit&&hit.url&&(Date.now()-hit.ts)<C.PLAY_CACHE_TTL) return hit.url;
    let priorityList=[];
    let backupList=[];
    for(const line of innerLines){
        const fullName = (line.name||"")+"-"+(line.code||"");
        if(fullName.includes("联通云")) priorityList.push(line);
        else backupList.push(line);
    }
    const tryLines = priorityList.concat(backupList);
    let finalUrl = "";
    for(const line of tryLines){
        if(!line.url) continue;
        const eps = splitEpisodeList(line.url);
        const targetEp = eps.find(x=>x.rawUrl===rawInput);
        if(!targetEp) continue;
        const bases = pickParses(targetEp.rawUrl);
        if(!bases.length) continue;
        let tmpUrl = "";
        for(let round=0;round<C.PLAY_ROUNDS&&!tmpUrl;round++){
            if(round>0) await sleep(round*C.PLAY_BACKOFF);
            for(let i=0;i<bases.length;i++){
                try{
                    const resp = await req(bases[i]+encodeURIComponent(targetEp.rawUrl),{headers:PH});
                    if(resp&&resp.content){
                        const u = resolveParse(resp.content);
                        if(u&&u.indexOf("http")===0){ tmpUrl=u; break; }
                    }
                }catch(e){}
            }
        }
        if(tmpUrl){
            finalUrl = tmpUrl;
            C.playCache[cacheKey]={url:finalUrl,ts:Date.now()};
            break;
        }
    }
    return finalUrl;
}

function base64Encode(text) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    let b64 = '';
    for (let i = 0; i < text.length; i += 3) {
        let n = (text.charCodeAt(i) << 16) | (text.charCodeAt(i + 1) << 8) | text.charCodeAt(i + 2);
        b64 += chars.charAt((n >> 18) & 63)
            + chars.charAt((n >> 12) & 63)
            + chars.charAt((n >> 6) & 63)
            + chars.charAt(n & 63);
    }
    let mod = text.length % 3;
    return (mod ? b64.slice(0, mod - 3) + "===".substring(mod) : b64);
}
function base64Decode(str) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    str = str.replace(/=/g, '');
    let bin = '';
    for (let i = 0; i < str.length; i += 4) {
        let n = (chars.indexOf(str.charAt(i)) << 18)
            | (chars.indexOf(str.charAt(i + 1)) << 12)
            | (chars.indexOf(str.charAt(i + 2)) << 6)
            | chars.indexOf(str.charAt(i + 3));
        bin += String.fromCharCode((n >> 16) & 255, (n >> 8) & 255, n & 255);
    }
    return bin.replace(/\0/g, '');
}
function decodeData(data) {
    if (!data || typeof data !== 'string') return '';
    let strippedStr = data.replace(/['"]/g, '').trim();
    if (!strippedStr) return '';
    let segmentLength = 10;
    let processedBase64 = '';
    for (let i = 0; i < strippedStr.length; i += segmentLength) {
        let segment = strippedStr.substring(i, i + segmentLength);
        processedBase64 += segment.split('').reverse().join('');
    }
    processedBase64 = processedBase64.replace(/\./g, '=');
    try {
        return base64Decode(processedBase64);
    } catch (e) {
        return '';
    }
}
function getSignedUrl(path) {
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const randomNumber = Math.floor(Math.random() * 800000001);
    const valueA = (randomNumber + 100000000).toString();
    const valueB = (900000000 - randomNumber).toString();
    const combined = valueA + valueB;
    let interleaved = '';
    let minLen = Math.min(combined.length, timestamp.length);
    for (let i = 0; i < minLen; i++) {
        interleaved += combined[i] + timestamp[i];
    }
    interleaved += combined.substring(minLen) + timestamp.substring(minLen);
    const ssid = base64Encode(interleaved).replace(/=/g, '.');
    function randomStr(len) {
        const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        let res = '';
        for (let i = 0; i < len; i++) res += chars.charAt(Math.floor(Math.random() * chars.length));
        return res;
    }
    const sign = randomStr(60);
    const token = randomStr(38);
    const connector = path.includes('?') ? '&' : '?';
    return `${host}${path}${connector}sign=${sign}&token=${token}&ssid=${ssid}`;
}
async function init(cfg) {}
async function home(filter) {
    const classes = [
        { type_id: '2', type_name: '连续剧' },
        { type_id: '1', type_name: '电影' },
        { type_id: '3', type_name: '综艺' },
        { type_id: '4', type_name: '动漫' }
    ];
    return JSON.stringify({ class: classes });
}
async function homeVod() {
    const url = getSignedUrl('/home');
    const r = await req(url, { headers });
    const json = JSON.parse(r.content);
    let videos = [];
    json.forEach(group => {
        (group.VodList || []).forEach(j => {
            videos.push({
                vod_id: decodeData(j.DId || j.DuId),
                vod_name: j.Name,
                vod_pic: decodeData(j.TnId),
                vod_remarks: j.Tag
            });
        });
    });
    return JSON.stringify({ list: videos });
}
async function category(tid, pg, filter, extend = {}) {
    let page = pg || 1;
    let pageStr = page.toString() === '1' ? '' : page.toString();
    let urlPath = `/vodshow/${tid}--------${pageStr}---`;
    const url = getSignedUrl(urlPath);
    const r = await req(url, { headers });
    const json = JSON.parse(r.content);
    let videos = (json.VodList || []).map(i => ({
        vod_id: decodeData(i.DId || i.DuId),
        vod_name: i.Name,
        vod_pic: decodeData(i.TnId),
        vod_remarks: i.Tag
    }));
    let pageCount = page;
    try {
        (json.PaginationList || []).forEach(j => {
            if (j.Type === 'StartEnd') {
                let parts = decodeData(j.PId || j.PuId).split('-');
                if (parts.length > 8) pageCount = parseInt(parts[8]);
            } else if (j.Type === 'ShortPage') {
                pageCount = parseInt(j.Name.split('/')[1]);
            }
        });
    } catch (e) {}
    return JSON.stringify({
        page: parseInt(page),
        pagecount: pageCount || parseInt(page),
        list: videos
    });
}
async function detail(id) {
    const url = getSignedUrl(id);
    const r = await req(url, { headers });
    const data = JSON.parse(r.content);
    const playUrls = (data.Playlist || []).map(i => {
        return `${i.EpisodeName}$${decodeData(i.VId)}`;
    }).join('#');
    const ccInnerLines = await getCcVodDetail(data.Name);
    globalThis._ccInnerLinesCache = ccInnerLines;
    let ccPlayStr = playUrls;
    if(ccInnerLines&&ccInnerLines.length>0){
        ccPlayStr = ccInnerLines[0].url;
    }
    return JSON.stringify({
        list: [{
            vod_id: id,
            vod_name: data.Name,
            vod_pic: decodeData(data.TnId),
            vod_remarks: `评分：${data.Rating}`,
            vod_year: data.ReleaseYear,
            vod_area: data.Region,
            vod_actor: Array.isArray(data.Actor) ? data.Actor.join(',') : data.Actor,
            vod_director: data.Director,
            vod_content: data.Description,
            vod_play_from: '恒轩$$$4K',
            vod_play_url: playUrls + '$$$' + ccPlayStr,
            type_name: `${data.Genre || ''},${data.Scenario || ''}`
        }]
    });
}
async function search(wd, quick, pg = 1) {
    const url = getSignedUrl('/vodsearch') + `&wd=${encodeURIComponent(wd)}`;
    const r = await req(url, { headers });
    const json = JSON.parse(r.content);
    const list = (json || []).map(i => ({
        vod_id: decodeData(i.DId || i.DuId),
        vod_name: i.Name,
        vod_pic: decodeData(i.TnId),
        vod_remarks: i.Tag
    }));
    return JSON.stringify({ page: pg, list: list });
}
async function play(flag, id, flags) {
    let lineIndex = 0;
    let realId = id;
    if(flag && flag.includes('>>>')){
        const arr = flag.split('>>>');
        lineIndex = parseInt(arr[0])||0;
        realId = arr[1];
    }
    if(lineIndex === 1){
        const inner = globalThis._ccInnerLinesCache;
        const realUrl = await parseCcPlayUrl(realId,inner);
        return JSON.stringify({
            parse: 0,
            url: realUrl,
            header: PH
        });
    }
    const url = getSignedUrl(id);
    const r = await req(url, { headers });
    const res = JSON.parse(r.content);
    return JSON.stringify({
        parse: 0,
        url: decodeData(res.HId),
        header: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Origin': 'https://w.duboku.io',
            'Referer': 'https://w.duboku.io/'
        }
    });
}
export default { init, home, homeVod, category, detail, search, play };
