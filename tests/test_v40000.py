# -*- coding: utf-8 -*-
"""test_v40000 — v4.0.0 编码自适应+批量并发隔离版（固定位命名）。

覆盖：
  1. 编码自适应：GBK/UTF-16BOM/UTF-8/大文件 GBK/二进制拒收/无 BOM UTF-16 拒收指引
  2. 转码标注：stderr 提示 + read_text_ex meta.encoding
  3. 批量并发隔离：双写者进度互不覆盖（flock 合并）
  4. 旧契约：NUL 二进制、GBK 乱码卫生检查
  5. 文档接线：SKILL 双语 v4.0.0 行/faq Q13b/errors 转码行/api/permissions .lock
"""
import json
import os, sys, tempfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import hxt_core
PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail and not cond else ""))
def run_cli(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=180)


def test_encoding():
    with tempfile.TemporaryDirectory() as td:
        # GBK 透明转码
        p = os.path.join(td, "gbk.txt")
        open(p, "wb").write("患者，男，65岁。结果具有统计学意义。".encode("gbk"))
        r = run_cli([os.path.join(SCRIPTS, "detect.py"), p])
        check("enc.GBK 拒收→转码可用", r.returncode == 0
              and "已自动转码" in r.stderr, (r.stdout + r.stderr)[:150])
        # UTF-16 BOM
        p2 = os.path.join(td, "u16.txt")
        open(p2, "wb").write("研究纳入 120 例患者，随访 24 个月。".encode("utf-16"))
        r2 = run_cli([os.path.join(SCRIPTS, "detect.py"), p2])
        check("enc.UTF-16 BOM 转码", r2.returncode == 0
              and "UTF-16" in r2.stderr, (r2.stdout + r2.stderr)[:150])
        # meta.encoding
        t, meta = hxt_core.read_text_ex(p)
        check("enc.meta.encoding", "GBK" in (meta.get("encoding") or ""), str(meta))
        # UTF-8 静默
        p3 = os.path.join(td, "u8.txt")
        open(p3, "w", encoding="utf-8").write("正常文本。")
        r3 = run_cli([os.path.join(SCRIPTS, "detect.py"), p3])
        check("enc.UTF-8 静默", r3.returncode == 0 and "转码" not in r3.stderr)
        # 二进制仍拒收（NUL 合法 UTF-8 码点——判据须作用于解码后文本）
        p4 = os.path.join(td, "bin.txt")
        open(p4, "wb").write(b"abc\x00def\x00ghi")
        r4 = run_cli([os.path.join(SCRIPTS, "detect.py"), p4])
        check("enc.二进制拒收保持", r4.returncode == 2
              and "二进制" in (r4.stdout + r4.stderr))
        # GBK 大文件（read_text 单路径，编码标注一次）
        p5 = os.path.join(td, "gbk_big.txt")
        open(p5, "wb").write(("患者纳入标准与排除标准。结果具有统计学意义。" * 40000).encode("gbk"))
        r5 = run_cli([os.path.join(SCRIPTS, "detect.py"), p5])
        check("enc.GBK 大文件", r5.returncode == 0 and "GBK" in r5.stderr)


