#!/usr/bin/env python3
"""
全国公共资源交易平台 - 抓取脚本 v4
有头浏览器绕WAF + 默认页加载 + 逐条提取详情

用法:
  python3 ggzy_scraper.py              # 交互式菜单
  python3 ggzy_scraper.py 10 50        # 非交互: 10页+50条详情
  python3 ggzy_scraper.py 257 0        # 只抓列表不抓详情
"""
from playwright.sync_api import sync_playwright
import json, time, re, os, sys

for k in ["HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"]:
    os.environ.pop(k, None)

# ========== 数据 ==========
BUSINESS_TYPES = {
    "1":{"id":"01","name":"工程建设"},"2":{"id":"02","name":"政府采购"},
    "3":{"id":"03","name":"土地使用权"},"4":{"id":"04","name":"矿业权"},
    "5":{"id":"05","name":"国有产权"},"6":{"id":"00","name":"不限（全部）"},
}
TRANSACTION_STAGES = {
    "1":{"id":"0001","name":"招标/采购公告"},"2":{"id":"0002","name":"中标候选人公示"},
    "3":{"id":"0003","name":"中标结果公示"},"4":{"id":"0004","name":"更正事项"},
}
PROVINCES = {
    "1":{"id":"110000","name":"北京"},"2":{"id":"120000","name":"天津"},
    "3":{"id":"130000","name":"河北"},"4":{"id":"140000","name":"山西"},
    "5":{"id":"150000","name":"内蒙古"},"6":{"id":"210000","name":"辽宁"},
    "7":{"id":"220000","name":"吉林"},"8":{"id":"230000","name":"黑龙江"},
    "9":{"id":"310000","name":"上海"},"10":{"id":"320000","name":"江苏"},
    "11":{"id":"330000","name":"浙江"},"12":{"id":"340000","name":"安徽"},
    "13":{"id":"350000","name":"福建"},"14":{"id":"360000","name":"江西"},
    "15":{"id":"370000","name":"山东"},"16":{"id":"410000","name":"河南"},
    "17":{"id":"420000","name":"湖北"},"18":{"id":"430000","name":"湖南"},
    "19":{"id":"440000","name":"广东"},"20":{"id":"450000","name":"广西"},
    "21":{"id":"460000","name":"海南"},"22":{"id":"500000","name":"重庆"},
    "23":{"id":"510000","name":"四川"},"24":{"id":"520000","name":"贵州"},
    "25":{"id":"530000","name":"云南"},"26":{"id":"540000","name":"西藏"},
    "27":{"id":"610000","name":"陕西"},"28":{"id":"620000","name":"甘肃"},
    "29":{"id":"630000","name":"青海"},"30":{"id":"640000","name":"宁夏"},
    "31":{"id":"650000","name":"新疆"},"0":{"id":"0","name":"不限（全国）"},
}
TIME_RANGES = {
    "1":{"id":"01","name":"当天"},"2":{"id":"02","name":"近三天"},
    "3":{"id":"03","name":"近十天"},"4":{"id":"04","name":"近一月"},
    "5":{"id":"05","name":"近三月"},
}

