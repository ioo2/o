import { Crypto, load, _ } from 'assets://js/lib/cat.js';

let HOST = 'https://www.xptv.cc';
let siteKey = '', siteType = '', sourceKey = '', ext = '';

const COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin'
};

async function request(url, ref, retry = 1) {
    const headers = { ...COMMON_HEADERS };
    if (ref) headers['Referer'] = ref;
    try {
        const res = await req(url, {
            method: 'get',
            headers: headers,
            timeout: 5000
        });
        return res;
    } catch (e) {
        if (retry > 0) {
            return await request(url, ref, retry - 1);
        }
        return { content: '' };
    }
}

function joinUrl(url) {
    if (!url) return '';
    if (url.startsWith('http')) return url;
    if (url.startsWith('//')) return 'https:' + url;
    if (url.startsWith('/')) return HOST + url;
    return HOST + '/' + url;
}

// 解析影片列表 (分类/搜索/首页通用)
function parseVodList(html) {
    const $ = load(html);
    const list = [];
    $('a[href^="/v/"]').each((_, el) => {
        const a = $(el);
        const href = a.attr('href');
        const name = a.find('h3').first().text().trim();
        if (!name) return;
        const pic = a.find('img').attr('src') || '';
        let remarks = '';
        const statusEl = a.find('.absolute.top-0.right-0').first();
        if (statusEl.length) remarks = statusEl.text().trim();
        const scoreEl = a.find('.absolute.top-0.left-0').first();
        if (scoreEl.length) {
            const score = scoreEl.text().trim();
            remarks = remarks ? score + ' | ' + remarks : score;
        }
        list.push({
            vod_id: href,
            vod_name: name,
            vod_pic: joinUrl(pic),
            vod_remarks: remarks
        });
    });
    const map = {};
    return list.filter(it => {
        if (!it.vod_id || map[it.vod_id]) return false;
        map[it.vod_id] = 1;
        return true;
    });
}

function init(cfg) {
    siteKey = cfg.skey;
    siteType = cfg.stype;
    sourceKey = cfg.sourceKey;
    ext = cfg.ext || '';
    if (ext && ext.startsWith('http')) {
        HOST = ext.replace(/\/$/, '');
    }
}

async function home(filter) {
    const classes = [
        { type_id: 'dianying', type_name: '电影' },
        { type_id: 'dianshiju', type_name: '电视剧' },
        { type_id: 'dongman', type_name: '动漫' }
    ];

    // 筛选参数定义（基于页面实际选项）
    const filterObj = {
        "class": [
            { n: "全部", v: "" }, { n: "剧情", v: "剧情" }, { n: "喜剧", v: "喜剧" }, { n: "爱情", v: "爱情" },
            { n: "动作", v: "动作" }, { n: "犯罪", v: "犯罪" }, { n: "惊悚", v: "惊悚" }, { n: "悬疑", v: "悬疑" },
            { n: "科幻", v: "科幻" }, { n: "恐怖", v: "恐怖" }, { n: "奇幻", v: "奇幻" }, { n: "冒险", v: "冒险" },
            { n: "古装", v: "古装" }, { n: "家庭", v: "家庭" }, { n: "历史", v: "历史" }, { n: "战争", v: "战争" },
            { n: "动画", v: "动画" }, { n: "传记", v: "传记" }, { n: "武侠", v: "武侠" }, { n: "运动", v: "运动" },
            { n: "音乐", v: "音乐" }, { n: "同性", v: "同性" }, { n: "纪录", v: "纪录" }, { n: "歌舞", v: "歌舞" },
            { n: "灾难", v: "灾难" }, { n: "西部", v: "西部" }, { n: "儿童", v: "儿童" }
        ],
        "area": [
            { n: "全部", v: "" }, { n: "内地", v: "内地" }, { n: "中国香港", v: "中国香港" }, { n: "中国台湾", v: "中国台湾" },
            { n: "韩国", v: "韩国" }, { n: "日本", v: "日本" }, { n: "美国", v: "美国" }, { n: "法国", v: "法国" },
            { n: "英国", v: "英国" }, { n: "泰国", v: "泰国" }, { n: "印度", v: "印度" }, { n: "其它", v: "其它" }
        ],
        "year": [
            { n: "全部", v: "" }, { n: "2026", v: "2026" }, { n: "2025", v: "2025" }, { n: "2024", v: "2024" },
            { n: "2023", v: "2023" }, { n: "2022", v: "2022" }, { n: "2021", v: "2021" }, { n: "2020", v: "2020" },
            { n: "10年代", v: "2010-2019" }, { n: "00年代", v: "2000-2009" }, { n: "90年代", v: "1990-1999" },
            { n: "80年代", v: "1980-1989" }, { n: "更早", v: "1800-1979" }
        ],
        "isend": [
            { n: "全部", v: "" }, { n: "已完结", v: "完结" }, { n: "连载中", v: "连载" }
        ],
        "by": [
            { n: "按时间", v: "time" }, { n: "按热度", v: "hits" }, { n: "按评分", v: "score" }
        ]
    };

    const filters = {};
    classes.forEach(c => {
        filters[c.type_id] = [
            { key: "class", name: "类型", value: filterObj["class"] },
            { key: "area", name: "地区", value: filterObj["area"] },
            { key: "year", name: "年份", value: filterObj["year"] },
            { key: "isend", name: "状态", value: filterObj["isend"] },
            { key: "by", name: "排序", value: filterObj["by"] }
        ];
    });

    return JSON.stringify({ class: classes, filters: filters });
}

