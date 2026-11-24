# novel-machine

A shell-and-Python pipeline that lets a cheap LLM CLI write a long Chinese web novel one chapter at a time, unattended, without drifting off the outline, rewriting the wrong files or forgetting what happened ten chapters ago.

一套让大模型命令行工具一章一章写长篇小说的流水线：无人值守地连写，不跑偏大纲，不乱改不该改的文件，也不忘记十章前发生了什么。

It was built for a real ongoing project (a fan-fiction novel in Traditional Chinese, written by Gemini through the `agy` CLI and maintained with Claude). The settings, roadmap and rules in this repo are that project's, kept here as a working example. The machine itself is not tied to the story: swap the files under `设定/`, `路标.md`, `作者意图.md` and the character-specific checks in `tools/check.py`, and it writes a different book.

这套机器原本服务于一个真实在写的项目：一部繁体中文同人小说，正文由 Gemini 通过 `agy` 命令行写，机器由 Claude 维护。仓库里的设定、路标和写作规矩都是那部书的，留着当完整示例。机器本身不绑定这个故事：换掉 `设定/`、`路标.md`、`作者意图.md`，再改掉 `tools/check.py` 里针对具体人物的检查，就能写另一本书。

## Why / 为什么要做这个

Letting a model "just keep writing" fails in predictable ways. Each one below has a fix in this repo:

让模型"一直往下写"，会以几种固定的方式翻车。下面每一种，仓库里都有对应的处理：

| Failure 翻车方式 | Fix 处理 |
|---|---|
| Every chapter follows the same skeleton and reuses last chapter's jokes 每章同一个骨架、重复上一章的梗 | `tools/compose.py` 把上一章的场次和用过的梗列给写手，点名不准再用；`tools/check.py` 发现连章重复的梗就判不过 |
| Model forgets state, contradicts earlier chapters 模型忘了状态，和前文矛盾 | 写手每章产出一份 `记忆/待更新.md`；下一章开写前合进 `进度.md`、`伏笔.md`，并按章存快照，可以回滚 |
| Model edits files it shouldn't (earlier chapters, scripts, settings) 模型改了不该改的文件 | `tools/guard.py` 在每次调模型前拍快照，调完把越界的改动还原，多出来的文件挪进隔离区 |
| Plot milestones get skipped or written too early 路标节点被跳过或提前写了 | `路标.md` 写"第 N 章要发生什么"，编排脚本每章告诉写手离下一个节点还有几章、这章能不能碰 |
| Fights every chapter 章章都在打 | 只有路标标了【打怪】的章才打，其余章的提示里写明不打 |
| Process killed mid-chapter (VM reboot) 写到一半进程被杀（VM 重启） | 每章有一个"进行中"标记，记着走到哪一步；之后要么用 `--续跑` 补完后面的步骤，要么干净地重写这一章，绝不会悄悄跳到下一章 |
| Quality drifts in ways the model can't see 质量往模型自己看不出的方向漂 | `tools/check.py` 有几十项检查：硬伤判 FAIL，自动修稿一次；文风问题只列 WARN |

## Run / 怎么跑

Needs bash (3.2 is fine, it runs on stock macOS), Python 3 and an LLM CLI. The default is `agy`; set `AGY=` to point at another one.

需要 bash（3.2 就够，macOS 自带的能跑）、Python 3 和一个大模型命令行工具。默认用 `agy`，要换就设 `AGY=`。

```
bin/novel-call.sh --doctor          # check the environment / 检查环境
bin/novel-call.sh '繼續'             # write the next chapter, model follows the roadmap / 写下一章，照路标走
bin/novel-call.sh '一段走向'          # write the next chapter following your direction / 照你给的走向写下一章
bin/novel-call.sh '重寫第N章 要求'     # roll back and rewrite chapter N / 回滚并重写第 N 章
bin/auto.sh 3                       # write 3 chapters in a row, then build and push / 连写 3 章，写完合本、推送
```

One chapter goes through these steps / 一章的流程：

```
记账 (merge memory) → 编排 (compose.py: setting slice + hints) → 写手 (one model call)
→ 粗筛 (check.py, one auto-fix round on FAIL) → 提交 (commit + push)
```

## Test / 测试

`tests/fake_agy.py` is a fake model. It writes a sample chapter, misbehaves on purpose (leaves stray scripts, edits files it shouldn't) and can be told to hang so the test can kill it.

`tests/fake_agy.py` 是一个假模型：它会写出一章样稿，故意捣乱（留下多余的脚本、改不该改的文件），也能按指令卡住，让测试把它杀掉。

```
AGY=$PWD/tests/fake_agy.py NOPUSH=1 bin/novel-call.sh '繼續'   # run in a copy / 在副本里跑
python3 tests/test_resume.py                                     # kill -9 mid-chapter, resume, rewrite / 写到一半 kill -9，再测续跑和重写
```

## Layout / 目录

| Path 路径 | What 内容 |
|---|---|
| `bin/` | entry scripts / 入口脚本 |
| `tools/` | compose, check, guard, memory merge, rollback / 编排、检查、越界守卫、记忆合并、回滚 |
| `设定/规则.md` | the one writing rulebook the model reads / 写手读的唯一一份写作规矩 |
| `设定/` (others) | world facts, character card, sealed plot lines / 世界设定、人设卡、封存的剧情线 |
| `路标.md` `作者意图.md` | roadmap and long-term intent / 路标和长期方向 |
| `记忆/` | running memory (state, foreshadowing, current focus) / 滚动记忆（进度、伏笔、当前焦点） |
| `文风/` | style samples / 文风样本 |
| `tests/` | fake model, resume test, sample chapters / 假模型、续跑测试、样稿 |

## Notes / 说明

- The sample chapters and style passages were written by the pipeline itself. The story is fan fiction inspired by Jiang Nan's 《龍族》; no text from the original novels is included.
- 样稿和文风段落都是这套流水线自己写出来的。故事是受江南《龍族》启发的同人，仓库里不含原著的任何文字。
- Deployment uses the model vendor's subscription login (OAuth). No API keys live in this repo.
- 部署走模型厂商的订阅登录（OAuth），仓库里没有任何 API Key。

## License

MIT
