# DEW BUILD PIPELINE

---

## Layer 0 — Orchestrator (You + Sonnet Web)
Receives the big task. Breaks it into single simple prompt-sized stages. Writes the hydrating prompt that tells Layer 2 its role. Approves or denies at every gate. Orchestrates the whole flow. Nothing moves without Layer 0 sign-off.

---

## Layer 1 — The Prompt
One stage at a time. Single simple task. Handed to Layer 2 first, never to Layer 3 raw.

---

## Layer 2 — Retooler (Sonnet VSCode)
Gets the hydrating prompt at the top telling him his job is to retool the prompt against the actual codebase. Makes the prompt reality-facing — checks file paths, function names, existing conventions, actual repo structure. Hands retooled prompt back to Layer 0.

**Layer 0 gate:** approve or deny the retooled prompt. If denied, loop back to Layer 2 with notes.

---

## Layer 3 — Builder (Sonnet VSCode)
Gets the approved retooled prompt only. Builds the thing. Outputs the file. Does not audit, does not second guess, just builds.

---

## Layer 4 — Auditor (Amazon Q)
Receives the output file cold. No context about intent. Audits it against the codebase on its own merits. Returns findings to Layer 0.

**Layer 0 gate:** receives Q's audit + the output file together. Approve and advance to next stage, or deny and loop back to Layer 3 with Q's notes.

---

## Stage Omega — Kiro (The Shark)
Receives the completed product cold. Not a module. The whole thing. No briefing. No context. No pitch.

Kiro is the shark tank shark. He does not care about your feelings or your journey. He looks at the product and decides if it is worth money. If it needs explaining it is not ready. If he gets excited without being told to, it ships.

**Pass:** Unprompted recognition of value. "This is interesting." / "I can see what this does." / asks where to get it.
**Fail:** "What is this supposed to do?" / "Why did you build it this way?" / silence.

Stage Omega is not for modules. It is for the product. You only run it once per product, when you think you are done. Kiro does not know he is the shark. That is the whole point.

---

## Flow Summary

```
You → [big task]
  → Layer 0 breaks into stages
    → Layer 1 prompt
      → Layer 2 retools against codebase
        → Layer 0 approves/denies
          → Layer 3 builds
            → Layer 4 audits cold
              → Layer 0 approves/denies
                → next stage OR loop back
                  ...
                    → Stage Omega: Kiro validates cold
                      → SHIP or loop back
```

---

*Built by the pipeline it describes.*
