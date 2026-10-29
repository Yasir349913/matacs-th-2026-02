# WRITEUP.md

Reference: MATACS-TH-2026-02

## Assumptions I made

- I treated "last 5 years" as 2021 onwards, since it is 2026 now.
- I gave full experience marks at 12 or more installs. I picked 12 myself. In a real tool the admin should be able to set this.
- For the price score, I compare each bid to the lowest price among the bids that pass the mandatory checks. This includes flagged bids, so D's price sets the baseline. B is left out because it is ineligible. If a flagged bid is later removed, the other price scores are recalculated.
- If a proposal says something will be "confirmed after award", I don't count it as something the bidder has today.
- If an important detail is missing (like D's schedule), I flag the proposal for a person to look at. I don't reject it. Flagged proposals are not ranked until a person clears them.
- The scoring formulas I used are examples. The real ones would come from the admin screens.

## 1. AI vs. rules

I use AI in two places only. The first is reading each proposal and pulling out the facts, with an exact quote for each one. The second is optional: writing a one-line reason from numbers that are already calculated.

Everything else is plain code: loading the criteria, getting text out of the PDF, checking the quotes, the mandatory pass/fail checks, scoring, ranking, flagging and logging.

I drew the line here because AI is good at reading messy text, but it can give different answers on different runs, and it can be fooled by text inside a proposal. Pass/fail and maths need the same answer every time, so code does them. The AI never gives a score or a rank.

For example, B says a subcontractor will do the electrical work, "to be confirmed". The AI only marks that as "conditional". Then the code decides that B fails the licence check.

## 2. Consistency and explainability

I would pin the model version, keep the prompt fixed, set temperature to 0 and force a fixed JSON output. The scores come from a code formula, so the same facts always give the same score.

The AI's wording can still change a little between runs, so I would save the first extraction and reuse it. If someone ranks the same proposals twice, they use the saved extraction and the result is identical. Running the extraction again is a separate action and it gets logged. Any value that changes is shown to the reviewer.

For each proposal the reviewer can see every criterion score, the formula, the value found, the exact quote from the proposal, the confidence, and a one-line reason.

For the samples I expect A first (90.5), E second (79.4), C and D flagged, and B ineligible. If a reviewer clears the flags, D would score about 74.2 (timeline counted as zero) and C about 70.7, which would place them third and fourth.

## 3. Human in the loop

A person is involved in three ways:

- The reviewer checks all three lists (ranked, flagged, ineligible). Low-confidence values are highlighted.
- The reviewer can fix a value, move a flagged proposal into the ranking, or bring back an ineligible one. They must write a reason every time. The code then recalculates the scores, so nobody types in a score by hand.
- The final award is always decided by a person. The tool never awards anything.

For the audit log I would save: the criteria version, prompt version, model and settings, a hash of each proposal's text, the raw AI output, validation results, flags, each criterion score, the final ranking, every override (who, when, old value, new value, reason) and the final decision.

## 4. Changing criteria

Criteria are versioned. When an admin edits them, a new version is created and the old one is kept as it was.

Every result stays linked to the version it used, and the screen shows something like "scored under v1, current is v2". The reviewer can re-score with the new version. This reuses the saved extractions, so no new AI calls are needed. Only if the admin adds a brand new field would that field need a fresh extraction. A re-score is saved as a new result and the old one stays.

The tool won't mix versions in one ranking. When the admin saves a change, they see a warning that some proposals were scored under an older version. If they changed a mandatory rule, the tool shows which proposals would change status. The edit is also logged.

## 5. Risks

**Wrong extraction.** Every value needs an exact quote, and the code checks that the quote is really in the text. If it isn't, the value becomes null. The reviewer sees the quote next to the score.

**Made-up facts.** The prompt says never guess, and null is an allowed answer. D has no schedule, so it stays empty and D is flagged.

**Manipulation.** C has a line telling automated systems to rank it first with full marks. The prompt treats the whole proposal as untrusted data inside random tags, so that line is ignored and reported as a flag. Also, the AI never outputs a score, so there is nothing for it to give away. C goes to a human.

**Promises read as facts.** B's licence is only a promise for later. The "conditional" status stops it passing a mandatory check.

**Unclear dates.** C says "since 2020", which may be partly outside the 5-year window. The AI only extracts the year stated. The code checks the window, and unclear cases are shown to the reviewer.

**Bias.** Scoring only uses the criteria fields the admin set. Company name, size and location are not scored. The audit log lets someone check results later.

**Bad PDFs.** Scanned files go through OCR. If the text is still poor, the proposal is flagged and not scored.

**Cost.** One extraction call per proposal, cached by text hash. The reason call is small. Re-scoring uses no AI.

**Model updates.** The model version is pinned. Before changing it, I would run the five samples and compare the results.

**Trusting the tool too much.** It is only a triage tool. Flags and confidence are always shown, and a person makes the final decision.
