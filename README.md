# 👕 내 옷장 · My Closet

**AI 비서에게 GitHub 주소 하나만 주세요. 그다음은 말만 하면 됩니다.**
Give your AI assistant this repo's address. After that, just talk.

```
https://github.com/m-ill/my-closet-skill 이 주소로 내 옷장 접속해줘
```

```
👕 내 옷장 (0벌)
아직 비어 있어요. 무엇을 할까요? 번호로 말해주세요.
1. 라벨 올리기 — 옷 라벨(택) 사진을 보내주세요
2. 내 옷장 보기
3. 사진 찍어 올리기 — 라벨 없는 옷은 옷 전체 사진
4. 설정 — 아침 추천 예약 · 옷 지우기 · 내보내기 · 코디 추천("오늘 뭐 입지?")
```

라벨 사진을 보내면 AI가 브랜드·품번·사이즈를 읽어 **묻지 않고 바로 저장**하고,
"오늘 뭐 입지?"라고 물으면 **내가 실제로 가진 옷으로만** 코디를 짜고, 품번으로 찾은 실제 상품 사진을 합성해 착장 이미지로 보여줍니다.
"매일 아침 7시에 추천해줘"라고 하면 비서의 예약 기능으로 **매일 아침 날씨에 맞는 코디 사진**을 보내 줍니다.
옷장 데이터는 **내 컴퓨터(또는 내 비서의 서버)에만** 저장됩니다. 가입도, 서버도, 요금도 없어요.

[![tests](https://github.com/m-ill/my-closet-skill/actions/workflows/test.yml/badge.svg)](https://github.com/m-ill/my-closet-skill/actions/workflows/test.yml)
![python](https://img.shields.io/badge/python-3.10%2B-blue) ![deps](https://img.shields.io/badge/dependencies-none-brightgreen) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

---

## 어떻게 동작하나요

| 하는 일 | 누가 |
|---|---|
| 사진·라벨 읽기, 코디 생각, 날씨 확인, 상품 사진 찾기, 착장 이미지 합성, 매일 아침 예약 | **당신의 AI 비서** (이미 가진 능력) |
| 읽은 정보를 검사하고 번호·날짜 붙여 저장 | **이 스킬** (`scripts/closet.py`, Python 표준 라이브러리만) |
| 데이터 보관 | **내 컴퓨터** `~/.my-closet/closet.db` (SQLite 파일 하나) |

- 옷마다 **바뀌지 않는 번호(#1, #2…)와 등록일**이 붙어요. 지운 번호는 다시 쓰지 않아요.
- 흐릿하거나 확실하지 않은 값은 비워 두고, 없는 옷을 지어내지 않도록 규칙이 들어 있어요.
- 저장 명령이 성공했을 때만 "저장됐어요"라고 말하게 되어 있어요.
- 사진·얼굴·링크·비밀번호는 저장하지 않아요. 글로 된 옷 정보만 남아요.

## 지원하는 AI 비서

명령을 실행할 수 있는 에이전트라면 됩니다.

| 비서 | 방법 |
|---|---|
| OpenClaw · Hermes · Codex · 기타 에이전트 | 위 문장 한 줄 ([AGENTS.md](AGENTS.md)를 읽고 스스로 설치) |
| Claude Code | `git clone https://github.com/m-ill/my-closet-skill ~/.claude/skills/my-closet` |
| ChatGPT · Gemini 일반 채팅 | 명령 실행이 안 돼서 저장은 불가 — 규칙만 읽고 대화를 도와줍니다 |

## 직접 써보기

```bash
git clone https://github.com/m-ill/my-closet-skill
cd my-closet-skill
python3 scripts/closet.py status
python3 scripts/closet.py add '{"kind":"label","fields":{"brand":"UNIQLO","category":"trousers","size":"L"}}'
python3 scripts/closet.py list
```

| 명령 | 하는 일 |
|---|---|
| `status` | 옷 개수와 메뉴 |
| `add '<JSON>'` | 옷 저장 (한 벌 또는 최대 50벌 목록, 하나라도 틀리면 전부 저장 안 함) |
| `list [--limit N]` | 최근 옷부터 목록 |
| `remove <번호>` | 옷 지우기 (번호는 재사용 안 함) |
| `export [--format csv\|json]` | 내보내기 |
| `pref [키 [값]]` | 아침 추천용 설정: city · timezone · morning_time · style · body · notes |

다른 위치에 저장하려면 `MY_CLOSET_DB=/path/closet.db`.

## English

My Closet is an [Agent Skill](SKILL.md) that turns any command-running AI assistant into a wardrobe keeper.
Send a photo of a clothing label and the assistant reads brand, product code and size and saves them at once;
ask "what should I wear today?" and it builds outfits only from clothes you actually own, optionally looking up
real product photos by product code. Data stays in one SQLite file on your machine. No account, no server, no fees.

Tell your assistant: `Open my closet from https://github.com/m-ill/my-closet-skill` — it follows [AGENTS.md](AGENTS.md).

## 기여 · Contributing

이슈와 PR 환영합니다. 테스트: `python3 -m unittest discover -s tests`
특히 반가운 것: 다른 비서에서 써본 후기, 옷 종류·색 코드 보강, 다국어 메뉴.

⭐ 도움이 됐다면 Star를 눌러 주세요. 더 많은 사람이 찾을 수 있어요.

## License

[MIT](LICENSE)
