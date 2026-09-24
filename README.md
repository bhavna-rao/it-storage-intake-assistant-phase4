# Storage Request Self-Service Intake Assistant
### Phase 4 — a working prototype of the Phase 2 BRD's core flow, following the IT Service Ticket Classification (Phase 1) and the AI-Augmented Ticket Triage Agent (Phase 3)

## Personal Portfolio Project
This is a self-directed practice project, not a real client engagement or employer deliverable. It implements a scoped-down, simulated version of the self-service storage request flow specified in the Phase 2 BRD.

## How this connects to Phase 1, 2 & 3
Phase 1 ([IT Service Ticket Classification](https://github.com/bhavna-rao/it-ticket-volume-complexity-analysis)) found Storage tickets were low-volume and the least complex category — the strongest candidate to automate first. Phase 2 ([Storage Self-Service BRD](https://github.com/bhavna-rao/it-storage-selfservice-portal-phase2)) turned that into formal requirements: a self-service form with rules-based auto-approval (FR-02) and routing to a review queue for exceptions (FR-03). Phase 3 ([AI-Augmented Ticket Triage Agent](https://github.com/bhavna-rao/it-ai-triage-agent-phase3)) tested a further, harder idea — could AI detect a Storage request from free text alone — and, even after improvement testing, found that approach isn't reliable enough yet on its own.

Phase 4 goes back to what Phase 2 actually specified and builds a small, working version of it: a conversational intake that captures a request in the requester's own words, then applies the same deterministic auto-approve/review-queue logic from FR-02/FR-03. Unlike Phase 3, the business decision here is never left to the AI — the AI only helps understand what the requester typed.

## What it does
1. Asks the requester what they need, in their own words (FR-01 — no general helpdesk ticket required).
2. Uses Claude to extract two fields from the conversation: the amount of storage requested (converted to GB) and the business justification. If either is missing or unclear, it asks a follow-up question rather than guessing.
3. Once both fields are captured, a plain Python rule — not the AI — decides the outcome: at or below the policy threshold, the request is auto-approved (FR-02); above it, the request is routed to the Storage Team's review queue (FR-03). This separation is deliberate: the part of the system that must always be correct is not left to a language model.
4. Prints a simulated status trail — submitted, approved-or-queued, provisioned — standing in for the real email notifications specified in FR-04.

## Scope of this prototype
This is intentionally a Storage-only assistant, matching the Phase 2 BRD's own scope exactly (the BRD is specifically an "IT Storage Request Self-Service Portal," not a general ticket intake system — Storage was chosen in Phase 1 as the low-risk category to pilot self-service on first). If someone enters a request that isn't about storage (a broken device, an access request, etc.), the assistant recognizes it's out of scope and redirects them to open a general IT ticket, instead of looping forever trying to extract a storage amount that was never going to be there. A hard 6-turn safety limit also prevents the conversation from running indefinitely if the intent stays unclear.

It covers FR-01 through FR-04 only, the core intake-and-decision flow. It deliberately leaves out of scope, for now: the "duration" field mentioned in the BRD's future-state process, the usage-lookup feature (FR-05), the Storage Team dashboard (FR-06), and mobile support (FR-07) — all noted as possible future extensions rather than built here.

## Results — verified with real, live runs
Unlike a fabricated example, these three transcripts are real conversations run against the live Anthropic API, covering all three paths through the logic:

**1. Small request — auto-approved (at/below the 10 GB placeholder threshold)**
```
You: I need 5 more GB on my mailbox, it's full

Request captured:
  Amount requested : 5.0 GB
  Justification    : mailbox is full

  [STATUS] Submitted
  [STATUS] Auto-approved (at/below the 10 GB placeholder threshold, FR-02)
  [STATUS] Provisioned (simulated)

Your request for 5.0 GB has been auto-approved. No further action needed.
```

**2. Large request — routed to the Storage Team review queue (above the threshold)**
```
You: I need about 50 more GB on my shared drive, we're archiving a large client project and running out of space

Request captured:
  Amount requested : 50.0 GB
  Justification    : archiving a large client project

  [STATUS] Submitted
  [STATUS] Routed to Storage Team review queue (above the 10 GB placeholder threshold, FR-03)

Your request for 50.0 GB has been sent to the Storage Team for manual review.
```

**3. Out-of-scope request — correctly redirected, not force-fit into a storage request**
```
You: my laptop screen is broken

Assistant: This assistant only handles requests for additional mailbox or drive
storage. For other issues, please open a general IT support ticket instead.

(Ending this session -- request was out of scope for this prototype.)
```

All three outcomes are exactly what the design intends: the deterministic threshold rule decided cases 1 and 2 correctly, and the AI correctly recognized the out-of-scope request in case 3 rather than forcing it through the storage flow.

## Honesty notes
- **The threshold is a placeholder, not an approved policy.** The Phase 2 BRD (Assumption #3) states real auto-approval thresholds are "placeholders pending a confirmation workshop with the Storage Team." This prototype uses 10 GB purely to demonstrate the FR-02/FR-03 logic end-to-end.
- **Nothing here is connected to a real storage system, ticketing queue, or email service.** Every status update and "provisioning" step is simulated, printed to the screen. No request submitted here provisions anything or reaches a real person.
- **The AI only extracts information — it does not make the approval decision.** That decision is a fixed, testable Python rule (see `decide()` in `intake_assistant.py`), covered by 11 unit tests in `test_intake_assistant.py` — including the exact threshold boundary (10 GB) and one GB on either side of it, which the two live-run scenarios below didn't happen to land on.
- This is a prototype, not a production system, and it does not represent real company data, a client engagement, or professional work experience.

## Skills demonstrated
**Business/domain (mine):** translating the Phase 2 BRD's functional requirements directly into a working flow; deciding what belongs in AI's hands (understanding free text) versus what must stay deterministic (the approval decision) — a real design judgment, not a default; scoping the prototype down to a defensible, honestly-labeled core rather than overbuilding.

**AI-directed development:** I designed the conversation flow, the field-extraction approach, and — critically — the decision to keep the approval logic outside the AI entirely; Claude AI implemented the code in Python at my direction. I'm not a Python developer; I reviewed, tested, and validated the logic myself. The same split applies to `test_intake_assistant.py`: I identified that my live-run testing (below) never actually exercised the exact 10 GB threshold, only values clearly above and below it, and directed that this gap be closed with dedicated unit tests; Claude wrote the test code, and I ran all 11 tests myself — in Colab, separately from where they were written — and confirmed the results independently rather than taking a "tests exist" claim on faith.

## Tools Used
Python (implemented with Claude AI direction) · Anthropic Claude API · Kaggle-derived dataset context (via Phase 1) · same MoSCoW-prioritized requirements as the Phase 2 BRD

## How to reproduce this
1. Get an Anthropic API key from console.anthropic.com.
2. `pip install -r requirements.txt`
3. Set the key as an environment variable: `export ANTHROPIC_API_KEY=your-key-here` (never hard-code it in a file).
4. `python intake_assistant.py`
5. Describe a storage need when prompted, answer any follow-up questions, and watch the simulated status trail.

## Running the unit tests
The `decide()` function — the deterministic approve/route rule — is covered separately from the live-API flow, so it can be checked instantly with no API key and no network call:
1. `pip install -r requirements-dev.txt` (installs pytest on top of the normal dependencies)
2. `pytest test_intake_assistant.py -v`
3. Expect 11 passed — covering the exact threshold boundary, both live-verified scenarios, the missing-input contract, a custom-threshold override, and one test that documents a known, undecided gap (negative amounts aren't currently rejected) rather than hiding it.

## How I personally verified this
Beyond running the automated `pytest` suite above, I also checked the logic by hand — typing each case myself and reading the actual result, rather than only trusting an automated "11 passed" summary:
- Pasted `decide()` on its own into a fresh Google Colab notebook (no other code, no installs needed) and called it directly with each case — `decide(10)`, `decide(9.99)`, `decide(10.01)`, `decide(5)`, `decide(50)`, `decide(0)`, `decide(None)`, `decide(15, threshold=20)`, `decide(-5)` — confirming every result myself before accepting the automated test file's claim.
- Separately, re-ran the full live conversational flow in Colab a second time — a different session from the one behind `Phase4_Live_Verification_Record.docx` — typing real input at the `You:` prompt exactly as a real user would, to re-confirm the AI-extraction-to-decision handoff still works end to end.
- Designed and documented these as formal test cases using Boundary Value Analysis and Equivalence Partitioning (standard QA/BA techniques), rather than picking numbers arbitrarily — see `Test_Case_Design_Template.xlsx`, which has a reusable blank template plus the 8 actual test cases run against this project's rule.

I don't write Python; Claude implemented `decide()` and `test_intake_assistant.py` at my direction (see "AI-directed development" above). What's mine here is deciding what needed checking, designing the specific scenarios with a standard test-design method, and personally executing and confirming every one of them — independently of how the code itself was written.

## Files in this repo
- `intake_assistant.py` — the full flow: conversational field extraction, deterministic decision logic, simulated status updates
- `test_intake_assistant.py` — automated unit tests for the deterministic `decide()` logic (11 tests, no API required)
- `Test_Case_Design_Template.xlsx` — the same coverage as a reusable, no-code test case document (Instructions, blank Template, and a Worked Example tab matching this project), showing the manual verification described above
- `requirements.txt` — Python dependencies to run the assistant
- `requirements-dev.txt` — adds pytest, for running the automated unit tests
- `Phase4_Live_Verification_Record.docx` — the three real, live-run transcripts (and one screenshot) behind the "Results" section above

## Note
This is a personal, self-directed portfolio project — Phase 4 of a multi-part initiative — built on the Phase 2 BRD's own requirements. It does not represent real company data, a client engagement, or professional work experience.
