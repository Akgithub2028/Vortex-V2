# VoRTeX Enterprise Security Model

VoRTeX is engineered to serve as a multi-tenant backend engine for enterprise AI applications. Security, tenant isolation, and cryptographic integrity are enforced across every layer.

---

## 1. Authentication & Access Control (RBAC)

- **API Key Hashing:** All client API keys (`vtx_live_...`) are hashed using SHA-256 before storage in the database `api_keys` table. Raw keys are never stored.
- **Role-Based Access Control (RBAC):**
  - **Owner / Admin:** Full control over workspace, keys, prompts, and workflow runs.
  - **Member:** Can trigger workflow executions and view read models.
  - **Viewer:** Read-only access to workflow run status and evaluation results.
- **Tenant Isolation:** Every database query and event store write is scoped explicitly to the authenticated `tenant_id`.

---

## 2. Cryptographic Payload Envelope Encryption

Sensitive workflow variables, prompt inputs, and output payloads are protected at rest using HKDF envelope encryption (`src/vortex/engine/security.py`):

1. **HMAC-based Key Derivation (HKDF):** A master system key isolates unique tenant encryption keys using HKDF-SHA256 with tenant ID salt.
2. **Payload Envelope:** Encrypted payloads are formatted as JSON envelopes containing version metadata, nonce/salt, and ciphertext.
3. **Data Integrity:** Decryption verifies payload integrity tags, preventing unauthorized tampering or cross-tenant data leakage.

---

## 3. Safety Guardrails Engine

All LLM requests routed through `ModelRouter` undergo two-stage inline guardrail scanning:

1. **Prompt Injection Defense (`PromptInjectionValidator`):** Scans inputs for jailbreak patterns (DAN framing, system prompt extraction, shell execution commands). High-risk matches trigger `GuardrailBlockError` or log warnings depending on configuration.
2. **PII Detection & Redaction (`PIIValidator`):** Detects personal identifiers (Social Security Numbers, Credit Cards, Email addresses, Phone numbers) and redacts them prior to external provider API dispatch.
3. **Content Policy Validation (`ContentPolicyValidator`):** Enforces policy rules against toxic or dangerous content payloads.

---

## 4. Input Length & Argument Sanitization

- **Variable Resolution:** `ToolNode` validates variable placeholders (`$var`) against `state.variables` to prevent tool injection.
- **Prompt Field Boundaries:** Input fields are validated against maximum character limits to defend against resource exhaustion / denial-of-service attacks.