# ========== 详情提取 ==========
def parse_detail(text):
    """从 iframe 文本提取金额/截止时间（兼容多省多格式）"""
    d={"budget_money":"","deposit_money":"","bid_deadline":"","doc_deadline":"",
       "funding_source":"","scale":"","plan_days":"","tender_agent":""}
    def cn(s):
        # 跨行日期: "2026 年06\n\n月 17 日" -> 2026-06-17
        s2=re.sub(r'\s+','',s)
        m=re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日',s2)
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else s.strip()
    for p,k in [
        (r'标段合同估算价[：:]?\s*([\d,.]+)\s*万元','budget_money'),
        (r'合同估算价[\s\S]*?([\d,.]+)\s*万元','budget_money'),
        (r'招标控制价[\s\S]*?([\d,.]+)\s*万元','budget_money'),
        (r'预算金额[：:]\s*([\d,.]+)\s*万元','budget_money'),
        (r'项目投资[：:]?\s*([\d,.]+)\s*万元','budget_money'),
        (r'投标保证金[：:]?\s*([\d,.]+)\s*万元','deposit_money'),
        (r'递交投标文件截止时间[：:]\s*(\S+)','bid_deadline'),
        (r'提交投标文件截止时间[：:]\s*(\S+)','bid_deadline'),
        (r'投标文件递交的截止时间[^。]*?(\d{4}\s*年[\s\S]*?月[\s\S]*?日)','bid_deadline'),
        (r'投标文件递交截止时间[^。\n]*?(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)','bid_deadline'),
        (r'投标截止时间[：:]?\s*(\d{4}\s*年[\s\S]*?月[\s\S]*?日)','bid_deadline'),
        (r'投标截止[：:]?\s*(\d{4}\s*年[\s\S]*?月[\s\S]*?日)','bid_deadline'),
        (r'招标文件获取截止时间[：:]\s*(\S+)','doc_deadline'),
        (r'获取招标文件[^。\n]*?(\d{4}\s*年[\s\S]*?月[\s\S]*?日)','doc_deadline'),
        (r'资金来源[：:]\s*(.+?)(?:\n|$)', 'funding_source'),
        (r'建设资金来自[^。]*?(\S+?)(?:[，。]|$)', 'funding_source'),
        (r'计划工期[：(（]*(?:日历天[)）]?\s*)?[：:]?\s*(\d+)','plan_days'),
        (r'服务期限\s*\n[^\n]*\n[^\n]*?(\d+)\s*天','plan_days'),
        (r'工期[：:]?\s*(\d+)\s*天','plan_days'),
        (r'招标代理机构[：:]\s*(\S+)','tender_agent'),
        (r'招标代理人[：:]\s*(\S+)','tender_agent'),
        (r'建设规模[：:]\s*(.+?)(?:\n|。|$)','scale'),
        (r'工程规模[：:]\s*(.+?)(?:\n|。|$)','scale'),
        (r'项目规模[：:]\s*(.+?)(?:\n|。|$)','scale'),
    ]:
        m=re.search(p,text)
        if m and not d[k]:
            v=m.group(1).strip()
            if k in ('bid_deadline','doc_deadline'): v=cn(v)
            d[k]=v[:200] if k in ('funding_source','scale','tender_agent') else v
    return d

# ========== 菜单 ==========
def menu(title,items):
    print(f"\n{'='*50}\n  {title}\n{'='*50}")
    for k,v in items.items(): print(f"  {k}. {v['name']}")
    while True:
        c=input("  请选择: ").strip()
        if c in items: return items[c]
        print("  输入无效")

# ========== 主函数 ==========
def run(max_pages=10, max_details=50, headless=False):
    """非交互式运行（使用默认过滤：工程建设/招标公告/全国/近三天）"""
    print(f"启动{'无头隐身' if headless else '有头'}浏览器...")
    print(f"设置: {max_pages}页, 最多{max_details}条详情")
    default_filters={
        'business_type': BUSINESS_TYPES['1'],
        'transaction_stage': TRANSACTION_STAGES['1'],
        'province': PROVINCES['0'],
        'time_range': TIME_RANGES['2'],
    }
    _do_scrape(max_pages, max_details, default_filters, info_type="招标/资审公告", headless=headless)

