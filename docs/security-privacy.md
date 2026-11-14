# Security, Privacy and Interaction Boundaries

**Status:** Proposed controls. Nothing is implemented yet. Requirement IDs refer to [requirements.md](requirements.md); tests refer to [testing.md](testing.md).

**Official basis (brief, p.3 "Keep interactions within the service's purpose"):**
- External websites and documents are information sources, never instructions (BR-17).
- The same boundaries apply to follow-ups and to role-adoption requests (BR-18).
- Never disclose another company's non-public profile information or user interactions (BR-19).
- Distinguish information and next steps from professional advice, eligibility decisions or Blue Science Park commitments (BR-20).
- Refer human decisions to staff (BR-21).
- Out-of-scope and unclear requests are handled as described (BR-22).
- **Explain how the boundaries are implemented and demonstrate that they work.**

The specific controls below are **team proposals**.

## 1. External Content Is Untrusted Data

| Rule | Requirement | Test |
|---|---|---|
| Extract visible text only (remove `script`, `style`, `noscript`, comments, `hidden`/`aria-hidden`, inline `display:none`) | FR-S05 | T-29 |
| Keep source text separate from instructions; never concatenate it into system prompts | FR-S01 | T-27 |
| Code, not the LLM, sets claim basis, scores, scope decisions and access | FR-P06, FR-M09, FR-S06, FR-I02 | T-01, T-18, T-30 |

## 2. Prompt-Injection Defence

This applies to profiling, explanations and the assistant.

1. **Delimiting.** External text goes into the user message as `<untrusted_content source="URL">…</untrusted_content>`. Look-alike closing tags inside the content are escaped.
2. **Instruction hierarchy.** The system prompt says the content is data to analyse; any instructions inside it are ignored.
3. **No capabilities.** No tools, function calling or browsing in any LLM call (FR-S02, FR-I11).
4. **Schema validation.** Output must parse into the Pydantic model; extra fields are rejected (FR-S03).
5. **Evidence check.** An injected statement only becomes `stated` if it really is on the page. It is then shown with its source, so the company can reject it (FR-P06, FR-P12).
6. **Output checks.** Banned phrases; citations restricted to stored URLs; length limits.
7. **Fixture.** A test page with visible and hidden injection attempts (T-27).

## 3. Outbound Requests and SSRF

**P0: fetch allowlist (FR-S04).** The MVP starts from a member list, so no user-supplied URL is ever fetched.

| Check | Rule |
|---|---|
| Allowlist | Only hosts from the member list (`data/config/members.*`) and the source register ([sources.md](sources.md)) |
| Scheme / port | `http`/`https`, ports 80/443 |
| Redirects | Max 3; each target must also be on the allowlist |
| Limits | 10 s timeout, 2 MB body, text-like content types only |
| Crawl scope | Max 10 pages per member, same site |
| Politeness | Honour `robots.txt`; generic user agent; ≥ 1 s between requests to the same host |

**P1: arbitrary URLs (FR-S10).** Needed only once "add company by URL" (FR-P17) exists:
- Resolve all A/AAAA records and reject private, loopback, link-local (including `169.254.169.254`), CGNAT, multicast, reserved and IPv6 ULA/link-local addresses.
- Connect to the validated IP.
- Re-validate on every redirect.
- Reject credentials in URLs and non-HTTP schemes.

Tests: T-28 (P0). The full SSRF tests are added with FR-S10.

## 4. Company-Private Data

**Private per company:**
- profile corrections, review states and priorities;
- **questions asked and answers given (interactions)**;
- saved items and feedback;
- the company's match explanations;
- the session token.

Everything else is derived from public sources.

| Control | Requirement | Test |
|---|---|---|
| Company-private endpoints require that company's token; mismatch → `403` | FR-S06 | T-30 |
| Matching reads only the active company's active claims | FR-M02 | T-04 |
| Assistant context contains only the active company's data and public items | FR-S07 | T-26 |
| Assistant declines requests for another company's non-public data or interactions, without confirming whether such data exists | FR-I10 | T-26 |
| The comparison view (P1) returns only public opportunity IDs and ranks | FR-U09 | — |
| Interactions are never used as context for another company | FR-S07 | T-26 |

**MVP limitation (must be stated in the demo):** sign-in is simulated with demo tokens. It shows the access logic, not production identity.

