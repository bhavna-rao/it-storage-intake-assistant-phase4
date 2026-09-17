"""
Storage Request Self-Service Intake Assistant
================================================
Phase 4 of the IT Service Ticket Classification initiative.

What this does
--------------
A small, conversational, terminal-based prototype of the self-service
storage request flow specified in the Phase 2 BRD (FR-01 through FR-04):

1. FR-01: lets the requester describe their storage need in their own
   words, instead of opening a general helpdesk ticket.
2. Uses Claude to extract two structured fields from that free text: the
   amount of storage requested (converted to GB) and the business
   justification. If either is missing, it asks a follow-up question
   rather than guessing. It also checks whether the request is actually
   about storage at all -- this assistant is intentionally scoped to
   storage requests only (matching the Phase 2 BRD's own scope), so an
   out-of-scope request (a broken device, an access request, etc.) gets
   a polite redirect instead of the assistant looping forever trying to
   extract a storage amount that was never going to be there.
3. FR-02 / FR-03: once both fields are known, a plain, deterministic
   Python rule -- not the AI -- decides whether the request is
   auto-approved (at/below the policy threshold) or routed to the
   Storage Team's review queue (above it). This is the one part of the
   flow that must always be correct, so it is not left to the AI.
4. FR-04: prints a simulated status trail (submitted -> approved/queued
   -> provisioned) the way real email notifications would fire in a
   production system.

Honesty note on the threshold
------------------------------
The Phase 2 BRD (Assumption #3) states that real auto-approval thresholds
are "placeholders pending a confirmation workshop with the Storage Team."
AUTO_APPROVE_THRESHOLD_GB below is exactly that: a placeholder used to
demonstrate the FR-02/FR-03 logic end-to-end, not a real approved policy
number.

Requirements
------------
- An Anthropic API key, set as the environment variable ANTHROPIC_API_KEY
  (never hard-code a key in this file or commit one to git).
- pip install anthropic

Run
---
    python intake_assistant.py
"""

import os
import sys
import json
from datetime import datetime

try:
    import anthropic
except ImportError:
    print("Missing dependency. Run: pip install anthropic")
    sys.exit(1)

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
MODEL = os.environ.get("INTAKE_MODEL", "claude-haiku-4-5")

# Placeholder policy threshold -- see "Honesty note on the threshold" above.
AUTO_APPROVE_THRESHOLD_GB = 10

EXTRACT_SYSTEM_PROMPT = """You are helping fill out a simple IT storage request form.
This assistant ONLY handles requests for additional mailbox or drive storage space.
It does not handle broken devices, access/permission requests, HR questions, purchasing,
project questions, or anything else.

From the conversation so far, extract three things:
- in_scope: true if this is (or could plausibly be) a request for more storage/mailbox/
  drive space. false ONLY if the message is clearly about something else entirely (e.g.
  a broken laptop, a password reset, an access request, an HR question). If unsure,
  use true rather than false.
- amount_gb: the additional storage being requested, converted to a number in gigabytes (GB).
  Convert MB to GB by dividing by 1000. If the amount is vague ("a bit more", "some extra
  space") with no number given anywhere, leave this null.
- justification: a short phrase capturing why they need it, in their own words. Leave this
  null if no reason has been given yet.

Respond with ONLY a JSON object, no other text, no markdown fences:
{"in_scope": <true/false>, "amount_gb": <number or null>, "justification": <string or null>}
"""


def extract_fields(client, transcript):
    """Ask Claude to pull (in_scope, amount_gb, justification) out of the
    conversation so far. Never used to make the approval decision --
    only to understand what the requester typed and whether this
    assistant is even the right tool for their request."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        system=EXTRACT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": transcript}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
    default = {"in_scope": True, "amount_gb": None, "justification": None}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = default
    if not isinstance(data, dict):
        data = default
    if "in_scope" not in data or not isinstance(data.get("in_scope"), bool):
        data["in_scope"] = True
    return data


def decide(amount_gb, threshold=AUTO_APPROVE_THRESHOLD_GB):
    """Pure, deterministic decision logic -- no AI involved.
    This is what actually implements FR-02 (auto-approve at/below
    threshold) and FR-03 (route above-threshold requests to the
    review queue). Kept separate from the AI extraction step on
    purpose: the business rule must always be correct, so it is not
    left to a model to infer."""
    if amount_gb is None:
        raise ValueError("amount_gb must be a number to decide")
    if amount_gb <= threshold:
        return "auto_approved"
    return "routed_for_review"


def print_status(label):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"  [STATUS] {label}  ({stamp})")


def run_intake():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY is not set. Export it before running this script.")
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)

    print("=" * 60)
    print("IT Storage Request Self-Service Intake Assistant (Phase 4 prototype)")
    print("=" * 60)
    print("Hi! I can help you request additional mailbox or drive storage.")
    print('What do you need, and why? (e.g. "I need 5 more GB on my mailbox, it\'s full")')
    print()

    transcript = ""
    amount_gb = None
    justification = None
    MAX_TURNS = 6  # safety net so the assistant can never loop forever

    for turn in range(1, MAX_TURNS + 1):
        if amount_gb is not None and justification is not None:
            break
        user_input = input("You: ").strip()
        if not user_input:
            continue
        transcript += f"\nUser: {user_input}"
        fields = extract_fields(client, transcript)

        if not fields.get("in_scope", True):
            print(
                "\nAssistant: This assistant only handles requests for additional "
                "mailbox or drive storage. For other issues, please open a general "
                "IT support ticket instead.\n"
            )
            print("(Ending this session -- request was out of scope for this prototype.)")
            return

        if fields.get("amount_gb") is not None:
            try:
                amount_gb = float(fields["amount_gb"])
            except (TypeError, ValueError):
                amount_gb = None
        if fields.get("justification"):
            justification = fields["justification"]

        if amount_gb is None:
            print("\nAssistant: How much additional storage do you need, in GB?\n")
        elif justification is None:
            print("\nAssistant: Got it. What's the reason for this request?\n")
    else:
        if amount_gb is None or justification is None:
            print(
                f"\nAssistant: I wasn't able to pin down your request after {MAX_TURNS} tries. "
                "Please open a general IT support ticket so a person can help directly."
            )
            print("(Ending this session -- could not complete intake within the turn limit.)")
            return

    print("\n" + "-" * 60)
    print("Request captured:")
    print(f"  Amount requested : {amount_gb} GB")
    print(f"  Justification    : {justification}")
    print("-" * 60 + "\n")

    print_status("Submitted")

    decision = decide(amount_gb)

    if decision == "auto_approved":
        print_status(
            f"Auto-approved (at/below the {AUTO_APPROVE_THRESHOLD_GB} GB placeholder threshold, FR-02)"
        )
        print_status("Provisioned (simulated)")
        print(f"\nYour request for {amount_gb} GB has been auto-approved. No further action needed.")
    else:
        print_status(
            f"Routed to Storage Team review queue (above the {AUTO_APPROVE_THRESHOLD_GB} GB placeholder threshold, FR-03)"
        )
        print(f"\nYour request for {amount_gb} GB has been sent to the Storage Team for manual review.")

    print("\n(This is a simulated prototype -- no real storage system or ticketing queue is connected.)")


if __name__ == "__main__":
    run_intake()