def run_interactive():
    """交互式运行"""
    print("\n📋 全国公共资源交易平台 - 招标数据抓取")
    print("="*50)
    bt=menu("选择业务类型",BUSINESS_TYPES)
    st=menu("选择交易阶段",TRANSACTION_STAGES)
    pv=menu("选择省份",PROVINCES)
    tr=menu("选择发布时间",TIME_RANGES)
    
    p=input("\n翻页数（每页20条，默认10页）: ").strip()
    pages=int(p) if p.isdigit() else 10
    d=input("抓详情条数（0=不抓，默认20）: ").strip()
    details=int(d) if d.isdigit() else 20
    
    it=input("\n只保留信息类型（留空=不过滤，默认=招标/资审公告）: ").strip()
    info_type=it if it else "招标/资审公告"
    hl=input("使用无头隐身模式？有被WAF拦截风险（y=无头/N=有头[推荐]）: ").strip().lower()
    headless=(hl=='y')
    
    print(f"\n{'='*50}")
    print(f"  业务: {bt['name']} | 阶段: {st['name']}")
    print(f"  省份: {pv['name']} | 时间: {tr['name']}")
    print(f"  翻页: {pages}页 | 详情: {details}条 | 类型: {info_type or '无'} | 模式: {'无头隐身' if headless else '有头'}")
    if input("\n开始抓取？(y/N): ").strip().lower()!='y':
        print("已取消"); return
    filters={
        'business_type': bt,
        'transaction_stage': st,
        'province': pv,
        'time_range': tr,
    }
    _do_scrape(pages, details, filters, info_type=info_type or None, headless=headless)

