#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy.py —— 直连 GitHub API 更新仓库内容（绕过 git 推送协议，适配受限网络）
用法：
    python deploy.py                # 上传 index.html + README.md
    python deploy.py a.html b.css   # 上传指定文件
依赖：本机 Git 凭据管理器中已保存 github.com 的凭据（git credential fill）
"""
import base64, json, subprocess, sys, urllib.request, os

REPO = "EKD5-dg/ai-gugong3d"
BRANCH = "main"
FILES = ["index.html", "README.md"]

def token():
    out = subprocess.run(["git", "credential", "fill"],
                         input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True).stdout
    return [l.split("=", 1)[1] for l in out.splitlines() if l.startswith("password=")][0]

def api(path, body=None, method=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"https://api.github.com{path}", data=data,
                                 method=method or ("POST" if data else "GET"),
                                 headers={"Authorization": f"token {token()}",
                                          "Accept": "application/vnd.github+json"})
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} on {path}: {e.read().decode()[:200]}")
        raise SystemExit(1)

def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def main():
    names = sys.argv[1:] or FILES
    here = os.path.dirname(os.path.abspath(__file__))
    for name in names:
        path = os.path.join(here, name)
        payload = {"message": f"deploy: 更新 {name}", "content": b64file(name), "branch": BRANCH}
        try:
            old = api(f"/repos/{REPO}/contents/{name}?ref={BRANCH}")
            payload["sha"] = old["sha"]
        except SystemExit:
            pass
        api(f"/repos/{REPO}/contents/{name}", payload, method="PUT")
        print(f"✓ 已更新 {name}")
    print("完成。线上地址：https://ekd5-dg.github.io/ai-gugong3d/")

if __name__ == "__main__":
    main()
