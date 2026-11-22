# For AI assistants: "이 주소로 내 옷장 접속해줘"

If the user gave you this repository's address and asked you to open / connect / install My Closet (내 옷장),
do the following. You need to be able to run shell commands (OpenClaw, Hermes, Claude Code, Codex, and similar
agents can). Ask before installing only if your own rules require it.

1. **Get the skill** into your skills folder (or any folder you keep):

   ```
   git clone https://github.com/m-ill/my-closet-skill ~/.my-closet/skill
   ```

   If it is already there, update it with `git -C ~/.my-closet/skill pull`.
   If your agent has its own skills directory (for example `~/.claude/skills`, `~/.openclaw/skills`,
   `~/.hermes/skills`), copy or link the folder there so it loads automatically next time.

2. **Check it works**: `python3 ~/.my-closet/skill/scripts/closet.py status`
   (use `python` if `python3` is missing; Python 3.10+ with no extra packages).

3. **Show the `guide`** from that output to the user exactly as printed, then follow [SKILL.md](SKILL.md)
   for everything after that.

From then on the user only needs to say "내 옷장" or send a photo.

## If you cannot run commands

If you are a chat-only assistant that cannot run programs or write files, **say so plainly**: you can read
the rules and help in this chat, but you cannot save anything to the closet. Never say a garment was saved
unless `closet.py add` actually returned `"ok": true`.
