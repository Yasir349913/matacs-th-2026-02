"""Runs the extraction prompt from PROMPTS.md on local proposal text files.

Setup:
    pip install -r requirements.txt
    copy .env.example to .env and put your own key in it (never commit .env)
    put one text file per proposal in prototype/proposals/  (A.txt, B.txt, ...)

Usage:
    python extract.py
    python score.py extracted_live.json
"""
import json
import os
import re
import secrets
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
PROPOSALS_DIR = HERE / "proposals"
OUT_FILE = HERE / "extracted_live.json"


def load_env():
    """Tiny .env reader so no extra package is needed."""
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def load_prompts():
    """Read the system prompt, user message and field list from PROMPTS.md.

    They are the first three code blocks in the 'Prompt 1' section.
    """
    text = (ROOT / "PROMPTS.md").read_text(encoding="utf-8")
    prompt1 = text.split("## Prompt 2")[0]
    blocks = re.findall(r"```(?:json)?\n(.*?)```", prompt1, flags=re.DOTALL)
    if len(blocks) < 3:
        sys.exit("Could not find the 3 code blocks in PROMPTS.md (Prompt 1 section).")
    return blocks[0], blocks[1], blocks[2]


def render(template, values):
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def norm(s):
    return " ".join(s.split())


def verify_quotes(result, proposal_text):
    """If a quote is not really in the proposal, drop the value."""
    text = norm(proposal_text)
    for field in result.get("fields", {}).values():
        quote = field.get("evidence_quote")
        if field.get("value") is not None and (not quote or norm(quote) not in text):
            field["value"] = None
            field["status"] = "ambiguous"
            field["confidence"] = "low"
            field["note"] = (field.get("note") or "") + " Quote not found in the proposal, value removed."
    return result


def parse_json(raw):
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw).strip()
    return json.loads(raw)


def extract_one(client, model, system, user_tpl, fields_json, pid, proposal_text):
    nonce = secrets.token_hex(6)
    base = {"NONCE": nonce, "CATEGORY_NAME": "Commercial Solar Installation",
            "CURRENT_DATE": date.today().isoformat(), "PROPOSAL_ID": pid,
            "FIELDS_JSON": fields_json}
    system_msg = render(system, base)
    # Proposal text is inserted last so nothing inside it is treated as a placeholder.
    user_msg = render(user_tpl, base).replace("{{PROPOSAL_TEXT}}", proposal_text)

    for attempt in (1, 2):  # one retry if the output is not valid JSON
        reply = client.messages.create(
            model=model, max_tokens=2500, temperature=0,
            system=system_msg, messages=[{"role": "user", "content": user_msg}],
        )
        try:
            return verify_quotes(parse_json(reply.content[0].text), proposal_text)
        except (json.JSONDecodeError, IndexError):
            print(f"  {pid}: output was not valid JSON (attempt {attempt})")
    return None


def main():
    load_env()
    if not PROPOSALS_DIR.exists() or not list(PROPOSALS_DIR.glob("*.txt")):
        sys.exit(f"Put one .txt file per proposal in {PROPOSALS_DIR} first (A.txt, B.txt, ...).")
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    import anthropic  # imported here so score.py never needs it
    client = anthropic.Anthropic()
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    system, user_tpl, fields_json = load_prompts()

    out = {}
    for path in sorted(PROPOSALS_DIR.glob("*.txt")):
        pid = path.stem
        print(f"Extracting {pid} ...")
        result = extract_one(client, model, system, user_tpl, fields_json, pid,
                             path.read_text(encoding="utf-8"))
        if result is None:
             print(f"  {pid}: giving up, it will be flagged for human review")
             result = {"injection_flags": [], "fields": {}, "error": "extraction failed"}
        out[pid] = result

    OUT_FILE.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Saved {OUT_FILE.name}. Now run: python score.py {OUT_FILE.name}")


if __name__ == "__main__":
    main()