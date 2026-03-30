# AI 新聞語音查詢 Skill

_定期搜尋熱門 AI 新聞，並用本地 TTS 語音發送給你，同時附上逐字稿。_

## 用途

- 每週/每日 AI 新聞自動摘要
- 用本地 TTS（sherpa-onnx vits-melo-tts-zh_en）語音發送
- 附上完整逐字稿文字
- 離線語音，無需 API key

## 調用方式

### 指令格式

```
搜尋 AI 新聞前五條，用語音發給我，並附上逐字稿
```

### 自動執行流程

1. 搜尋網路熱門 AI 新聞（5 則）
2. 生成逐字稿摘要
3. 用 sherpa-onnx TTS 生成語音檔案
4. 用 Telegram Bot 發送語音 + 逐字稿文字

## 技術細節

### TTS 工具

- **模型**: `vits-melo-tts-zh_en`（中文 + 英文，支援中英混合）
- **路徑**: `$HOME/.openclaw/tools/sherpa-onnx-tts/`
- **環境變數**:
  ```bash
  export SHERPA_ONNX_RUNTIME_DIR="$HOME/.openclaw/tools/sherpa-onnx-tts/runtime"
  export SHERPA_ONNX_MODEL_DIR="$HOME/.openclaw/tools/sherpa-onnx-tts/vits-melo-tts-zh_en"
  ```

### 語音生成命令

```bash
$SHERPA_ONNX_RUNTIME_DIR/bin/sherpa-onnx-offline-tts \
  --vits-model="$SHERPA_ONNX_MODEL_DIR/model.onnx" \
  --vits-lexicon="$SHERPA_ONNX_MODEL_DIR/lexicon.txt" \
  --vits-tokens="$SHERPA_ONNX_MODEL_DIR/tokens.txt" \
  --output-filename="/Users/aiserver/.openclaw/workspace/audio/ai_news_tts.wav" \
  "要轉換的中文文字"
```

### 新聞搜尋

- 使用 `web_search` 工具
- 搜尋關鍵詞：`AI news technology artificial intelligence`
- 限制結果：5 則
- 時間範圍：過去一週

## 範例輸出

```
嗨，Alan。我為你搜尋到五則熱門的 AI 新聞。

第一則，小米神秘 AI 模型揭曉。路透社報導，小米的 AI 模型團隊 MiMo，確認 Hunter Alpha 是 MiMo-V2-Pro 的早期內部測試版本。

第二則，中國接納 OpenClaw，政府警覺。紐約時報報導，OpenClaw 這個新 AI Agent 的興起，以及政府對它的警覺，凸顯了 AI 競賽如何重塑中國科技產業。

...（其他新聞）
```

## 權限與限制

- **查詢範圍**: 公開技術新聞、技術趨勢
- **禁止**: 敏感議題、未公開機密、個人隱私
- **語音**: 本地離線 TTS，無需額外授權

## 相關工具

- `web_search` - 搜尋網路新聞
- `tts` - 文字轉語音（本 Skill 使用 `exec` 直接調用 sherpa-onnx）
- `message` - 發送語音檔案和文字

## 檔案位置

- **Skill 目錄**: `skills/ai-news-tts/`
- **語音存檔**: `audio/ai_news_tts.wav`

## 版本

- **V1.0** - 2026-03-19 建立
- **TTS 版本**: sherpa-onnx vits-melo-tts-zh_en

---

_維護者：Yvonne_
