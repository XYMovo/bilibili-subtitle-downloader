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

## 三、第三轮修改（3项）— P2 体验增强

### P2-1 转写取消细粒度化

| # | 修改项 | 说明 |
|---|--------|------|
| P2-1a | **块处理中取消检查** | `transcribeSingleChunk()` 返回后、特征提取后均检查 abort 信号，不再仅依赖块间检查 |
| P2-1b | **部分结果保留** | 取消转写时，若已有完成的片段，自动合并去重并返回部分结果，而非丢弃 |
| P2-1c | **点击取消按钮** | 转写按钮点击后变为"转写中...(点此取消)"，用户点击即可触发 `AbortController.abort()` |
| P2-1d | **取消后状态反馈** | 进度条显示"转写已取消，保留已完成部分..."，Toast 提示"正在取消转写..." |

### P2-2 IndexedDB 转写进度自动保存与恢复

| # | 修改项 | 说明 |
|---|--------|------|
| P2-2a | **逐块自动保存** | 每个音频分块处理完成后，自动将部分结果保存到 IndexedDB（key: `_partial_` + 域名） |
| P2-2b | **页面加载恢复** | 添加 `restoreTranscriptionResults()` 函数，页面加载时自动检测并恢复已保存的转写结果 |
| P2-2c | **视频添加时恢复** | 视频添加到列表时自动检查 IndexedDB，如有已保存结果则直接恢复显示 |
| P2-2d | **自动清理** | 转写完成/失败后自动删除临时部分保存；新转写开始时自动清理旧的部分结果 |

### P2-3 DOC 导出改用 .docx 格式

| # | 修改项 | 说明 |
|---|--------|------|
| P2-3a | **OOXML .docx 生成** | `gtDoc()` 改为 async 函数，使用 JSZip 生成标准 OOXML .docx 文件（包含 `[Content_Types].xml`、`_rels/.rels`、`word/document.xml` 等） |
| P2-3b | **回退机制** | 若 JSZip 生成失败，自动回退到旧的 Word XML 格式 |
| P2-3c | **格式标识更新** | 格式标识从 `"doc"` 改为 `"docx"`，MIME 类型映射同步更新 |
| P2-3d | **UI 更新** | 侧边栏格式选择器从 "DOC" 改为 "DOCX"，文件扩展名 `.docx` |
| P2-3e | **Blob 下载** | .docx 输出为 Blob 对象，通过 `ct()` 函数正确下载（已原生支持 Blob） |

---

## 四、导出格式详细说明

### 3.1 四种导出格式对比

| 格式 | 函数 | 输出内容 | 特点 |
|------|------|---------|------|
| **SRT** | `dt()` | 序号 + 时间轴 + 文本 | 标准字幕格式，带精确时间戳 |
| **TXT** | `gtContinuous()` | 纯连续文本 | 去除所有时间戳、序号、空行，文本前后连续不分行 |
| **MD** | `gtMarkdown()` | Markdown 文档 | 标题 + 作者 + 链接 + 连续正文，真 Markdown 语法 |
| **DOCX** | `gtDoc()` (async) | OOXML .docx 文件 | 标准Word格式，JSZip打包，所有现代Word版本可直接打开 |

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
   - **DOCX** — 需要 Word 文档时选此项，标准 .docx 格式

---

## 七、P2 代码审查 Bug 修复（3项）

| # | Bug | 严重性 | 修复 |
|---|-----|--------|------|
| Fix-1 | **取消按钮点击无效** | 🔴 严重 | `We()` 函数设置 `S.disabled=true`，disabled 按钮不接收 click 事件。移除 disabled 设置，按钮始终可点击，用 `classList.toggle('transcribing')` + innerHTML 区分状态 |
| Fix-2 | **IndexedDB 部分保存无法恢复** | 🔴 严重 | 部分保存存 `{chunks,text,language}` 但 restore 检查 `saved.srtContent`，导致永远匹配不上。添加 fallback 检查 `saved.text \|\| saved.chunks?.length`，subtitleText 也从 text/chunks 字段构建 |
| Fix-3 | **DOCX 文件名双扩展名** | 🟡 重要 | `c` 已含扩展名（如 `title.srt`），`c+".docx"` 产生 `title.srt.docx`。改用 `c.replace(/\.[^.]+$/,"")+".docx"` 替换扩展名 |

---

## 八、P3 改进实施（可用性·可视化·易用性）— 已完成

### 可用性 (Usability) — 补充修复

| # | 改进项 | 实现方式 | 优先级 | 状态 |
|---|--------|---------|--------|------|
| P3-Fix | **导出格式快速选择器** | 在 table-actions 上方添加 `#quickFormatSelect` 原生下拉框（TXT/SRT/MD/DOCX），与设置弹窗格式选择器双向同步，用户无需打开设置即可切换导出格式 | 🔴 紧急 | ✅ |

### P1 遗留修复

