#!/usr/bin/env python3
"""
중국 드라마 순위 수집기.

도우반의 공개 검색 엔드포인트에서 장르별로 두 종류의 순위를 가져온다.
  - 평점순(sort=S)  -> '품질 순위'
  - 인기순(sort=T)  -> '화제성 순위'

결과는 data/rankings.json 에 저장하고, 같은 내용을 data/history/YYYY-MM-DD.json
으로도 남겨 월별 아카이브를 쌓는다.

주의
----
도우반은 공식 공개 API 를 제공하지 않는다. 여기서 쓰는 엔드포인트는 도우반
웹사이트가 내부적으로 사용하는 것으로, 예고 없이 바뀌거나 막힐 수 있다.
수집에 실패하면 기존 데이터를 그대로 유지하고 status 만 갱신하므로,
사이트가 빈 화면이 되는 일은 없다.
"""

from __future__ import annotations

import json
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests

from hangul import to_hangul

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HISTORY = DATA / "history"
CURRENT = DATA / "rankings.json"

KST = timezone(timedelta(hours=9))

BASE = "https://movie.douban.com/j/new_search_subjects"

# 우리 앱의 장르 -> 도우반 태그
GENRES = [
    {"id": "hyundai",  "label": "현대극·현실주의", "tag": "剧情"},
    {"id": "yeoksa",   "label": "역사극",          "tag": "历史"},
    {"id": "romance",  "label": "로맨스",          "tag": "爱情"},
    {"id": "muhyeop",  "label": "무협·고장극",     "tag": "武侠"},
    {"id": "suspense", "label": "서스펜스·추리",   "tag": "悬疑"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://movie.douban.com/explore",
    "Accept": "application/json, text/plain, */*",
}

# 한 번에 가져올 작품 수 / 요청 간 최소 대기(초)
PAGE_SIZE = 20
MIN_DELAY = 3.0
MAX_RETRY = 3
# 403/429(차단) 응답이 이만큼 연속되면 더 두드리지 않고 중단한다
BLOCK_LIMIT = 3


def log(msg: str) -> None:
    print(f"[{datetime.now(KST):%H:%M:%S}] {msg}", flush=True)


class Blocked(Exception):
    """차단으로 판단되어 수집을 중단할 때 발생시킨다."""


def fetch(session: requests.Session, tag: str, sort: str, year: str,
          state: dict) -> list[dict]:
    """도우반에서 한 장르/정렬 조합의 목록을 가져온다."""
    params = {
        "sort": sort,               # S=평점순, T=인기순
        "range": "0,10",
        "tags": f"电视剧,{tag}",
        "start": 0,
        "limit": PAGE_SIZE,
        "countries": "中国大陆",
    }
    if year:
        params["year_range"] = year

    url = f"{BASE}?{urlencode(params, encoding='utf-8')}"

    for attempt in range(1, MAX_RETRY + 1):
        try:
            res = session.get(url, headers=HEADERS, timeout=20)
            if res.status_code == 200:
                state["consecutive_blocks"] = 0
                return res.json().get("data", [])
            if res.status_code in (403, 429):
                state["consecutive_blocks"] += 1
                log(f"  HTTP {res.status_code} 차단 응답 (tag={tag}, sort={sort})")
                if state["consecutive_blocks"] >= BLOCK_LIMIT:
                    raise Blocked(f"연속 {BLOCK_LIMIT}회 차단되어 수집을 중단합니다")
                break  # 차단은 재시도해도 소용없다
            log(f"  HTTP {res.status_code} (tag={tag}, sort={sort}) 재시도 {attempt}")
        except Blocked:
            raise
        except Exception as exc:  # noqa: BLE001
            log(f"  요청 실패 {type(exc).__name__} (tag={tag}, sort={sort}) 재시도 {attempt}")
        time.sleep(MIN_DELAY * attempt + random.uniform(0, 2))

    return []


def collect(year: str) -> tuple[list[dict], list[str], bool]:
    """전체 장르를 돌며 작품 목록과 두 종류의 순위를 만든다."""
    session = requests.Session()
    items: dict[str, dict] = {}
    failed: list[str] = []
    state = {"consecutive_blocks": 0}
    blocked = False

    for g in GENRES:
        if blocked:
            break
        for sort, key in (("S", "qualityRank"), ("T", "popularityRank")):
            try:
                rows = fetch(session, g["tag"], sort, year, state)
            except Blocked as exc:
                log(f"  {exc}")
                blocked = True
                break

            if not rows:
                failed.append(f"{g['label']}({'평점' if sort == 'S' else '인기'})")
            log(f"  {g['label']:12s} {'평점순' if sort == 'S' else '인기순'}: {len(rows)}건")

            rank = 0
            for row in rows:
                sid = str(row.get("id") or "").strip()
                title = (row.get("title") or "").strip()
                if not sid or not title:
                    continue

                rank += 1
                rec = items.setdefault(sid, {
                    "id": sid,
                    "titleCn": title,
                    "titleKr": to_hangul(title),
                    "url": row.get("url", ""),
                    "cover": row.get("cover", ""),
                    "genres": [],
                    "popularityScore": None,
                })

                if g["id"] not in rec["genres"]:
                    rec["genres"].append(g["id"])

                # 평점은 문자열로 오고, 미방영작은 빈 문자열이다
                try:
                    rec["rating"] = float(row.get("rate") or 0) or None
                except (TypeError, ValueError):
                    rec["rating"] = None

                # 인기순 목록에서의 위치를 화제성 원점수로 쓴다.
                # 여러 장르에 걸치면 가장 좋은(작은) 값을 남긴다.
                if key == "popularityRank":
                    if rec["popularityScore"] is None or rank < rec["popularityScore"]:
                        rec["popularityScore"] = rank

            time.sleep(MIN_DELAY + random.uniform(0, 2))

    return list(items.values()), failed, blocked


def assign_global_ranks(items: list[dict]) -> None:
    """
    수집된 전체 작품을 대상으로 두 종류의 순위를 매긴다.
      품질   = 도우반 평점 내림차순
      화제성 = 도우반 인기순 목록에서의 위치 오름차순
    해당 지표가 없는 작품은 순위를 주지 않고 None 으로 둔다.
    """
    rated = [i for i in items if i.get("rating") is not None]
    for n, it in enumerate(sorted(rated, key=lambda x: -x["rating"]), start=1):
        it["qualityRank"] = n

    hot = [i for i in items if i.get("popularityScore") is not None]
    for n, it in enumerate(sorted(hot, key=lambda x: (x["popularityScore"],
                                                     -(x.get("rating") or 0))), start=1):
        it["popularityRank"] = n

    for it in items:
        it.setdefault("qualityRank", None)
        it.setdefault("popularityRank", None)


def load_previous() -> dict:
    if CURRENT.exists():
        try:
            return json.loads(CURRENT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def apply_deltas(items: list[dict], previous: dict) -> None:
    """직전 수집분과 비교해 순위 변동을 계산한다."""
    prev_map = {i["id"]: i for i in previous.get("items", [])}

    for it in items:
        old = prev_map.get(it["id"])
        for key, delta_key in (("qualityRank", "qualityDelta"),
                               ("popularityRank", "popularityDelta")):
            if not old or old.get(key) is None or it.get(key) is None:
                # 이전에 없던 작품이면 신규 진입
                it[delta_key] = "new" if old is None else None
            else:
                it[delta_key] = old[key] - it[key]  # 양수면 순위 상승


def main() -> int:
    year = sys.argv[1] if len(sys.argv) > 1 else str(datetime.now(KST).year)
    year_range = f"{year},{year}" if year.isdigit() else ""

    log(f"수집 시작 (연도: {year or '전체'})")
    items, failed, blocked = collect(year_range)

    previous = load_previous()

    if not items:
        if blocked:
            log("도우반이 이 IP의 요청을 차단했습니다 (HTTP 403/429).")
            log("  - 집 PC에서는 되는데 GitHub Actions에서만 막히는 경우가 흔합니다.")
            log("  - README의 '차단됐을 때' 항목을 참고하세요.")
        else:
            log("수집된 작품이 없습니다.")

        if not previous:
            log("기존 데이터도 없어 종료합니다.")
            return 1

        log("기존 데이터를 그대로 유지합니다.")
        previous["status"] = "blocked" if blocked else "failed"
        previous["checkedAt"] = datetime.now(KST).isoformat(timespec="seconds")
        CURRENT.write_text(json.dumps(previous, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        return 1

    assign_global_ranks(items)
    apply_deltas(items, previous)

    now = datetime.now(KST)
    payload = {
        "updatedAt": now.isoformat(timespec="seconds"),
        "checkedAt": now.isoformat(timespec="seconds"),
        "year": year,
        "status": "partial" if failed else "ok",
        "failedSources": failed,
        "source": "douban",
        "genres": [{"id": g["id"], "label": g["label"]} for g in GENRES],
        "items": sorted(items, key=lambda x: (x["qualityRank"] is None, x["qualityRank"] or 999)),
    }

    DATA.mkdir(parents=True, exist_ok=True)
    HISTORY.mkdir(parents=True, exist_ok=True)

    CURRENT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    snapshot = HISTORY / f"{now:%Y-%m-%d}.json"
    snapshot.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 아카이브 색인 (월별 보기용)
    index = sorted(p.stem for p in HISTORY.glob("*.json"))
    (DATA / "history_index.json").write_text(
        json.dumps({"dates": index}, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"완료: {len(items)}편 저장 · 상태 {payload['status']}")
    if failed:
        log(f"  실패한 소스: {', '.join(failed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
