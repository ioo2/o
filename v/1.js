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
    nodes: [
        "http://156.238.228.37:894/v1",
        "http://124.221.108.97:894/v1",
        "http://110.42.56.152:894/v1"
    ],
    resolveKey: new Uint8Array([89,56,114,81,51,109,86,49,115,84,53,107,76,57,120,90])
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
const SBOX = new Uint8Array([
0x63,0x7C,0x77,0x7B,0xF2,0x6B,0x6F,0xC5,0x30,0x01,0x67,0x2B,0xFE,0xD7,0xAB,0x76,
0xCA,0x82,0xC9,0x7D,0xFA,0x59,0x47,0xF0,0xAD,0xD4,0xA2,0xAF,0x9C,0xA4,0x72,0xC0,
0xB7,0xFD,0x93,0x26,0x36,0x3F,0xF7,0xCC,0x34,0xA5,0xE5,0xF1,0x71,0xD8,0x31,0x15,
0x04,0xC7,0x23,0xC3,0x18,0x96,0x05,0x9A,0x07,0x12,0x80,0xE2,0xEB,0x27,0xB2,0x75,
0x09,0x83,0x2C,0x1A,0x1B,0x6E,0x5A,0xA0,0x52,0x3B,0xD6,0xB3,0x29,0xE3,0x2F,0x84,
0x53,0xD1,0x00,0xED,0x20,0xFC,0xB1,0x5B,0x6A,0xCB,0xBE,0x39,0x4A,0x4C,0x58,0xCF,
0xD0,0xEF,0xAA,0xFB,0x43,0x4D,0x33,0x85,0x45,0xF9,0x02,0x7F,0x50,0x3C,0x9F,0xA8,
0x51,0xA3,0x40,0x8F,0x92,0x9D,0x38,0xF5,0xBC,0xB6,0xDA,0x21,0x10,0xFF,0xF3,0xD2,
0xCD,0x0C,0x13,0xEC,0x5F,0x97,0x44,0x17,0xC4,0xA7,0x7E,0x3D,0x64,0x5D,0x19,0x73,
0x60,0x81,0x4F,0xDC,0x22,0x2A,0x90,0x88,0x46,0xEE,0xB8,0x14,0xDE,0x5E,0x0B,0xDB,
0xE0,0x32,0x3A,0x0A,0x49,0x06,0x24,0x5C,0xC2,0xD3,0xAC,0x62,0x91,0x95,0xE4,0x79,
0xE7,0xC8,0x37,0x6D,0x8D,0xD5,0x4E,0xA9,0x6C,0x56,0xF4,0xEA,0x65,0x7A,0xAE,0x08,
0xBA,0x78,0x25,0x2E,0x1C,0xA6,0xB4,0xC6,0xE8,0xDD,0x74,0x1F,0x4B,0xBD,0x8B,0x8A,
0x70,0x3E,0xB5,0x66,0x48,0x03,0xF6,0x0E,0x61,0x35,0x57,0xB9,0x86,0xC1,0x1D,0x9E,
0xE1,0xF8,0x98,0x11,0x69,0xD9,0x8E,0x94,0x9B,0x1E,0x87,0xE9,0xCE,0x55,0x28,0xDF,
0x8C,0xA1,0x89,0x0D,0xBF,0xE6,0x42,0x68,0x41,0x99,0x2D,0x0F,0xB0,0x54,0xBB,0x16
]);
const RCON = new Uint8Array([0x00,0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1B,0x36]);
function uint32(v){return v>>>0;}
function rotWord(w){return uint32((w<<8)|(w>>>24));}
function subWord(w){
    return uint32((SBOX[(w>>>24)&0xff]<<24)|(SBOX[(w>>>16)&0xff]<<16)|(SBOX[(w>>>8)&0xff]<<8)|SBOX[w&0xff]);
}
function expandKey(key){
    const k32=new Uint32Array(44);
    for(let i=0;i<16;i+=4)k32[i/4]=(key[i]<<24)|(key[i+1]<<16)|(key[i+2]<<8)|key[i+3];
    for(let i=4;i<44;i++){
        let t=k32[i-1];
        if(i%4===0){
            t=rotWord(t);
            t=subWord(t);
            t=uint32(t^(RCON[i/4]<<24));
        }
        k32[i]=uint32(k32[i-4]^t);
    }
    const out=new Uint8Array(176);
    for(let i=0;i<44;i++){
        out[i*4]=(k32[i]>>>24)&0xff;
        out[i*4+1]=(k32[i]>>>16)&0xff;
        out[i*4+2]=(k32[i]>>>8)&0xff;
        out[i*4+3]=k32[i]&0xff;
    }
    return out;
}
function xtime(b){
    let x=(b<<1)&0xff;
    if(b&0x80)x^=0x1b;
    return x;
}
function aesEncBlock(keyExp,block){
    const st=new Uint8Array(block);
    for(let r=0;r<16;r++)st[r]^=keyExp[r];
    for(let round=1;round<=10;round++){
        for(let i=0;i<16;i++)st[i]=SBOX[st[i]];
        for(let c=1;c<4;c++){
            for(let r=0;r<4;r++){
                const t=st[r+c*4];
                st[r+c*4]=st[r+(c-1)*4];
                st[r+(c-1)*4]=t;
            }
        }
        if(round!==10){
            for(let col=0;col<4;col++){
                const i=col*4;
                const a0=st[i],a1=st[i+1],a2=st[i+2],a3=st[i+3];
                st[i]=xtime(a0)^xtime(a1)^a1^a2^a3;
                st[i+1]=a0^xtime(a1)^xtime(a2)^a2^a3;
                st[i+2]=a0^a1^xtime(a2)^xtime(a3)^a3;
                st[i+3]=xtime(a0)^a0^a1^a2^xtime(a3);
            }
        }
        const off=round*16;
        for(let i=0;i<16;i++)st[i]^=keyExp[off+i];
    }
    return st;
}
function ghash(h,data){
    const X=new Uint8Array(16);
    let v0=0n,v1=0n;
    const H=BigInt('0x'+Array.from(h).map(x=>x.toString(16).padStart(2,'0')).join(''));
    for(let o=0;o<data.length;o+=16){
        let blk=0n;
        const end=Math.min(o+16,data.length);
        for(let i=o;i<end;i++)blk=(blk<<8n)|BigInt(data[i]);
        if(end-o<16)blk<<=BigInt(8*(16-(end-o)));
        let tmp=(v0<<64n)|v1;
        tmp^=blk;
        let hi=tmp>>128n,lo=tmp&((1n<<128n)-1n);
        let x=lo;
        let y=H;
        let z=0n;
        for(let bit=0;bit<128;bit++){
            if((x&(1n<<127n))!==0n)z^=y;
            x<<=1n;
            if((y&1n)!==0n)y=(y>>1n)^0xe1000000000000000000000000000000n;
            else y>>=1n;
        }
        v0=z>>64n;
        v1=z&0xffffffffffffffffn;
    }
    const res=new Uint8Array(16);
    for(let i=15;i>=0;i--){
        if(i>=8){res[i]=Number(v1&0xffn);v1>>=8n;}
        else{res[i]=Number(v0&0xffn);v0>>=8n;}
    }
    return res;
}
function aesGcmDecrypt(key,nonce,ciphertext,tag){
    const keyExp=expandKey(key);
    const H=aesEncBlock(keyExp,new Uint8Array(16));
    let counter=new Uint8Array(nonce);
    const ctr=new Uint8Array(16);
    ctr.set(nonce);
    ctr.set([0,0,0,1],12);
    const plain=new Uint8Array(ciphertext.length);
    for(let o=0;o<ciphertext.length;o+=16){
        const b=aesEncBlock(keyExp,ctr);
        const take=Math.min(16,ciphertext.length-o);
        for(let i=0;i<take;i++)plain[o+i]=ciphertext[o+i]^b[i];
        let n=((ctr[12]<<24)|(ctr[13]<<16)|(ctr[14]<<8)|ctr[15])+1;
        ctr[12]=(n>>>24)&0xff;ctr[13]=(n>>>16)&0xff;ctr[14]=(n>>>8)&0xff;ctr[15]=n&0xff;
    }
    const aad=new Uint8Array(0);
    const lenA=new Uint8Array(8),lenC=new Uint8Array(8);
    const ghIn=new Uint8Array(aad.length+((-aad.length)%16)+ciphertext.length+((-ciphertext.length)%16)+16);
    ghIn.set(aad);
    ghIn.set(ciphertext,aad.length+((-aad.length)%16));
    const dv=new DataView(lenA.buffer);dv.setBigUint64(0,BigInt(aad.length*8),false);
    const dc=new DataView(lenC.buffer);dc.setBigUint64(0,BigInt(ciphertext.length*8),false);
    ghIn.set(lenA,ghIn.length-16);ghIn.set(lenC,ghIn.length-8);
    const tCalc=ghash(H,ghIn);
    const t0=aesEncBlock(keyExp,counter);
    for(let i=0;i<16;i++)tCalc[i]^=t0[i];
    for(let i=0;i<16;i++)if(tCalc[i]!==tag[i])throw new Error("tag fail");
    return plain;
}
function base64UrlDecode(s){
    s=s.replace(/-/g,'+').replace(/_/g,'/');
    while(s.length%4)s+='=';
    return Uint8Array.from(atob(s),c=>c.charCodeAt(0));
}
function parseExt(s){
    if(!s)return {};
    if(typeof s==='object')return s;
    try{return JSON.parse(s);}catch(e){return {};}
}
function mapItem(it){
    const v={};
    v.vod_id=String(it.vod_id!=null?it.vod_id:'');
    v.vod_name=String(it.vod_name||'').trim();
    v.vod_pic=it.vod_pic||'';
    let remark=String(it.vod_remarks||'');
    remark=remark.replace(/4K|蓝光|更新|高清/g,'').replace(/[★◆☆※#$■●]/g,'').replace(/\s+/g,' ').trim();
    v.vod_remarks=remark;
    return v;
}
function splitEpisodeList(playStr){
    const s=String(playStr||'').replace(/#+$/,'');
    const epsOut=[];
    const eps=s.split('#');
    for(const ep of eps){
        const p=ep.indexOf('$');
        let epName='',rawUrl=ep;
        if(p>=0){epName=ep.slice(0,p);rawUrl=ep.slice(p+1);}
        epName=epName.replace(/-?4K|-?蓝光|-?高清/g,'').replace(/[★◆☆※#$■●_-]/g,'').replace(/\s+/g,' ').trim();
        epsOut.push({epName:epName,rawUrl:rawUrl});
    }
    return epsOut;
}
function joinEpisodeList(epList){
    return epList.map(e=>(e.epName||'')+'$'+e.rawUrl).join('#');
}
async function getApi(path,pairs){
    let q='';
    if(C.token)q='token='+encodeURIComponent(C.token);
    let first=q.length===0;
    for(const k in pairs){
        if(pairs[k]===undefined||pairs[k]===null||pairs[k]==='')continue;
        q+=(first?'':'&')+k+'='+encodeURIComponent(String(pairs[k]));
        first=false;
    }
    const url=C.host+path+(q?'?'+q:'');
    let resp=null;
    try{resp=await req(url,{headers:H});}catch(e){return null;}
    if(!resp||String(resp.code)!=='200'||!resp.content)return null;
    let j=null;
    try{j=JSON.parse(resp.content);}catch(e){return null;}
    if(!j||j.code!==1)return null;
    if(j&&j.data&&j.data.token)C.token=String(j.data.token);
    else if(j&&j.token)C.token=String(j.token);
    return j;
}
async function getIndex(){
    const j=await getApi('/api.php/app/index_video',{});
    return j||{data:{}};
}
async function getNav(){
    const j=await getApi('/api.php/app/nav',{});
    return j||{list:[]};
}
const FILTER_DEFS=[
    {key:'class',name:'类型'},
    {key:'area',name:'地区'},
    {key:'lang',name:'语言'},
    {key:'year',name:'年份'}
];
function strToFilter(str){
    const items=(str||'').split(',').map(s=>s.trim()).filter(Boolean);
    const value=[{n:'全部',v:'all'}];
    for(const it of items)value.push({n:it,v:it});
    return value;
}
function buildFilters(navList){
    const filters={};
    if(!Array.isArray(navList))return filters;
    for(const c of navList){
        const te=c.type_extend;
        if(!te)continue;
        const arr=[];
        for(const def of FILTER_DEFS){
            if(te[def.key])arr.push({key:def.key,name:def.name,init:'all',value:strToFilter(te[def.key])});
        }
        if(arr.length)filters[String(c.type_id)]=arr;
    }
    return filters;
}
async function init(cfg){
    try{
        const ext=cfg&&(cfg.ext!==undefined?cfg.ext:cfg);
        const e=parseExt(ext);
        if(e.host)C.host=String(e.host).replace(/\/+$/,'');
        C.keyTried=false;
        C.playCache={};
    }catch(e){}
}
async function home(){
    const j=await getNav();
    const classes=[];
    if(j&&Array.isArray(j.list)){
        for(let i=0;i<j.list.length;i++){
            const c=j.list[i];
            if(c&&c.type_id!=null)classes.push({type_id:String(c.type_id),type_name:String(c.type_name||'')});
        }
    }
    if(cat)classes.unshift({type_id:'home',type_name:'首页'});
    const nameMap={"首页":"首页","最新电影":"电影","热播国剧":"电视剧","国漫":"动漫","国综":"综艺"};
    let filteredClasses=classes.filter(item=>nameMap.hasOwnProperty(item.type_name));
    filteredClasses=filteredClasses.map(item=>{return {type_id:item.type_id,type_name:nameMap[item.type_name]};});
    const filters=buildFilters(j&&j.list);
    return JSON.stringify({class:filteredClasses,filters:filters});
}
async function homeVod(){
    const j=await getIndex();
    const list=[];
    const seen={};
    if(j&&Array.isArray(j.list)){
        for(let i=0;i<j.list.length&&list.length<C.homeCount;i++){
            const c=j.list[i];
            if(c&&Array.isArray(c.vlist)){
                for(let k=0;k<c.vlist.length&&list.length<C.homeCount;k++){
                    const it=c.vlist[k];
                    const id=String(it.vod_id!=null?it.vod_id:'');
                    if(id&&seen[id])continue;
                    if(id)seen[id]=1;
                    list.push(mapItem(it));
                }
            }
        }
    }
    return JSON.stringify({list:list});
}
async function category(tid,pg,filter,extend){
    pg=parseInt(pg)||1;
    if(String(tid)==='home'){
        const d=JSON.parse(await homeVod());
        return JSON.stringify({list:d.list||[],page:1,pagecount:1});
    }
    const params={tid:String(tid),pg:String(pg)};
    if(extend&&typeof extend==='object'){
        for(const def of FILTER_DEFS){
            const v=extend[def.key];
            if(v&&v!=='all')params[def.key]=String(v);
        }
    }
    const j=await getApi('/api.php/app/video',params);
    if(j&&Array.isArray(j.list)){
        const list=[];
        for(let i=0;i<j.list.length;i++)list.push(mapItem(j.list[i]));
        let pagecount=parseInt(j.pagecount)||0;
        if(!pagecount)pagecount=list.length>=C.size?pg+1:pg;
        return JSON.stringify({list:list,page:pg,pagecount:pagecount});
    }
    return JSON.stringify({list:[],page:pg,pagecount:1});
}
async function search(wd,quick,pg=1){
    pg=parseInt(pg)||1;
    const j=await getApi('/api.php/app/search',{text:wd,pg:String(pg)});
    const list=[];
    if(j&&Array.isArray(j.list)){
        for(let i=0;i<j.list.length;i++)list.push(mapItem(j.list[i]));
    }
    const pagecount=list.length>=C.searchSize?pg+1:pg;
    return JSON.stringify({list:list,page:pg,pagecount:pagecount});
}
async function detail(id){
    const j=await getApi('/api.php/app/video_detail',{id:String(id)});
    const list=[];
    if(j&&j.data){
        const d=j.data;
        const vod={};
        vod.vod_id=String(d.vod_id!=null?d.vod_id:id);
        vod.vod_name=String(d.vod_name||'').trim();
        vod.vod_pic=d.vod_pic||'';
        vod.vod_content=String(d.vod_content||'');
        vod.vod_actor=d.vod_actor||'';
        vod.vod_director=d.vod_director||'';
        vod.vod_area=d.vod_area||'';
        vod.vod_lang=d.vod_lang||'';
        const yr=parseInt(d.vod_year);
        vod.vod_year=isNaN(yr)?'':yr;
        vod.vod_class=d.vod_class||'';
        let dr=String(d.vod_remarks||'');
        dr=dr.replace(/4K|蓝光|更新|高清/g,'').replace(/[★◆☆※#$■●_-]/g,'').replace(/\s+/g,' ').trim();
        vod.vod_remarks=dr;
        vod._innerLines=[];
        if(Array.isArray(d.vod_url_with_player)&&d.vod_url_with_player.length){
            for(const it of d.vod_url_with_player){
                if(!it)continue;
                const nm=it.name!=null?String(it.name):'';
                const cd=it.code!=null?String(it.code):'';
                const rawUrl=it.url!=null?it.url:'';
                vod._innerLines.push({name:nm,code:cd,url:rawUrl});
            }
            const firstLine=vod._innerLines[0];
            vod.vod_play_from="恒轩";
            vod.vod_play_url=firstLine?firstLine.url:"";
        }else{
            const fromRaw=String(d.vod_play_from||'');
            const urlRaw=String(d.vod_play_url||'');
            const fromArr=fromRaw.split('$$$');
            const urlArr=urlRaw.split('$$$');
            for(let idx=0;idx<fromArr.length;idx++){
                vod._innerLines.push({name:fromArr[idx],code:'',url:urlArr[idx]||''});
            }
            vod.vod_play_from="恒轩";
            vod.vod_play_url=vod._innerLines.length>0?vod._innerLines[0].url:"";
        }
        list.push(vod);
    }
    return JSON.stringify({list:list});
}
const PLAY_CACHE_TTL=120000;
function validPlayObj(obj){
    if(!obj||typeof obj!=='object')return null;
    const url=String(obj.url||'').trim();
    if(!/^https?:\/\//i.test(url))return null;
    return {url:url,header:obj.header||PH};
}
function localResolve(token){
    try{
        const buf=base64UrlDecode(token);
        const nonce=buf.slice(0,12);
        const ct=buf.slice(12,buf.length-16);
        const tag=buf.slice(buf.length-16);
        const decBuf=aesGcmDecrypt(C.resolveKey,nonce,ct,tag);
        const plain=Array.from(decBuf).map(c=>String.fromCharCode(c)).join('').trim();
        if(/^https?:\/\//i.test(plain))return {url:plain,header:PH};
        const jo=JSON.parse(plain);
        return validPlayObj(jo);
    }catch(e){
        return null;
    }
}
async function remoteResolve(token){
    for(const node of C.nodes){
        try{
            const u=node+"/resolve?url="+encodeURIComponent(token);
            const resp=await req(u,{headers:PH});
            if(!resp||!resp.content)continue;
            const j=JSON.parse(resp.content);
            if(parseInt(j.code||resp.code)!==200)continue;
            let data=j.data;
            if(String(j.encoding||'').toLowerCase()==="encoded"&&typeof data==="string"){
                const buf=base64UrlDecode(data);
                const nonce=buf.slice(0,12);
                const ct=buf.slice(12,buf.length-16);
                const tag=buf.slice(buf.length-16);
                const decBuf=aesGcmDecrypt(C.resolveKey,nonce,ct,tag);
                const plain=Array.from(decBuf).map(c=>String.fromCharCode(c)).join('').trim();
                data=JSON.parse(plain);
            }
            const ret=validPlayObj(data);
            if(ret)return ret;
        }catch(e){continue;}
    }
    return null;
}
async function play(flag,id,flags){
    const rawInput=String(id||'').trim();
    const cacheKey=rawInput;
    const hit=C.playCache[cacheKey];
    if(hit&&hit.url&&(Date.now()-hit.ts)<PLAY_CACHE_TTL){
        return JSON.stringify({parse:0,url:hit.url,header:hit.header||PH});
    }
    let token=rawInput;
    if(flags&&flags._innerLines&&Array.isArray(flags._innerLines)){
        const eps=splitEpisodeList(flags._innerLines[0].url);
        const targetEp=eps.find(x=>x.rawUrl===rawInput);
        if(targetEp)token=targetEp.rawUrl;
    }
    let res=localResolve(token);
    if(!res)res=await remoteResolve(token);
    if(res){
        C.playCache[cacheKey]={url:res.url,ts:Date.now(),header:res.header};
        return JSON.stringify({parse:0,url:res.url,header:res.header});
    }
    return JSON.stringify({parse:0,url:"",header:PH});
}
export function __jsEvalReturn(){
    return {
        init:init,
        home:home,
        homeVod:homeVod,
        category:category,
        categoryContent:category,
        search:search,
        detail:detail,
        play:play
    };
}
