# WAF 绕过参考

## 2026-05-25 实战实测（最新）

### URL 参数发现
过滤条件可通过 URL 参数直接传递（服务端过滤，比 Vue 注入更可靠）：
```
https://www.ggzy.gov.cn/deal/dealList.html?DEAL_CLASSIFY={bt_id}&DEAL_STAGE={st_id}
```
- `DEAL_CLASSIFY`: 业务类型 ID（01=工程建设, 02=政府采购, 00=不限）
- `DEAL_STAGE`: 交易阶段 ID（0001=招标公告, 0002=中标候选人, 0003=中标结果）
- 省份/时间范围：URL 参数名未知，仍走 Vue 实例注入

### WAF 产品
该网站使用 360网站卫士 / 类似 CDN WAF，特征：
- 对 headless 浏览器返回伪 404 页面（"网页暂时无法访问"）
- 对非浏览器请求静默拦截 JS/API 资源
- 有验证码机制（/information/captcha），但正常 Vue 请求流不会触发
- `wait_until="networkidle"` 容易超时，改用 `domcontentloaded` 或 `load`

### 关键发现：headed vs headless

| 模式 | 列表页 | 详情页 | 结论 |
|------|--------|--------|------|
| `headless=True`（裸） + 直连 | Vue records=0 (API 被静默拦截) | iframe 超时 | ❌ 不可用 |
| `headless=True` + 代理(境外IP) | "网页暂时无法访问" | 同上 | ❌ 不可用 |
| `headless=False` + 直连 | Vue records=20 ✅ | iframe 正常加载 ✅ | ✅ 稳定可用 |
| `headless=True` + 隐身补丁 + URL参数 | Vue records=20 ✅ | iframe 正常加载 ✅ | ✅ **2026-05-25 实测可用（列表+详情）** |

### 无头隐身模式技术方案（2026-05-25 实测成功）
```python
b = pw.chromium.launch(
    headless=True,
    args=['--disable-blink-features=AutomationControlled',
          '--no-first-run', '--no-default-browser-check']
)
ctx.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'plugins',   {get: () => [1,2,3,4,5]});
    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en']});
    if (!window.chrome) window.chrome = {runtime: {}};
""")
# 配合 URL 参数传过滤条件
pg.goto('https://www.ggzy.gov.cn/deal/dealList.html?DEAL_CLASSIFY=01&DEAL_STAGE=0001')
```
关键：**URL 参数 + 隐身补丁缺一不可**（单独隐身补丁不确定有效）

### 限流时间线（实测）
- 抓取 257 页（5000+ API 请求）→ 立即触发限流
- 冷却 2 分钟后可恢复列表页访问，但详情页仍被拦截
- 冷却 3-5 分钟后详情页恢复
- 频繁请求会导致重新触发限流
- 建议：每次抓取间隔至少 2 秒，每 50 页暂停 30 秒

### 检测方法
```python
# 检查是否被WAF拦截
info = page.evaluate("""() => {
    const vm = document.querySelector('#app').__vue__;
    return vm ? {records: vm.records.length, total: vm.ttlrow} : 'no vue';
}""")
# records=0, total=0 → 被WAF拦截
# records=20, total=10000+ → 正常
```

### 恢复访问
1. 关闭所有 Playwright 浏览器实例
2. 等待 2-4 小时（或换 IP）
3. 改用 `headless=False` 启动
4. 先在浏览器手动访问一次 ggzy.gov.cn 确认可访问

### 测试过的 HTTP 方案（均失败）
- curl + 完整浏览器 headers → 404
- requests + session + cookies → 404
- requests + captcha token → code 801（验证码错误）
- `--noproxy '*'` 直连 → 404
- 代理出口（境外 IP）→ 404

所有 HTTP 方案都不可行。必须使用真实浏览器（Playwright headed）。
