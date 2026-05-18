import {Crypto, _} from 'assets://js/lib/cat.js';
let host = 'https://bbys.app';
let device_id = '';
const pkg = 'com.sunshine.tv';
const ver = '4';
const device_id_cache_key = 'com.sunshine.tv_3qys_B7k7Dt56Rn';

async function init(cfg) {
    const ext = cfg.ext;
    if (typeof cfg.ext === 'string' && cfg.ext.startsWith('http')) {
        host = cfg.ext.trim().replace(/\/$/, '');
    }
}

async function home(filter) {
    const hd = await getHeaders();
    const resp = await req(`${host}/api.php/app/index/home`, { headers: hd });
    const json = JSON.parse(resp.content);
    const classes = _.map(json.data.categories, (i) => ({
        'type_id': i.type_name,
        'type_name': i.type_name
    }));
    const videos = [];
    for (const cat of json.data.categories) {
        videos.push(...arr2vods(cat.videos));
    }
    return JSON.stringify({ class: classes, list: videos });
}

async function homeVod() {
    return JSON.stringify({ list: [] });
}

async function category(tid, pg, filter, extend) {
    const hd = await getHeaders();
    const url = `${host}/api.php/app/filter/vod?type_name=${encodeURIComponent(tid)}&page=${pg}&sort=hits`;
    const resp = await req(url, { headers: hd });
    const json = JSON.parse(resp.content);
    return JSON.stringify({
        list: arr2vods(json.data),
        pagecount: json.pageCount,
        page: parseInt(pg)
    });
}

async function search(wd, quick, pg=1) {
    const hd = await getHeaders();
    const url = `${host}/api.php/app/search/index?wd=${encodeURIComponent(wd)}&page=${pg}&limit=15`;
    const resp = await req(url, { headers: hd });
    const json = JSON.parse(resp.content);
    return JSON.stringify({
        list: arr2vods(json.data),
        pagecount: json.pageCount,
        page: parseInt(pg)
    });
}


async function detail(id) {
    const hd = await getHeaders();
    const resp = await req(`${host}/api.php/app/vod/get_detail?vod_id=${id}`, { headers: hd });
    const json = JSON.parse(resp.content);
    const data = json.data[0];
    const vodplayer = json.vodplayer;

    
    const raw_shows = data.vod_play_from.split('$$$');
    const raw_urls_list = data.vod_play_url.split('$$$');
    const allLines = [];

    
    for (let i = 0; i < raw_shows.length; i++) {
        const show_code = raw_shows[i];
        const urls_str = raw_urls_list[i];
        const player_info = _.find(vodplayer, (p) => p.from === show_code);
        if (!player_info) continue;

        const urls = [];
        for (const u of urls_str.split('#')) {
            if (u.includes('$')) {
                const [ep, url] = u.split('$');
                urls.push({ ep, url });
            }
        }
        if (urls.length === 0) continue;

        allLines.push({
            show_code,
            show_name: player_info.show,
            need_parse: player_info.decode_status,
            urls_str,
            urls
        });
    }


    let target = null;
    target = _.find(allLines, line => 
        line.show_name.includes('JD蓝光') || line.show_name.includes('JD4K')
    );

    
    if (!target && allLines.length > 0) {
        target = allLines[0];
    }

    
    const shows = [];
    const play_urls = [];
    if (target) {
        const finalUrls = [];
        for (const u of target.urls) {
            finalUrls.push(`${u.ep}$${target.show_code}@${target.need_parse}@${u.url}`);
        }
        play_urls.push(finalUrls.join('#'));
        shows.push('恒轩'); 
    }

    const video = {
        'vod_id': data.vod_id.toString(),
        'vod_name': data.vod_name,
        'vod_pic': data.vod_pic,
        'vod_remarks': data.vod_remarks,
        'vod_year': data.vod_year,
        'vod_area': data.vod_area,
        'vod_actor': data.vod_actor,
        'vod_director': data.vod_director,
        'vod_content': data.vod_content,
        'vod_play_from': shows.join('$$$'),
        'vod_play_url': play_urls.join('$$$'),
        'type_name': data.vod_class
    };
    return JSON.stringify({ list: [video] });
}

async function play(flag, vid, flags) {
    const parts = vid.split('@');
    const play_from = parts[0];
    const need_parse = parts[1];
    const raw_url = parts[2];
    let url = '';
    let jx = 0;
    if (need_parse === '1') {
        try {
            const hd = await getHeaders();
            const apiUrl = `${host}/api.php/app/decode/url/?url=${encodeURIComponent(raw_url)}&vodFrom=${play_from}`;
            const resp = await req(apiUrl, { headers: hd, timeout: 30000 });
            const json = JSON.parse(resp.content);
            if (json.data && json.data.startsWith('http')) {
                url = json.data;
            }
        } catch (e) {
            console.error('Play decode error:', e);
        }
    }
    if (!url) {
        url = raw_url;
        if (/(www\.iqiyi|v\.qq|v\.youku|www\.mgtv|www\.bilibili)\.com/.test(raw_url)) {
            jx = 1;
        }
    }
    return JSON.stringify({ jx: jx, parse: 0, url: url, header: {'User-Agent': 'com.sunshine.tv/1.2.0 (Linux;Android 15) AndroidXMedia3/1.4.1'}});
}

async function getHeaders() {
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const nonce = randomStr(3, '0123456789');
    if (!device_id) {
        device_id = await local.get('cache', device_id_cache_key);
        if (!device_id || device_id.length !== 16) {
            device_id = randomStr(16);
            await local.set('cache', device_id_cache_key, device_id);
        }
    }
    const sign_str = `finger=SF-C3B2B41F6EFFFF9869176CF68F6790E8F07506FC88632C94B4F5F0430D5498CA&id=${pkg}&nonce=${nonce}&sk=SK-thanks&time=${timestamp}&v=${ver}`;
    const sign = sha256(sign_str);
    return {
        'User-Agent': 'okhttp/4.12.0',
        'Accept': 'application/json',
        'x-aid': pkg,
        'x-ave': ver,
        'x-time': timestamp,
        'x-nonc': nonce,
        'x-sign': sign,
        'x-device-id': device_id,
        'x-device-brand': 'vivo',
        'x-device-model': 'V2309A',
        'x-update-id': '0245861b-2ebf-5524-389d-f983830651ec'
    };
}

function arr2vods(arr) {
    return _.map(arr, (i) => {
        let type_name = i.type_name || '';
        if (i.vod_class) {
            type_name = type_name + (type_name ? ',' : '') + i.vod_class;
        }
        return {
            'vod_id': i.vod_id.toString(),
            'vod_name': i.vod_name,
            'vod_pic': i.vod_pic,
            'vod_remarks': i.vod_remarks,
            'type_name': type_name,
            'vod_year': i.vod_year
        };
    });
}

function randomStr(len, chars = '0123456789abcdef') {
    let str = '';
    for (let i = 0; i < len; i++) {
        str += chars[_.random(0, chars.length - 1)];
    }
    return str;
}

function sha256(text) {
    return Crypto.SHA256(text).toString().toUpperCase();
}

export function __jsEvalReturn() {
    return {
        init: init,
        home: home,
        homeVod: homeVod,
        category: category,
        search: search,
        detail: detail,
        play: play
    };
}