# matacs-th-2026-02

**Name:** Yasir Maqsood
**Reference:** MATACS-TH-2026-02
**Role:** Associate Software Developer
**Time actually spent:** About 70 minutes in total: about 40 minutes on the design (write-up, prompts, diagram, ranking) and about 30 minutes on the optional prototype.

## What this is

My design for an AI-assisted proposal triage tool for the Commercial Solar Installation category. AI is only used to read proposals and extract facts. Pass/fail checks, scoring and ranking are plain code, and a person makes the final decision.

## Files

- [WRITEUP.md](WRITEUP.md): answers to the five questions
- [PROMPTS.md](PROMPTS.md): extraction prompt and reason prompt
- [ranking.json](ranking.json): my expected ranking of proposals A to E
- [diagram/process-flow.png](diagram/process-flow.png): process flow from upload to ranked output
- [prototype/](prototype/): optional script for scoring, extraction and 33 offline tests
- [prototype/README.md](prototype/README.md): how to run the prototype

## How I used AI tools

I used Claude to talk through the requirements, draft the prompts and check the edge cases in the sample set. I did not accept its work as it was: its first write-up was too stiff and generic for a non-developer reader, which goes against the brief's request for plain writing, so I rewrote it in my own words. I also checked its output against the brief myself, including the file names, the word limit and the format rules.

## Note on the samples

Proposals are referred to by letter (A to E) only. No proposal text or brief text is copied here.
