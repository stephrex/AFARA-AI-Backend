"""Download a big file through a hostile proxy by pulling small byte ranges.

This network corrupts TLS after ~60-120KB per connection, so we request tiny
ranges (well under that), each retried on its own, and append. Resumes from
whatever is already on disk.
"""
import os, sys, time, urllib.request, urllib.error

URL = "https://huggingface.co/facebook/mms-tts-yor/resolve/main/model.safetensors"
OUT = os.path.join("models", "mms-tts-yor", "model.safetensors")
CHUNK = 48 * 1024          # under the corruption threshold
MAX_RETRY = 2000

def total_size() -> int:
    req = urllib.request.Request(URL, headers={"Range": "bytes=0-0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        # Content-Range: bytes 0-0/145xxxxx
        cr = r.headers.get("Content-Range", "")
        return int(cr.split("/")[-1])

def have() -> int:
    return os.path.getsize(OUT) if os.path.exists(OUT) else 0

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    total = None
    for _ in range(20):
        try:
            total = total_size(); break
        except Exception as e:
            print("size retry:", type(e).__name__, flush=True); time.sleep(1)
    if not total:
        print("COULD_NOT_GET_SIZE", flush=True); sys.exit(1)
    print(f"total={total} bytes ({total/1048576:.1f} MB)", flush=True)

    retries = 0
    last_report = 0
    while have() < total:
        start = have()
        end = min(start + CHUNK - 1, total - 1)
        req = urllib.request.Request(URL, headers={"Range": f"bytes={start}-{end}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if not data:
                retries += 1; continue
            with open(OUT, "ab") as f:
                f.write(data)
            if have() - last_report >= 5 * 1048576:
                last_report = have()
                print(f"{have()/1048576:.1f} / {total/1048576:.1f} MB "
                      f"({100*have()/total:.0f}%)", flush=True)
        except Exception:
            retries += 1
            if retries > MAX_RETRY:
                print("GAVE_UP at", have(), flush=True); sys.exit(1)
            time.sleep(0.3)
    print(f"DONE {have()} bytes, {retries} retries", flush=True)

main()