| # | 修复项 | 实现方式 | 优先级 | 状态 |
|---|--------|---------|--------|------|
| P1-4 Fix | **字幕重试指数退避（补全）** | P1-4 此前只在 `getBilibiliSubtitleContentByTrack` 一处实现了退避（且公式 `(3-s)` 错误），现补全 `getBilibiliSubtitle`(2处)、`getBilibiliSubtitleTracks`(1处)、`fetchSubtitleWithAid`(2处) 的退避，公式统一为 `(param+1)*1e3`（3s/2s/1s 逐步退避） | ⭐⭐ | ✅ |
| P0-Fix | **突破 64MB 消息限制** | 长视频音频解码失败需前端处理时，全量 `Array.from(audioData)` 超过 Chrome 的 64MB postMessage 限制。新增 `pendingAudioBuffers` Map 暂存缓冲区（5分钟自动清理），`getAudioDataChunk` 消息按 4MB 分块传输，sidepanel 接受分块后重构完整数组再解码 | 🔴 紧急 | ✅ |
| Bug-Fix | **srtContent undefined 崩溃** | `transcribeAudioInFrontend` 多块转写完成后引用局部变量 `f`（作用域错误），导致 `Cannot read properties of undefined (reading 'srtContent')`。修复：将 `f` 声明提升到 if 块外部，添加空值守卫 | 🔴 紧急 | ✅ |
| Default | **默认导出格式改为 Markdown + 单文件** | 默认格式 `txt`→`md`，默认模式 `zip`→`single`，同步更新 HTML 默认选中状态 | ⭐ | ✅ |

### 可用性 (Usability)

| # | 改进项 | 实现方式 | 优先级 | 状态 |
|---|--------|---------|--------|------|
| P3-1 | **字幕内容预览** | 添加 `#previewModal` 模态框，`showSubtitlePreview()` 函数，点击字幕状态列弹出预览，含复制按钮、SRT/TXT 智能格式切换、ESC 关闭 | ⭐⭐⭐ | ✅ |
| P3-2 | **视频搜索/过滤** | 添加 `#searchContainer`（搜索框+状态下拉筛选），`initSearch()` IIFE 实时过滤，为每行设置 `data-title/data-author/data-status` 属性 | ⭐⭐⭐ | ✅ |
| P3-3 | **全选/反选按钮** | 添加 `#selectAllCheckbox`、`#invertSelectionBtn`、`#selectHasSubtitleBtn`、`#selectNoSubtitleBtn`，`initSelectActions()` IIFE，每行 `row-checkbox`，表头全选复选框 | ⭐⭐ | ✅ |
| P3-4 | **操作确认对话框** | 添加 `#confirmModal` 模态框，`showConfirm()` Promise 函数，删除视频前弹出确认（显示视频标题），清空表格已有原生确认对话框 | ⭐⭐ | ✅ |
| P3-5 | **批量进度信息增强** | 添加 `#progressCountInfo` 显示区，`updateProgressCount(done,total)` 函数，批量获取字幕时显示"已处理 X/Y 个" | ⭐ | ✅ |

### 可视化 (Visualization)

| # | 改进项 | 实现方式 | 优先级 | 状态 |
|---|--------|---------|--------|------|
| P3-6 | **暗色模式** | CSS 变量系统（`--sb-bg`/`--sb-card`/`--sb-text` 等 17 个变量），`@media(prefers-color-scheme:dark)` 自动切换，适配输入框/表格/模态框/Toast 等所有组件 | ⭐⭐ | ✅ |
| P3-7 | **转写进度可视化** | `updateTranscribeChunkProgress(current,total)` 函数，在进度圆环下方显示分块进度 | ⭐⭐ | ✅ |
| P3-8 | **字幕状态色块** | `.status-badge` CSS 类（success/loading/error/none/transcribing 五种样式），暗色模式自适应，`_p3PostRender()` 自动为状态列添加色块包裹 | ⭐ | ✅ |
| P3-9 | **操作反馈微动画** | `fadeInRow` 行入场动画、按钮 `:active` 缩放、状态徽章过渡、Toast `toastPulse` 弹跳动画、按钮 hover 放大 | ⭐ | ✅ |

### 易用性 (Ease of Use)

| # | 改进项 | 实现方式 | 优先级 | 状态 |
|---|--------|---------|--------|------|
| P3-10 | **格式选择记忆** | `h()` 函数中写入 `localStorage.subbatch_last_format`，页面加载时 `restoreFormat()` 自动恢复上次格式选择 | ⭐⭐⭐ | ✅ |
| P3-11 | **一键复制字幕增强** | 复制成功后按钮变绿并显示"已复制!"（1.5秒恢复），预览模态框内置复制按钮 | ⭐⭐ | ✅ |
| P3-12 | **视频拖拽排序** | — | ⭐ | ❌ 未实现 |
| P3-13 | **键盘快捷键** | `initKeyboardShortcuts()` IIFE：Ctrl+S 导出、Ctrl+A 全选、Delete 删除选中项，输入框内不触发 | ⭐ | ✅ |

### P3 修改文件变化

| 文件 | 修改前大小 | 修改后大小 | 变化 |
|------|-----------|-----------|------|
| sidepanel.html | 44KB | 53KB | +9KB（搜索框、选择按钮、确认/预览模态框、暗色模式CSS、微动画CSS、状态色块CSS） |
| script.js | 108KB | 117KB | +9KB（showConfirm/showSubtitlePreview/updateProgressCount/updateTranscribeChunkProgress 函数、initSearch/initSelectActions/initKeyboardShortcuts IIFE、_p3PostRender 集成代码、格式记忆逻辑） |

---

## 九、已知限制

- 转写取消机制已在分块间、特征提取后、块处理后均添加检查，但 `model.generate()` 推理执行期间仍无法中断（约 10-30 秒）
- IndexedDB 转写进度保存为每个分块处理后触发，若浏览器进程被强制关闭，最后一个分块的结果可能丢失
- 扩展体积仍为 ~800MB（两个 Whisper 模型打包在扩展内），需要模型外置方案才能上架 Chrome Web Store
