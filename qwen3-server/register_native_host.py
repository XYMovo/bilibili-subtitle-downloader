"""
注册 Chrome Native Messaging Host
用法: python register_native_host.py
"""
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
MANIFEST_FILE = SCRIPT_DIR / "com.subbatch.qwen3.json"
BAT_FILE = SCRIPT_DIR / "qwen3_server.bat"

def register():
    # 读取清单
    with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    # 更新路径
    manifest["path"] = str(BAT_FILE)

    # Chrome Native Messaging 注册目录
    home = Path.home()
    if sys.platform == "win32":
        target_dir = home / "AppData" / "Local" / "Google" / "Chrome" / "NativeMessagingHosts"
        registry_key = r"HKCU\Software\Google\Chrome\NativeMessagingHosts\com.subbatch.qwen3"
    elif sys.platform == "darwin":
        target_dir = home / "Library" / "Application Support" / "Google" / "Chrome" / "NativeMessagingHosts"
        registry_key = None
    else:
        target_dir = home / ".config" / "google-chrome" / "NativeMessagingHosts"
        registry_key = None

    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "com.subbatch.qwen3.json"

    with open(target_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"[OK] Native Messaging Host 已注册")
    print(f"  清单文件: {target_file}")
    print(f"  执行文件: {BAT_FILE}")

    # Windows 注册表
    if sys.platform == "win32":
        import subprocess
        try:
            subprocess.run(
                ["reg", "add", registry_key, "/ve", "/d", str(target_file), "/f"],
                capture_output=True, check=True
            )
            print(f"  注册表:   {registry_key}")
        except Exception as e:
            print(f"  [警告] 注册表写入失败: {e}")
            print(f"  请手动运行:")
            print(f'  reg add "{registry_key}" /ve /d "{target_file}" /f')

    print(f"\n请在 Chrome 扩展的 background.js 中使用扩展 ID 替换 __EXTENSION_ID__")
    print(f"扩展 ID 可在 chrome://extensions 页面查看")


if __name__ == "__main__":
    register()
