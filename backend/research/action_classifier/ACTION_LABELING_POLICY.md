# PromptShield Action Labelling Policy

## Purpose

This document defines how prompts are labelled for the experimental PromptShield contextual action classifier.

The classifier predicts one of four actions:

- `allow`
- `review`
- `redact`
- `block`

The classifier must consider the meaning, intent and context of the complete prompt. It must not make decisions from isolated keywords alone.

This research remains separate from the current production application until it passes the required evaluation and safety checks.

## Core Principles

1. Label the user’s apparent intent, not merely the words used.
2. Consider whether the user is requesting actionable assistance.
3. Distinguish harmful requests from educational or protective discussion.
4. Distinguish actual sensitive values from discussions about sensitive data.
5. Use `review` when the available context is genuinely insufficient.
6. Never assume that a topic is harmful merely because it mentions security, identity documents, crime or safety.
7. Prefer false-review over an unjustified automatic block or redaction.
8. Use fictional data in all research examples.

## Action Summary

| Action | Meaning |
|---|---|
| `allow` | The prompt is legitimate and contains no exposed sensitive value |
| `review` | The prompt is suspicious or ambiguous, but automatic blocking or redaction is not sufficiently justified |
| `redact` | The prompt exposes an actual sensitive value that should be removed before forwarding |
| `block` | The prompt clearly requests harmful, unlawful or security-bypassing assistance |

## Decision Priority

When multiple conditions exist, apply this order:

1. A clear harmful or security-bypassing request receives `block`.
2. A non-harmful prompt containing sensitive information receives `redact`.
3. An ambiguous prompt receives `review`.
4. A benign prompt receives `allow`.

If a blocked prompt also contains sensitive information:

- The primary action remains `block`.
- Sensitive values must still be redacted from stored or displayed previews.
- The original unredacted prompt must not be stored.

---

## Allow

Use `allow` when the prompt is benign, legitimate, educational, protective or administrative and does not expose an actual sensitive value.

### Allow examples

```text
Explain how passport applications work.
What documents are legally required to enter the UK?
I lost my passport abroad. What official steps should I take?
I lost my passport abroad. What official steps should I take?
Explain how prompt injection attacks work.
Explain how API tokens should be stored securely.