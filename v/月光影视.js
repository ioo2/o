/*
title: '月光影视', author: '小可乐/v5.12.1'
说明：可以不写ext，也可以写ext，ext支持的参数和格式参数如下
"ext": {
    "host": "xxxx", //站点网址
    "timeout": 6000  //请求超时，单位毫秒
}
*/
var HOST;
const MOBILE_UA = 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36';
const DefHeader = {'User-Agent': MOBILE_UA};
const KParams = {
    headers: {'User-Agent': MOBILE_UA},
    timeout: 5000
};

async function init(cfg) {
    try {
        let host = cfg.ext?.host?.trim() || 'https://www.dzwhs.com';
        HOST = host.replace(/\/$/, '');
        KParams.headers['Referer'] = HOST;
        let parseTimeout = parseInt(cfg.ext?.timeout, 10);
        KParams.timeout = parseTimeout > 0 ? parseTimeout : 5000;
        KParams.resHtml = await request(HOST);
    } catch (e) {
        console.error('初始化参数失败：', e.message);
    }
}

async function home(filter) {
    try {
        let resHtml = KParams.resHtml;
        if (!resHtml) throw new Error('源码为空');
        let classes = cutStr(resHtml, '/zwhstp', '/a>', '', false, 1, true).map(it => {
            let cName = cutStr(it, '>', '<', '');
            let cId = cutStr(it, '/', '.', '');
            return {type_name: cName || '未知', type_id: cId || '1'};
        });
        let filters = {
            "1":[{"key":"cateId","name":"类型","value":[{"n":"全部","v":"全部"},{"n":"动作片","v":"6"},{"n":"喜剧片","v":"7"},{"n":"爱情片","v":"8"},{"n":"科幻片","v":"9"},{"n":"恐怖片","v":"10"},{"n":"剧情片","v":"11"},{"n":"战争片","v":"12"},{"n":"纪录片","v":"13"},{"n":"悬疑片","v":"14"},{"n":"犯罪片","v":"15"},{"n":"奇幻片","v":"16"},{"n":"动画片","v":"31"},{"n":"预告片","v":"32"}]}],
            "2":[{"key":"cateId","name":"类型","value":[{"n":"全部","v":"全部"},{"n":"国产剧","v":"17"},{"n":"港台剧","v":"18"},{"n":"日韩剧","v":"20"},{"n":"欧美剧","v":"21"},{"n":"海外剧","v":"22"}]}],
            "3":[{"key":"cateId","name":"类型","value":[{"n":"全部","v":"全部"},{"n":"大陆综艺","v":"23"},{"n":"日韩综艺","v":"24"},{"n":"欧美综艺","v":"25"},{"n":"港台综艺","v":"26"}]}],
            "4":[{"key":"cateId","name":"类型","value":[{"n":"全部","v":"全部"},{"n":"国产动漫","v":"27"},{"n":"日韩动漫","v":"28"},{"n":"欧美动漫","v":"29"},{"n":"其他动漫","v":"30"}]}]
        };
        return JSON.stringify({class: classes, filters: filters});
    } catch (e) {
        console.error('获取分类失败：', e.message);
        return JSON.stringify({class: [], filters: {}});
    }
}

async function homeVod() {
    try {
        let resHtml = KParams.resHtml;
        let VODS = getVodList(resHtml);
        return JSON.stringify({list: VODS});
    } catch (e) {
        console.error('推荐页获取失败：', e.message);
        return JSON.stringify({list: []});
    }
}

async function category(tid, pg, filter, extend) {
    try {
        pg = parseInt(pg, 10) || 1;
        let cateUrl = `${HOST}/zwhstp/${extend?.cateId ?? tid}-${pg}.html`;
        let resHtml = await request(cateUrl);
        let VODS = getVodList(resHtml);
        return JSON.stringify({list: VODS, page: pg, pagecount: 999, limit: 30, total: 29970});
    } catch (e) {
        console.error('类别页获取失败：', e.message);
        return JSON.stringify({list: [], page: 1, pagecount: 0, limit: 30, total: 0});
    }
}

async function search(wd, quick, pg) {
    try {
        pg = parseInt(pg, 10) || 1;
        let searchUrl = `${HOST}/zwhstp/id.html?wd=${encodeURIComponent(wd)}&page=${pg}`;
        let resHtml = await request(searchUrl);
        let VODS = getVodList(resHtml);
        return JSON.stringify({list: VODS, page: pg, pagecount: 10, limit: 30, total: 300});
    } catch (e) {
        console.error('搜索页获取失败：', e.message);
        return JSON.stringify({list: [], page: 1, pagecount: 0, limit: 30, total: 0});
    }
}

