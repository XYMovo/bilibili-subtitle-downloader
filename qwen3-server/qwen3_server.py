"""
Qwen3 转录服务 — Chrome Native Messaging Host
通过 stdin/stdout JSON 与 SubBatch 扩展通信
"""
import sys
import json
import struct
import os
import traceback
from pathlib import Path

# --- 配置 ---
MODEL_CACHE_DIR = Path(__file__).parent / "models" / "qwen3"
MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(MODEL_CACHE_DIR / "huggingface")
os.environ["MODELSCOPE_CACHE"] = str(MODEL_CACHE_DIR / "modelscope")

# --- Native Messaging 协议 ---
def read_message():
    """读取 Chrome 发送的 4 字节长度前缀 + JSON 消息"""
    raw_len = sys.stdin.buffer.read(4)
    if not raw_len or len(raw_len) < 4:
        return None
    msg_len = struct.unpack('=I', raw_len)[0]
    data = sys.stdin.buffer.read(msg_len)
    return json.loads(data.decode('utf-8'))

def write_message(msg):
    """向 Chrome 发送 4 字节长度前缀 + JSON 消息"""
    data = json.dumps(msg, ensure_ascii=False).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('=I', len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()

# --- 懒加载模型 ---
_asr_model = None
_asr_model_size = None
_vad_model = None

def get_asr_model(model_size="0.6B"):
    global _asr_model, _asr_model_size
    if _asr_model is not None and _asr_model_size == model_size:
        return _asr_model
    # 释放旧模型
    if _asr_model is not None:
        del _asr_model
    from qwen3_aligner.model_loader import load_asr_model
    model_name = f"Qwen/Qwen3-ASR-{model_size}"
    _asr_model = load_asr_model(model_name)
    _asr_model_size = model_size
    return _asr_model

def run_transcription(audio_path, language="Chinese", model_size="0.6B"):
    """执行转录，返回 (full_text, segments)"""
    import torch
    import torchaudio

    # 加载音频
    waveform, sample_rate = torchaudio.load(audio_path)
    if sample_rate != 16000:
        resampler = torchaudio.transforms.Resample(sample_rate, 16000)
        waveform = resampler(waveform)
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    audio_tensor = waveform[0]

    # VAD 分段
    from FireRedVAD import FireRedVAD
    global _vad_model
    if _vad_model is None:
        _vad_model = FireRedVAD()

    segments = _vad_model.segment(audio_tensor.numpy(), 16000)
    if not segments:
        # 回退：整段转录
        segments = [{"start": 0.0, "end": len(audio_tensor) / 16000.0}]

    # 构建 chunks
    chunks = []
    for seg in segments:
        start_sample = int(seg["start"] * 16000)
        end_sample = int(seg["end"] * 16000)
        chunk_audio = audio_tensor[start_sample:end_sample]
        chunks.append({
            "audio": chunk_audio,
            "offset": seg["start"]
        })

    # 加载模型并转录
    model = get_asr_model(model_size)
    from qwen3_aligner.transcribe import transcribe_audio
    results = transcribe_audio(chunks, model, language=language)

    # 构建输出
    full_text = " ".join([r["text"] for r in results if r.get("text")])

    # 生成 SRT
    srt_lines = []
    idx = 1
    for r in results:
        text = r.get("text", "").strip()
        if not text:
            continue
        start_time = r.get("offset", 0.0)
        # 估算每个分段的时长
        end_time = start_time + max(len(text) / 5.0, 0.5)
        srt_lines.append(f"{idx}")
        srt_lines.append(f"{_format_time(start_time)} --> {_format_time(end_time)}")
        srt_lines.append(text)
        srt_lines.append("")
        idx += 1

    return full_text, results, "\n".join(srt_lines)


def _format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# --- 消息处理 ---
def handle_transcribe(msg):
    """处理转录请求"""
    audio_path = msg.get("audioPath")
    language = msg.get("language", "Chinese")
    model_size = msg.get("modelSize", "0.6B")

    if not audio_path or not os.path.exists(audio_path):
        return {"success": False, "message": f"音频文件不存在: {audio_path}"}

    try:
        full_text, segments, srt = run_transcription(audio_path, language, model_size)

        seg_list = []
        for r in segments:
            seg_list.append({
                "text": r.get("text", "").strip(),
                "lang": r.get("lang", "unknown"),
                "offset": r.get("offset", 0.0)
            })

        return {
            "success": True,
            "fullText": full_text,
            "segments": seg_list,
            "srtContent": srt,
            "language": "zh",
            "languageName": "中文",
            "engine": f"Qwen3-ASR-{model_size}"
        }
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return {"success": False, "message": f"转录失败: {str(e)}"}


def handle_ping(msg):
    """健康检查"""
    return {"success": True, "message": "Qwen3 服务就绪", "version": "1.0.0"}


HANDLERS = {
    "transcribe": handle_transcribe,
    "ping": handle_ping,
}


def main():
    # 写入就绪信号
    write_message({"type": "ready", "message": "Qwen3 转录服务已启动"})

    while True:
        msg = read_message()
        if msg is None:
            break

        request_id = msg.get("requestId", "unknown")
        action = msg.get("action", "")

        handler = HANDLERS.get(action)
        if handler:
            response = handler(msg)
        else:
            response = {"success": False, "message": f"未知 action: {action}"}

        response["requestId"] = request_id
        write_message(response)

    # 清理
    global _asr_model
    if _asr_model is not None:
        del _asr_model
    _asr_model = None


if __name__ == "__main__":
    main()
