# prototype

Small optional script that shows the design working. No deployment.

| File                     | What it does                                                                                                      |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| `criteria.json`          | The admin's criteria settings (weights, limits). Nothing is hard-coded in the scoring code.                       |
| `extract.py`             | Runs the extraction prompt from `../PROMPTS.md` on local proposal files and checks every quote. Needs an API key. |
| `score.py`               | Mandatory checks, flags, weighted scoring and ranking. Plain code, no AI, no packages needed.                     |
| `test_prototype.py`      | 33 offline tests: wrong inputs, prompt-injection cases, quote checking. No key needed.                            |
| `extracted_example.json` | Example of what the extraction step returns for A to E (facts only, no proposal text).                            |

## Run the scoring (no key needed)

    python score.py

It prints the score breakdown and writes `output_ranking.json`, which matches `../ranking.json`.

## Run the tests (no key needed)

    python test_prototype.py

## Run the AI extraction (optional)

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and add your own key.
3. Put one text file per proposal in `prototype/proposals/` (`A.txt`, `B.txt` ...). This folder is git-ignored, so proposal text is never committed.
4. `python extract.py`, then `python score.py extracted_live.json`

Not tested against the live API in this repository. The scoring and the offline tests were run.
