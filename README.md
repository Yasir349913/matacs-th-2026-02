# matacs-th-2026-02

**Name:** Yasir Maqsood
**Reference:** MATACS-TH-2026-02
**Role:** Associate Software Developer
**Time actually spent:** About 60 minutes

## What this is

My design for an AI-assisted proposal triage tool for the Commercial Solar Installation category. AI is only used to read proposals and extract facts. Pass/fail checks, scoring and ranking are plain code, and a person makes the final decision.

## Files

- [WRITEUP.md](WRITEUP.md): answers to the five questions
- [PROMPTS.md](PROMPTS.md): extraction prompt and reason prompt
- [ranking.json](ranking.json): my expected ranking of proposals A to E
- [diagram/process-flow.png](diagram/process-flow.png): process flow from upload to ranked output

## How I used AI tools

I read the brief twice myself first, then used Claude to talk through the requirements, plan the flow, draft the prompts and check the edge cases in the sample set (B's licence promise, C's embedded instruction, D's missing schedule). I reviewed its work against the brief instead of accepting it as it was.

For example, its first write-up sounded too stiff and generic, so I asked for a plainer version and edited it in my own words. I also checked the brief's rules for the diagram before choosing the PNG format, to make sure it met the requirement.

## Note on the samples

Proposals are referred to by letter (A to E) only. No proposal text or brief text is copied here.