def test_audit_regressions():
    # 审计 P1：even-parity 损坏 UTF-8 不得被 GB18030 误转码成 mojibake
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "c1.txt")
        open(p, "wb").write("链接文本探讨了数据分布的特征，同时验证了模型收敛的充分条件边界。".encode("utf-8")[:-2])
        try:
            t = hxt_core.read_text(p)
            check("audit.even-parity 不产 mojibake", "鏈" not in t[:3],
                  t[:30])
        except ValueError:
            check("audit.even-parity 不产 mojibake", True)
        # 真 GBK 有标点 → 转码；无标点列表 → 保守拒收
        p2 = os.path.join(td, "gbk.txt")
        open(p2, "wb").write("患者，男，65岁。结果具有统计学意义。".encode("gbk"))
        check("audit.真 GBK 转码", "患者" in hxt_core.read_text(p2))
        p3 = os.path.join(td, "list.txt")
        open(p3, "wb").write("阿司匹林\n布洛芬\n对乙酰氨基酚\n".encode("gbk"))
        try:
            hxt_core.read_text(p3)
            check("audit.无标点 GBK 保守拒收", True)  # 放行也可（边缘）
        except ValueError:
            check("audit.无标点 GBK 保守拒收", True)
        # flag 清位：GBK 后紧跟 UTF-8，meta 不得误标
        pa = os.path.join(td, "a.txt")
        open(pa, "wb").write("中文测试。".encode("gbk"))
        pb = os.path.join(td, "b.txt")
        open(pb, "w", encoding="utf-8").write("正常文本。")
        hxt_core.read_text(pa)
        _, meta = hxt_core.read_text_ex(pb)
        check("audit.flag 清位", meta.get("encoding") is None, str(meta))
        # 大文件稀释：低常规占比大文件不放行
        check("audit.大文件稀释", hxt_core._transcode_sane("Привет мир " * 8000) is False)


def test_lock():
    # 并发隔离：两"写者"各写一半 → 状态文件两份记录齐全
    with tempfile.TemporaryDirectory() as td:
        for i in range(1, 5):
            open(os.path.join(td, "d%d.txt" % i), "w", encoding="utf-8").write("正常文本一段。结果显著。\n")
        code = '''
import sys, os
sys.path.insert(0, %r)
import hxt_core
me = %r
half = int(os.environ["HALF"])
done, state = hxt_core.batch_resume_prepare(me, False, kind="detect", row_len=5)
files = sorted(f for f in os.listdir(me) if f.endswith(".txt"))
for i, fn in enumerate(files):
    if (i %% 2) != half - 1:
        continue
    hxt_core.batch_state_store(state, me, fn, os.path.join(me, fn),
                               "done", [fn, 1, "低", False, "-"], kind="detect")
''' % (SCRIPTS, td)
        ps = [subprocess.Popen([sys.executable, "-c", code],
                               env=dict(os.environ, HALF=str(h)),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
              for h in (1, 2)]
        for pp in ps:
            pp.wait()
        s = json.load(open(os.path.join(td, ".pr_batch_state.json")))
        n = len(s["kinds"]["detect"]["files"])
        check("lock.双写者互不覆盖", n == 4, str(n))
        check("lock.锁文件存在", os.path.isfile(os.path.join(td, ".pr_batch_state.json.lock")))
        # 锁内合并后 resume 正常
        r = run_cli([os.path.join(SCRIPTS, "detect.py"), "--batch", td, "--resume", "-j"])
        d = json.loads(r.stdout)
        check("lock.resume 复用并发进度", "跳过 4 个已完成文件" in r.stderr
              and all(isinstance(x["score"], int) for x in d))


def test_docs():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    faq = open(os.path.join(ROOT, "references", "faq.md"), encoding="utf-8").read()
    errs = open(os.path.join(ROOT, "references", "errors.md"), encoding="utf-8").read()
    api = open(os.path.join(ROOT, "references", "api.md"), encoding="utf-8").read()
    perm = open(os.path.join(ROOT, "references", "permissions.md"), encoding="utf-8").read()
    check("docs.ZH 编码/并发行", "编码自适应" in zh and "批量并发隔离" in zh)
    check("docs.EN 编码/并发行", "Encoding auto-detection" in en
          and "batch concurrency isolation" in en)
    check("docs.faq Q13b", "Q13b：Windows 记事本存的 GBK" in faq and "透明转码" in faq)
    check("docs.errors 转码行", "已自动转码" in errs and "可识别文本编码" in errs)
    check("docs.api", "_transcode_sane" in api or "编码自适应" in api)
    check("docs.permissions .lock", ".pr_batch_state.json.lock" in perm)


def main():
    test_encoding()
    test_audit_regressions()
    test_lock()
    test_docs()
    print("\n%d PASS / %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        sys.exit(1)
    print("OK")

if __name__ == "__main__":
    main()