_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins',   {get: () => [1,2,3,4,5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en']});
if (!window.chrome) window.chrome = {runtime: {}};
const _origQuery = window.navigator.permissions ? window.navigator.permissions.query : null;
if (_origQuery) {
    window.navigator.permissions.query = p =>
        p.name === 'notifications'
        ? Promise.resolve({state: Notification.permission})
        : _origQuery(p);
}
"""

def _build_url(filters):
    """用 URL 参数传递业务类型和交易阶段（省份/时间仍走 Vue 注入）"""
    bt = filters['business_type']['id']
    st = filters['transaction_stage']['id']
    return f'https://www.ggzy.gov.cn/deal/dealList.html?DEAL_CLASSIFY={bt}&DEAL_STAGE={st}'

def _apply_vue_filters(pg, filters):
    """通过 Vue 实例注入省份/时间范围（URL 参数无法覆盖的维度）"""
    pv_id = filters['province']['id']
    tr_id = filters['time_range']['id']
    js = f"""
    (function(){{
        const vm = document.querySelector('#app').__vue__;
        if (!vm) return 'no-vue';
        function set(candidates, val) {{
            for (const k of candidates) {{ if (k in vm) {{ vm[k]=val; return; }} }}
        }}
        set(['province','provinceCode','areaCode'], '{pv_id}');
        set(['publishTimeType','timeRange','dateRange','timeType'], '{tr_id}');
        const fn = vm.doSearch || vm.search || vm.getData || vm.loadData || vm.goToPage;
        if (fn) {{ fn.call(vm, 1); return 'ok'; }}
        return 'no-search-fn';
    }})()
    """
    result = pg.evaluate(js)
    print(f"Vue 省份/时间注入: {result}")
    time.sleep(3)

def _check_waf(pg):
    """检查是否被 WAF 拦截（records=0 且 total=0 为拦截特征）"""
    info = pg.evaluate("""() => {
        const vm = document.querySelector('#app').__vue__;
        if (!vm) return {ok: false, reason: 'no-vue'};
        return {ok: (vm.records||[]).length > 0, records: (vm.records||[]).length, total: vm.ttlrow||0};
    }""")
    return info

def _do_scrape(max_pages, max_details, filters, info_type="招标/资审公告", headless=False, out_path=None):
    """核心抓取逻辑。
    headless: True=无头隐身模式（需WAF不拦截），False=有头模式（默认/稳定）
    info_type: 按 informationTypeText 包含过滤，None=不过滤
    out_path: Excel 输出路径，None=默认桌面
    """
    all_records=[]
    dc=0
    filtered_out=0
    url = _build_url(filters)
    mode_label = "无头隐身" if headless else "有头"

    with sync_playwright() as pw:
        launch_args = ['--disable-blink-features=AutomationControlled',
                       '--no-first-run', '--no-default-browser-check']
        b = pw.chromium.launch(headless=headless, args=launch_args)
        ctx = b.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            locale='zh-CN',
            viewport={'width':1920,'height':1080})
        if headless:
            ctx.add_init_script(_STEALTH_SCRIPT)
        pg = ctx.new_page()

        print(f"\n加载页面（{mode_label}模式）...")
        print(f"URL: {url}")
        pg.goto(url, wait_until='load', timeout=60000)
        time.sleep(15)

        # WAF 检测
        waf = _check_waf(pg)
        if waf.get('ok'):
            print(f"  ✅ WAF 检测通过: records={waf.get('records',0)}, total={waf.get('total',0)}")
        else:
            if headless:
                print(f"  ⚠️ WAF 检测: records={waf.get('records',0)}, total={waf.get('total',0)}")
                print("  ⚠️ 无头模式被WAF拦截！建议改用 headless=False（有头模式）")
                b.close(); return
            else:
                print(f"  ⚠️ 页面数据为空，可能被限流。records={waf.get('records',0)}")

        print(f"应用过滤: 业务={filters['business_type']['name']} 阶段={filters['transaction_stage']['name']} "
              f"省份={filters['province']['name']} 时间={filters['time_range']['name']}")
        # URL 已处理业务类型和阶段，再通过 Vue 注入省份/时间
        _apply_vue_filters(pg, filters)
        
        for pn in range(1,max_pages+1):
            if pn>1:
                pg.evaluate(f'document.querySelector("#app").__vue__.goToPage({pn})')
                time.sleep(2)
            
            # 每 50 页暂停 30s，降低限流风险
            if pn>1 and (pn-1)%50==0:
                print(f"  ⏸ 已翻{pn-1}页，暂停30s冷却...")
                time.sleep(30)
            
            recs=pg.evaluate('()=>{const v=document.querySelector("#app").__vue__;return v?JSON.parse(JSON.stringify(v.records)):[]}')
            if not recs:
                # 区分「数据抓完」vs「WAF 中途踢掉」
                waf_mid=_check_waf(pg)
                if not waf_mid.get('ok') and waf_mid.get('records',0)==0 and pn>1:
                    print(f"  ⚠️ 第{pn}页 WAF 中途拦截，暂停30s后重试...")
                    time.sleep(30)
                    recs=pg.evaluate('()=>{const v=document.querySelector("#app").__vue__;return v?JSON.parse(JSON.stringify(v.records)):[]}')
                    if not recs:
                        print(f"  ⚠️ 重试失败，停止抓取"); break
                    print(f"  ✅ 重试成功，继续第{pn}页")
                else:
                    print(f"第{pn}页: 无更多数据，完成"); break
            
            # 按信息类型过滤
            if info_type:
                before=len(recs)
                recs=[r for r in recs if info_type in r.get('informationTypeText','')]
                skip=before-len(recs)
                if skip: filtered_out+=skip
            
            # 逐条点开详情
            if max_details and dc<max_details:
                for idx,r in enumerate(recs):
                    if dc>=max_details: break
                    u=r.get('url','')
                    if not u: continue
                    try:
                        dp=ctx.new_page()
                        dp.goto(f'https://www.ggzy.gov.cn{u}',wait_until='domcontentloaded',timeout=30000)
                        try: dp.wait_for_selector('iframe',timeout=10000)
                        except Exception: dp.close(); continue
                        time.sleep(1.5)
                        for f in dp.frames:
                            if '/information/deal/html/b/' in f.url:
                                r.update(parse_detail(f.evaluate('()=>document.body.innerText')))
                                dc+=1
                                parts=[]
                                if r.get('budget_money'): parts.append(f"💰{r['budget_money']}万")
                                if r.get('bid_deadline'): parts.append(f"截标:{r['bid_deadline']}")
                                if r.get('plan_days'): parts.append(f"工期:{r['plan_days']}天")
                                if parts: print(f"  [{pn}-{idx}] {' '.join(parts)}")
                                break
                        dp.close()
                        time.sleep(0.5)
                    except Exception as e:
                        print(f"  ⚠️ 详情抓取失败 [{pn}-{idx}]: {e}")
            
            all_records.extend(recs)
            print(f"第{pn}页: {len(recs)}条 (详情{dc})")
        
        out="/tmp/ggzy_records.json"
        with open(out,'w',encoding='utf-8') as f:
            json.dump(all_records,f,ensure_ascii=False)
        hb=sum(1 for r in all_records if r.get("budget_money"))
        filter_note=f", 过滤非{info_type}:{filtered_out}条" if info_type and filtered_out else ""
        print(f"\n✅ 完成! {len(all_records)}条{filter_note}, 详情{dc}条(含预算{hb})")
        print(f"保存: {out}")
        
        # 自动生成Excel
        _gen_excel(all_records, out_path=out_path)
        b.close()

def _gen_excel(records, out_path=None):
    """生成Excel。out_path: 自定义路径，None=默认桌面"""
    import openpyxl
    from openpyxl.styles import Font,PatternFill,Alignment,Border,Side
    wb=openpyxl.Workbook()
    ws=wb.active; ws.title="招标公告"
    hdrs=["序号","标题","发布时间","省份","来源平台","业务类型","信息类型","行业",
          "预算(万元)","保证金(万元)","投标截止时间","文件获取截止","资金来源","计划工期(天)","招标代理","URL"]
    hf=Font(bold=True,color="FFFFFF",size=11); hfl=PatternFill(start_color="1F4E79",end_color="1F4E79",fill_type="solid")
    df=Font(size=10); lf=Font(size=10,color="0563C1",underline="single"); bf=Font(size=10,color="C00000")
    bd=Border(left=Side(style='thin',color='D0D0D0'),right=Side(style='thin',color='D0D0D0'),
              top=Side(style='thin',color='D0D0D0'),bottom=Side(style='thin',color='D0D0D0'))
    af=PatternFill(start_color="F2F7FB",end_color="F2F7FB",fill_type="solid")
    bff=PatternFill(start_color="FFF3E0",end_color="FFF3E0",fill_type="solid")
    cc=Alignment(horizontal='center',vertical='center'); lc=Alignment(horizontal='left',vertical='center',wrap_text=True)
    for col,h in enumerate(hdrs,1):
        c=ws.cell(row=1,column=col,value=h); c.font=hf; c.fill=hfl; c.alignment=cc; c.border=bd
    for i,w in enumerate([6,40,12,8,24,10,12,12,10,10,16,14,20,10,20,60],1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width=w
    ccs={1,3,4,7,8,9,10,13,14}
    for idx,rec in enumerate(records,1):
        row=idx+1; up=rec.get("url",""); fu=f"https://www.ggzy.gov.cn{up}" if up and not up.startswith("http") else up
        vals=[idx,rec.get("title",""),rec.get("publishTime",""),rec.get("provinceText",""),
              rec.get("transactionSourcesPlatformText",""),rec.get("businessTypeText",""),
              rec.get("informationTypeText",""),rec.get("industryTypeText",""),
              rec.get("budget_money",""),rec.get("deposit_money",""),rec.get("bid_deadline",""),
              rec.get("doc_deadline",""),rec.get("funding_source",""),rec.get("plan_days",""),
              rec.get("tender_agent",""),fu]
        for col,val in enumerate(vals,1):
            c=ws.cell(row=row,column=col,value=val); c.font=df; c.border=bd
            c.alignment=cc if col in ccs else lc
            if idx%2==0: c.fill=af
            if col in(9,10) and val: c.font=bf; c.fill=bff
        uc=ws.cell(row=row,column=16)
        if fu: uc.hyperlink=fu; uc.font=lf
    ws.freeze_panes="A2"; ws.auto_filter.ref=f"A1:P{len(records)+1}"
    out=os.path.expanduser(out_path) if out_path else os.path.expanduser("~/Desktop/招标公告_数据.xlsx")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    wb.save(out)
    print(f"Excel: {out}")

if __name__=="__main__":
    if len(sys.argv)>1:
        run(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv)>2 else 50)
    else:
        run_interactive()