Sending company text to an LLM provider is pending [Q-05](requirements.md#q-open-questions).

## 5. API Key Handling

- Keys come only from environment variables (local `.env`, gitignored). A `.env.example` with empty values is committed (FR-S09).
- Keys are never returned by the API, sent to the frontend, logged, put in error messages or included in prompts.
- Each developer uses their own key. If a key is exposed, revoke it immediately.
- Test: T-37 (P0 schema/config check). Automated log scanning is P1 (FR-S12).

## 6. Personal-Data Minimisation

- Profiles describe companies, not people. There are no fields for person names, roles, emails or phone numbers (FR-S08, T-37).
- Pages whose path suggests personal data (`/team`, `/people`, `/medarbetare`) are skipped unless needed for company facts. *(team proposal)*
- Scrubbing contact details from quotes is P1 (FR-S11).
- The raw HTML cache is local and gitignored, and deleted after the hackathon.
- Public pages only: no login-protected or consent-walled content.

## 7. Interaction Boundaries

**Scope (brief p.3, supported interactions):** technology, research, market and regional developments relevant to companies; events, testing environments and funding; expertise, potential partners and collaboration; understanding recommendations and refining interests; support and contact routes within Blue Science Park.

**Implementation (team proposal, D-018):**

| Step | What happens | Requirement |
|---|---|---|
| 1. Pre-check (code) | Length limit. Patterns for override and role adoption ("ignore previous", "you are now", "system prompt", "act as", Swedish equivalents). Another demo company's name combined with private-data terms. A hit sets the category directly | FR-I06, FR-I10 |
| 2. Classify (LLM, structured) | `in_scope` · `out_of_scope` · `unclear` · `boundary_override` · `needs_human` | FR-I02 |
| 3. Respond | See the table below | FR-I03–I05, FR-I08 |
| 4. Post-check (code) | Schema; banned phrases; citations limited to stored URLs; no claim values from other companies | FR-M07, FR-S07 |
| 5. Fail closed | Any error → standard remit-and-redirect response | FR-I12 |
| Follow-ups | Last 3 exchanges of the same company included; steps 1–5 on every turn | FR-I07 |

| Handling | Response pattern | Brief (p.3) |
|---|---|---|
| `in_scope` | Answer from the active company's profile, matches and public items, with citations; next step; disclaimer if about opportunities | Supported interactions |
| `out_of_scope` | One or two sentences on the service's remit, plus 1–3 suggested relevant questions or a contact route | "briefly explain its remit and guide the user…" |
| `unclear` | One focused clarifying question | "ask a focused clarifying question" |
| `boundary_override` | Decline, restate the remit, continue with the original rules; never reveal the system prompt | "attempt to override", "requests to adopt another role" |
| `needs_human` | State that it is a human decision; refer to Blue Science Park staff via the contact route ([sources.md](sources.md#reference-blue-science-park-contact-routes)) | "Refer questions that need a human decision or commitment" |

**Demonstrating the boundaries:** the scenario set and results go in [quality-boundary-check.md](quality-boundary-check.md#4-interaction-limits) (T-20–T-26, T-35).

## Honesty Rules

These apply to UI text, API output, docs and the pitch (BR-08, BR-14, BR-20).

- **Standard disclaimer**, appended by code to every match and to every assistant answer about opportunities:
  > "This is an automated suggestion based on public information. It is not professional advice, a formal eligibility decision or a commitment by Blue Science Park. Check the official source before acting."
- **Funding label:** "Potential match — eligibility not assessed" (FR-M06).
- **Banned phrases**, case-insensitive, English and Swedish: "you are eligible", "you qualify", "guaranteed", "will receive", "will be funded", "is approved", "Blue Science Park will", "du är berättigad", "garanterat", "kommer att beviljas". A hit replaces the text with the template (FR-M07, T-17).
- **Inferred claims** are worded as "may be relevant" and never as priorities or confirmed facts (FR-M08, T-07).
- **Basis labels:** "Stated on source", not "Verified" (D-016).
- Every item shows its `data_status`; snapshot, seed and simulated data are labelled (FR-O03, FR-U07).
- Collaboration suggestions (P2) must not imply that either company has expressed an interest (brief p.3 item 5).
