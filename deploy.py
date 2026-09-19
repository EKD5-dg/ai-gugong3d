#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy.py —— 直连 GitHub API 更新仓库内容（绕过 git 推送协议，适配受限网络）
用法：
    python deploy.py                # 上传 index.html + README.md + vendor/
    python deploy.py a.html b.css   # 只上传指定文件（不动 vendor）
两种情况都会跳过内容与远端一致的文件，不再产生空提交。
依赖：本机 Git 凭据管理器中已保存 github.com 的凭据（git credential fill）
"""
import base64, hashlib, json, subprocess, sys, urllib.request, os

# Windows 控制台默认 GBK，打印 ✓/｜ 这类字符会 UnicodeEncodeError 把发布打断在中途
# （比 报错更糟：可能只传了一半文件）。这里统一成 ASCII 输出并允许有损编码。
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

REPO = "EKD5-dg/ai-gugong3d"
BRANCH = "main"
FILES = ["index.html", "README.md"]
VENDOR_DIR = "vendor"   # 离线依赖（Three.js 本地包），一并同步

def token():
    out = subprocess.run(["git", "credential", "fill"],
                         input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True).stdout
    pw = [l.split("=", 1)[1] for l in out.splitlines() if l.startswith("password=")]
    if not pw:
        raise SystemExit("GitHub 凭据获取失败：git credential fill 无返回，请重试或先 git push 一次以刷新凭据")
    return pw[0]

def api(path, body=None, method=None, ok404=False):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"https://api.github.com{path}", data=data,
                                 method=method or ("POST" if data else "GET"),
                                 headers={"Authorization": f"token {token()}",
                                          "Accept": "application/vnd.github+json"})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.load(resp)
    except urllib.error.HTTPError as e:
        if ok404 and e.code == 404:
            return None   # 仅 GET 查询"文件不存在"（新文件）时允许 404
        print(f"HTTP {e.code} on {path}: {e.read().decode()[:200]}")
        raise SystemExit(1)

def read(path):
    with open(path, "rb") as f:
        return f.read()

def blob_sha(data):
    """git blob 哈希；Contents API 返回的 sha 就是它，可直接比对内容是否真的变了。"""
    h = hashlib.sha1(); h.update(b"blob %d" % len(data)); h.update(b"\0"); h.update(data)
    return h.hexdigest()

def targets_of(here, argv):
    """带参数就只传这些文件；不带参数才连 vendor 一起同步。"""
    if argv:
        return [os.path.normpath(os.path.join(here, a)) for a in argv]
    ts = [os.path.join(here, f) for f in FILES]
    vdir = os.path.join(here, VENDOR_DIR)
    if os.path.isdir(vdir):
        for root, _, fs in os.walk(vdir):
            ts += [os.path.join(root, f) for f in fs]
    return ts

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    done = skipped = 0
    for path in targets_of(here, sys.argv[1:]):
        name = os.path.relpath(path, here).replace("\\", "/")
        if not os.path.isfile(path):
            print(f"[FAIL] 文件不存在：{name}"); raise SystemExit(1)
        data = read(path)
        old = api(f"/repos/{REPO}/contents/{name}?ref={BRANCH}", ok404=True)
        if old and old.get("sha") == blob_sha(data):
            skipped += 1                      # 内容一致就别再制造空提交
            continue
        payload = {"message": f"deploy: 更新 {name}", "content": base64.b64encode(data).decode(),
                   "branch": BRANCH}
        if old and "sha" in old:
            payload["sha"] = old["sha"]       # 已有文件必须带 sha 才能覆盖
        res = api(f"/repos/{REPO}/contents/{name}", payload, method="PUT")
        if not isinstance(res, dict) or not (res.get("content") or {}).get("sha"):
            print(f"[FAIL] PUT 未返回内容 sha，可能未生效：{name}")
            raise SystemExit(1)
        done += 1
        print(f"[OK] 已更新 {name}")
    print(f"完成：更新 {done} 个，跳过未变动 {skipped} 个。")
    print("线上地址： https://ai-gugong3d.pages.dev  |  https://ekd5-dg.github.io/ai-gugong3d/")

if __name__ == "__main__":
    main()
