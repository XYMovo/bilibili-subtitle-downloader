# SubBatch v2.0.0 修改报告

## 修改日期：2026-06-14

---

## 一、第一轮修改（9项）— 基础功能修复

| # | 修改项 | 文件 | 修改内容 |
|---|--------|------|---------|
| 1 | 时长限制突破 | script.js | `>3600` → `>9000`（60分钟 → 2.5小时） |
| 2 | 音频解码缓冲区 | background.js | OfflineAudioContext `3600*e` → `9000*e` |
| 3 | 下载超时延长 | background.js | 3分钟 → 10分钟（`18e4` → `6e5`） |
| 4 | SW WhisperTranscriber 释放 | background.js | 添加 `dispose()` 方法，转写完成/失败后自动调用 |
| 5 | Service Worker 保活 | background.js + manifest.json | chrome.alarms 每 27 秒 ping + `"alarms"` 权限 |
| 6 | postMessage 安全加固 | background.js | 4 处 `"*"` → `"https://www.bilibili.com"` |
| 7 | WBI Key 获取去重 | background.js | `_wbiKeysPending` Promise 防并发重复请求 |
| 8 | PCM 转换精度修正 | background.js | `32767` → `32768` 消除 DC 偏移 |
| 9 | Bridge 竞态修复 | background.js | bridge 注入后添加 200ms 延迟 |

---

## 二、第二轮修改（10项）— P0 稳定性 + P1 体验提升

### P0 核心稳定性（6项）

| # | 修改项 | 说明 |
|---|--------|------|
| P0-1 | **前端 Whisper 模型释放** | 添加 `disposeFrontendWhisper()` 函数，转写完成/失败后释放 model/processor/tokenizer 三个全局变量，回收 ~500MB 显存/内存 |
| P0-2 | **转写取消机制** | 添加 `isTranscribing` 锁 + `transcriptionAbortController`（AbortController），分块推理循环中检测取消信号，用户可中途终止 |
| P0-3 | **offscreen 死代码清理** | 删除 `offscreen.html`，移除 manifest 中 `offscreen` 权限和 web_accessible_resources 声明 |
| P0-4 | **模型加载互斥锁** | 添加 `_modelInitPromise` 变量，并发调用 `initFrontendWhisper` 共享同一个 Promise，防止重复加载导致内存翻倍 |
| P0-5 | **Toast 监听器** | 复查确认原有 3 秒自动清理 + 点击清理机制已正确实现，无需修改 |
| P0-6 | **IndexedDB 中间结果持久化** | 创建 `subbatch-store` 数据库，转写结果自动保存到 IndexedDB，侧栏关闭后可恢复 |

### P1 体验提升（4项）

| # | 修改项 | 说明 |
|---|--------|------|
| P1-1 | **DOM DocumentFragment 优化** | `et()` 表格重建改为 DocumentFragment 批量插入，减少 DOM 回流次数，50+ 视频时提升明显 |
| P1-2 | **真多格式连续文本导出** | 新增三种导出格式函数，导出文本前后连续不分行（见下方详细说明） |
| P1-3 | **音频下载进度反馈** | `downloadAudioDirectly` 改用 ReadableStream 流式下载，通过 `audioDownloadProgress` 消息实时上报下载进度百分比 |
| P1-4 | **字幕重试指数退避** | 固定 1s 重试 → 指数退避 `1s×(3-retries)`，依次等待 3s/2s/1s |

---

## 三、导出格式详细说明

### 3.1 四种导出格式对比

| 格式 | 函数 | 输出内容 | 特点 |
|------|------|---------|------|
| **SRT** | `dt()` | 序号 + 时间轴 + 文本 | 标准字幕格式，带精确时间戳 |
| **TXT** | `gtContinuous()` | 纯连续文本 | 去除所有时间戳、序号、空行，文本前后连续不分行 |
| **MD** | `gtMarkdown()` | Markdown 文档 | 标题 + 作者 + 链接 + 连续正文，真 Markdown 语法 |
| **DOC** | `gtDoc()` | Word XML 文档 | Microsoft YaHei 字体，段落分隔，Word 可直接打开 |

### 3.2 连续文本的实现

**之前的 gt() 函数**：每行字幕一个换行，中英文混排时空格不统一，输出是一段一段的。

**新的 gtContinuous() 函数**：
- 去除所有 SRT 格式标记（序号、时间轴 `-->`、空行）
- 中文文本：逐句拼接，自然段以中文句号等标点分段
- 英文文本：句子之间用空格连接，自然流畅
- `cleanTranscriptionText()` 仍然生效，去除口语词和重复
- 最终输出：一段完整的、前后连续的文本，不是一行一行分开的

### 3.3 示例输出对比

**SRT 格式**：
```
1
00:00:01,000 --> 00:00:03,000
大家好

2
00:00:03,500 --> 00:00:06,000
今天我们来聊一下

3
00:00:06,500 --> 00:00:09,000
关于AI字幕的技术
```

**TXT 格式（连续文本）**：
```
大家好今天我们来聊一下关于AI字幕的技术
```

**MD 格式**：
```markdown
# 视频标题

**作者:** UP主名称

**链接:** https://www.bilibili.com/video/BV1xxxxxx

大家好今天我们来聊一下关于AI字幕的技术
```

---

## 四、修改后文件清单

| 文件 | 修改前大小 | 修改后大小 | 变化 |
|------|-----------|-----------|------|
| background.js | 63KB | 57KB | 减小（流式下载优化） |
| script.js | 108KB | 102KB | 增大（新增格式函数、IndexedDB、取消机制） |
| manifest.json | - | 1.5KB | 移除 offscreen，保留 alarms |
| offscreen.html | 1.5KB | 已删除 | - |

---

## 五、使用说明

1. 打开 Chrome，访问 `chrome://extensions`
2. 开启"开发者模式"
3. 点击"加载已解压的扩展程序"，选择 `C:\Users\XYM\Downloads\subbatch-local-v2.0.0`
4. 在 B站视频页面点击扩展图标，侧边栏打开
5. 导出时选择格式：
   - **SRT** — 需要字幕时间轴时选此项
   - **TXT** — 只需要纯文本内容时选此项，输出连续不分行
   - **MD** — 需要 Markdown 格式时选此项
   - **DOC** — 需要 Word 文档时选此项

---

## 六、已知限制

- 转写取消机制仅在分块边界生效（每 30 秒一个检查点），无法在推理中途取消
- IndexedDB 持久化目前仅在 `pe()` 函数存储结果时触发保存，手动关闭侧栏前未完成的转写无法恢复
- DOC 导出为 Word XML 格式（.doc 扩展名），部分旧版 Word 可能需要用 WPS 或 Word 2016+ 打开
- 扩展体积仍为 ~800MB（两个 Whisper 模型打包在扩展内），需要模型外置方案才能上架 Chrome Web Store
