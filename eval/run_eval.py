"""Send every question in questions.json to /chat, score the answers, save results.json.

The API must be running with the three files of data/samples uploaded.

Usage: python eval/run_eval.py [--api-url http://127.0.0.1:8000] [--pause 15] [--rescore]
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
SAMPLES = {"meeting_notes.txt", "rapport_projet_atlas.docx", "remote_work_policy.pdf"}

# phrases that show the assistant said the information is missing
NOT_FOUND = [
    "not found", "no information", "not contain", "not mention", "not include",
    "not provide", "not specif", "no mention", "unable to find", "could not find",
    "couldn't find", "pas trouvé", "pas été trouvé", "introuvable", "aucune information",
    "ne contien", "pas mentionné", "ne figure pas", "ne précise", "ne fournissent pas",
    "ne mentionne", "n'est mentionné", "nulle part",
]


def post_chat(api_url: str, question: str) -> dict:
    body = json.dumps({"message": question, "history": []}).encode()
    request = urllib.request.Request(
        api_url + "/chat", body, {"Content-Type": "application/json"}
    )
    # wait and retry when the LLM is rate limited (429) or briefly unreachable (502)
    for attempt in range(4):
        try:
            return json.loads(urllib.request.urlopen(request, timeout=180).read())
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 502) or attempt == 3:
                raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode()[:300]}") from exc
            print(f"   HTTP {exc.code}, waiting 40s before retrying...")
            time.sleep(40)
    raise RuntimeError("unreachable")


def contains(answer: str, keyword: str) -> bool:
    """True if `keyword` appears in `answer` as a whole word or number."""
    text = answer.lower().replace(" ", " ").replace(" ", " ")
    # "1 240", "1,240" and "1240" must all match the keyword "1240"
    compact = re.sub(r"(?<=\d)[ ,](?=\d{3}\b)", "", text)
    # not inside a longer word or number: "3" must not match "3.4" or "30"
    pattern = rf"(?<![\w.]){re.escape(keyword.lower())}(?!\w|[.,]\d)"
    return bool(re.search(pattern, text) or re.search(pattern, compact))


def score(item: dict, answer: str, tools: list[str], sources: list[str]) -> dict:
    """Automatic checks: was the right source or tool used, is the answer correct."""
    if item["category"] == "no_answer":
        retrieval_ok = None
        answer_ok = any(phrase in answer.lower() for phrase in NOT_FOUND)
    else:
        if "expected_source" in item:
            retrieval_ok = item["expected_source"] in sources
        else:
            retrieval_ok = item["expected_tool"] in tools
        answer_ok = all(
            any(contains(answer, keyword) for keyword in group)
            for group in item["must_contain"]
        )
    return {
        **item,
        "answer": answer,
        "tools_called": tools,
        "sources": sources,
        "retrieval_ok": retrieval_ok,
        "answer_ok": answer_ok,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--pause", type=float, default=15, help="seconds between questions")
    parser.add_argument(
        "--rescore", action="store_true", help="re-score the saved answers without calling the API"
    )
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    questions = json.loads((EVAL_DIR / "questions.json").read_text(encoding="utf-8"))
    results_path = EVAL_DIR / "results.json"
    results = []

    if args.rescore:
        saved = {r["id"]: r for r in json.loads(results_path.read_text(encoding="utf-8"))}
        for item in questions:
            old = saved[item["id"]]
            result = score(item, old["answer"], old["tools_called"], old["sources"])
            results.append({**result, "seconds": old["seconds"]})
    else:
        documents = json.loads(urllib.request.urlopen(args.api_url + "/documents").read())
        indexed = {doc["filename"] for doc in documents}
        if indexed != SAMPLES:
            sys.exit(
                f"The evaluation expects exactly the files of data/samples to be uploaded.\n"
                f"Currently indexed: {sorted(indexed)}"
            )
        for index, item in enumerate(questions):
            if index:
                time.sleep(args.pause)
            started = time.time()
            response = post_chat(args.api_url, item["question"])
            result = score(
                item,
                response["answer"],
                [call["name"] for call in response["tool_calls"]],
                sorted({source["filename"] for source in response["sources"]}),
            )
            result["seconds"] = round(time.time() - started, 1)
            results.append(result)

    for result in results:
        flag = "ok " if result["answer_ok"] and result["retrieval_ok"] is not False else "FAIL"
        print(f"[{flag}] {result['id']:>2} {result['category']:<15} {result['question']}")
        print(f"        {result['answer'][:160].replace(chr(10), ' ')}")

    results_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\nCategory          answers correct   right source/tool")
    for category in dict.fromkeys(r["category"] for r in results):
        rows = [r for r in results if r["category"] == category]
        answers = sum(r["answer_ok"] for r in rows)
        scored = [r for r in rows if r["retrieval_ok"] is not None]
        retrieval = f"{sum(r['retrieval_ok'] for r in scored)}/{len(scored)}" if scored else "-"
        print(f"{category:<17} {answers}/{len(rows):<15} {retrieval}")
    total = sum(r["answer_ok"] for r in results)
    print(f"{'TOTAL':<17} {total}/{len(results)}")
    print(f"\nSaved {results_path}")


if __name__ == "__main__":
    main()