async function homeVod() {
    try {
        const res = await request(HOST + '/');
        const list = parseVodList(res.content || '');
        return JSON.stringify({ list: list });
    } catch (e) {
        return JSON.stringify({ list: [] });
    }
}

async function category(tid, pg, filter, extend) {
    pg = parseInt(pg) || 1;
    extend = extend || {};

    // 构建筛选路径：/show/{tid}/class/.../area/.../year/.../isend/.../by/...-pg.html
    let base = tid; // dianshiju / dianying / dongman
    let pathParts = [];
    if (extend.class) pathParts.push('class/' + encodeURIComponent(extend.class));
    if (extend.area) pathParts.push('area/' + encodeURIComponent(extend.area));
    if (extend.year) pathParts.push('year/' + encodeURIComponent(extend.year));
    if (extend.isend) pathParts.push('isend/' + encodeURIComponent(extend.isend));
    if (extend.by) pathParts.push('by/' + encodeURIComponent(extend.by));

    let path = base;
    if (pathParts.length > 0) path += '/' + pathParts.join('/');

    let url = HOST + '/show/' + path + (pg > 1 ? '-' + pg : '') + '.html';
    // 若没有任何筛选，回退到类型分页
    if (pathParts.length === 0 && !extend.class && !extend.area && !extend.year && !extend.isend && !extend.by) {
        url = HOST + '/type/' + tid + '-' + pg + '.html';
    }

    try {
        const res = await request(url, HOST + '/');
        const list = parseVodList(res.content || '');
        return JSON.stringify({
            page: pg,
            pagecount: list.length > 0 ? pg + 1 : pg,
            limit: 24,
            total: list.length * 24,
            list: list
        });
    } catch (e) {
        return JSON.stringify({ page: pg, pagecount: 0, limit: 24, total: 0, list: [] });
    }
}