function getVodList(khtml) {
    try {
        if (!khtml) return [];
        let kvods = [];
        let listArr = cutStr(khtml, 'lazyload"', '/a>', '', false, 1, true);
        for (let it of listArr) {
            let kname = cutStr(it, 'title="', '"', '');
            let kpic = cutStr(it, 'data-original="', '"', '');
            let kremarks = cutStr(it, 'text-right">', '<', '');
            let kid = cutStr(it, 'href="', '"', '');
            if (kname && kid) {
                kvods.push({
                    vod_name: kname,
                    vod_pic: kpic,
                    vod_remarks: kremarks || '完结',
                    vod_id: `${kid}@${kname}@${kpic}@${kremarks}`
                });
            }
        }
        return kvods;
    } catch (e) {
        return [];
    }
}

async function detail(ids) {
    try {
        let arr = ids.split('@');
        let id = arr[0] || '';
        let kname = arr[1] || '';
        let kpic = arr[2] || '';
        let kremarks = arr[3] || '';
        
        let detailUrl = id.startsWith('http') ? id : `${HOST}${id}`;
        let resHtml = await request(detailUrl);
        if (!resHtml) throw new Error('为空');
        
        let intros = cutStr(resHtml, 'stui-content col-pd', 'play-btn', '', false);
        let ktabs = cutStr(resHtml, 'pull-right"></span>', '/h3>', '', false, 1, true);
        let kurls = cutStr(resHtml, '"stui-content__playlist', '</ul>', '', false, 1, true).map(item => {
            return cutStr(item, '<a', '/a>', '', false, 1, true).map(it => {
                let n = cutStr(it, '>', '<', '');
                let u = cutStr(it, 'href="', '"', '');
                return n + '$' + u;
            }).join('#');
        });

         
        let targetIdx = 0;
        if (ktabs.length) {
            let air = ktabs.findIndex(t=>/AirPlay|airplay/i.test(t));
            if(air !== -1) targetIdx = air;
            else {
                let lg = ktabs.findIndex(t=>/蓝光|抢先/.test(t));
                if(lg !== -1) targetIdx = lg;
            }
        }

        let VOD = {
            vod_id: detailUrl,
            vod_name: kname,
            vod_pic: kpic,
            type_name: cutStr(intros, '类型：', '<span', '未知'),
            vod_remarks: kremarks,
            vod_year: cutStr(intros, '年份：', '</p', '----'),
            vod_area: cutStr(intros, '地区：', '<span', '未知'),
            vod_lang: '国语',
            vod_director: cutStr(intros, '导演：', '</p', '未知'),
            vod_actor: cutStr(intros, '主演：', '</p', '未知'),
            vod_content: cutStr(intros, '简介：', '</', '暂无简介'),
            vod_play_from: '恒轩',
            vod_play_url: kurls[targetIdx] || ''
        };
        return JSON.stringify({list: [VOD]});
    } catch (e) {
        console.error('详情失败：',e);
        return JSON.stringify({list: []});
    }
}

async function play(flag, ids, flags) {
    try {
        let playUrl = ids.startsWith('http') ? ids : `${HOST}${ids}`;
        let resHtml = await request(playUrl);
        let kcode = safeParseJSON(cutStr(resHtml, 'var player_', ';', '', false));
        let url = kcode?.url || '';
        let parse = 0;
        if(!/m3u8|mp4|mkv/.test(url)){
            parse = 1;
            url = playUrl;
        }
        return JSON.stringify({jx:0, parse, url, header: DefHeader});
    } catch(e){
        return JSON.stringify({jx:0, parse:0, url:'', header:{}});
    }
}

function cutStr(str, prefix, suffix, d='', clean=true, i=1, all=false) {
    try {
        if (!str) return all ? [] : d;
        const reg = new RegExp(escapeReg(prefix) + '([\\s\\S]*?)' + escapeReg(suffix), 'g');
        let ms = [...str.matchAll(reg)];
        if (all) return ms.map(m=>(clean ? cleanTxt(m[1]||d) : m[1]||d));
        i = Math.max(0, parseInt(i)-1);
        return ms[i] ? (clean ? cleanTxt(ms[i][1]) : ms[i][1]) : d;
    } catch(e) {
        return all ? [] : d;
    }
}

function cleanTxt(s){
    return String(s||'').replace(/<[^>]+>/g,'').replace(/\s+/g,' ').trim();
}

function escapeReg(s){
    return String(s||'').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function safeParseJSON(s){
    try{return JSON.parse(s)}catch(e){return {}}
}

async function request(reqUrl, options = {}) {
    try {
        let opt = {
            headers: KParams.headers,
            timeout: KParams.timeout,
            ...options
        };
        let res = await req(reqUrl, opt);
        return res?.content || '';
    } catch (e) {
        return '';
    }
}

export function __jsEvalReturn() {
    return { init, home, homeVod, category, search, detail, play, proxy:null };
}