async function detail(id) {
    try {
        const url = joinUrl(id);
        const res = await request(url, HOST + '/');
        const html = res.content || '';
        const $ = load(html);

        const vod = {
            vod_id: id,
            vod_name: $('h1').first().text().trim() || $('.title').first().text().trim(),
            vod_pic: joinUrl($('img').first().attr('src') || ''),
            vod_content: $('.intro, .desc, [class*="description"]').first().text().trim() ||
                         $('meta[name="description"]').attr('content') || ''
        };

        // 提取元数据
        const infoText = $('.info, .meta, .video-info').text() || $('body').text();
        const directorMatch = infoText.match(/导演[：:]\s*(.+?)(?:\s|$)/);
        if (directorMatch) vod.vod_director = directorMatch[1].trim();
        const actorMatch = infoText.match(/主演[：:]\s*(.+?)(?:\s|$)/);
        if (actorMatch) vod.vod_actor = actorMatch[1].trim();
        const typeMatch = infoText.match(/类型[：:]\s*(.+?)(?:\s|$)/);
        if (typeMatch) vod.vod_type = typeMatch[1].trim();
        const areaMatch = infoText.match(/地区[：:]\s*(.+?)(?:\s|$)/);
        if (areaMatch) vod.vod_area = areaMatch[1].trim();
        const yearMatch = infoText.match(/年份[：:]\s*(.+?)(?:\s|$)/);
        if (yearMatch) vod.vod_year = yearMatch[1].trim();

        // 提取播放列表 (基于播放页结构，详情页应包含类似 .playlist-grid)
        const playFrom = [];
        const playUrl = [];
        $('.playlist-grid a').each((_, el) => {
            const a = $(el);
            const title = a.text().trim();
            const link = a.attr('href');
            if (link && link.includes('/p/')) {
                if (!playFrom.length) playFrom.push('恒轩');
                if (!playUrl[0]) playUrl[0] = [];
                playUrl[0].push(title + '$' + link);
            }
        });

        if (playUrl.length > 0) {
            vod.vod_play_from = playFrom.join('$$$');
            vod.vod_play_url = playUrl.map(arr => arr.join('#')).join('$$$');
        } else {
            // 兼容无列表的情况
            vod.vod_play_from = '恒轩';
            vod.vod_play_url = '';
        }

        return JSON.stringify({ list: [vod] });
    } catch (e) {
        return JSON.stringify({ list: [] });
    }
}

async function search(wd, quick, pg) {
    pg = parseInt(pg) || 1;
    const url = HOST + '/so.html?wd=' + encodeURIComponent(wd) + '&page=' + pg;
    try {
        const res = await request(url, HOST + '/');
        const list = parseVodList(res.content || '');
        return JSON.stringify({
            page: pg,
            pagecount: list.length > 0 ? pg + 1 : pg,
            limit: 24,
            total: list.length * 24,
            list: list
        });
    } catch (e) {
        return JSON.stringify({ page: pg, pagecount: 0, limit: 24, total: 0, list: [] });
    }
}

async function play(flag, id, flags) {
    try {
        const url = joinUrl(id);
        const res = await request(url, HOST + '/');
        const html = res.content || '';
        const match = html.match(/var\s+player_aaaa\s*=\s*(\{[^;]+\});/);
        if (match) {
            const player = JSON.parse(match[1]);
            let realUrl = player.url || '';
            // 加密字段处理
            if (player.encrypt == 1 && realUrl) {
                // 先URI解码
                realUrl = decodeURIComponent(realUrl);
                // 尝试Base64解码
                try {
                    const words = Crypto.enc.Base64.parse(realUrl);
                    realUrl = Crypto.enc.Utf8.stringify(words);
                } catch (e) {}
            }
            if (realUrl && (realUrl.startsWith('http') || realUrl.startsWith('/'))) {
                return JSON.stringify({
                    parse: 0,
                    url: realUrl.startsWith('/') ? HOST + realUrl : realUrl,
                    header: { 'User-Agent': COMMON_HEADERS['User-Agent'], 'Referer': url }
                });
            }
        }
        // 降级为嗅探模式
        return JSON.stringify({
            parse: 1,
            url: url,
            header: { 'User-Agent': COMMON_HEADERS['User-Agent'] }
        });
    } catch (e) {
        return JSON.stringify({ parse: 1, url: id });
    }
}

export function __jsEvalReturn() {
    return { init, home, homeVod, category, detail, search, play };
}
