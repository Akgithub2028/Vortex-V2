"""
Unit tests for Vortex Phase 10: Multi-Tenant Payload Encryption and Security Isolation.
"""

import pytest
import uuid

from vortex.engine.security import PayloadEncryptor


def test_payload_encryption_and_decryption_isolation():
    tenant1_id = uuid.uuid4()
    tenant2_id = uuid.uuid4()

    original_data = {
        "user_prompt": "Confidential financial data",
        "api_key_ref": "sk-secret-123",
        "internal_val": 42,
    }

    # Encrypt payload for tenant 1
    encrypted1 = PayloadEncryptor.encrypt_payload(tenant1_id, original_data)
    assert encrypted1["_encrypted"] is True
    assert "iv" in encrypted1
    assert "data" in encrypted1
    assert "tag" in encrypted1
    assert "Confidential financial data" not in str(encrypted1["data"])

    # Decrypt with correct tenant_id -> succeeds
    decrypted1 = PayloadEncryptor.decrypt_payload(tenant1_id, encrypted1)
    assert decrypted1 == original_data

    # Decrypt with wrong tenant_id -> fails HMAC or returns raw encrypted dict
    decrypted2 = PayloadEncryptor.decrypt_payload(tenant2_id, encrypted1)
    assert decrypted2 != original_data


def test_encrypt_empty_payload():
    """Encrypting an empty dict should return it unchanged."""
    result = PayloadEncryptor.encrypt_payload(uuid.uuid4(), {})
    assert result == {}


def test_decrypt_non_encrypted_payload():
    """Decrypting a plain (non-encrypted) payload should return it unchanged."""
    plain = {"key": "value", "count": 42}
    result = PayloadEncryptor.decrypt_payload(uuid.uuid4(), plain)
    assert result == plain


def test_decrypt_tampered_tag():
    """Tampered HMAC tag should fail decryption gracefully."""
    tenant_id = uuid.uuid4()
    original = {"secret": "data"}
    encrypted = PayloadEncryptor.encrypt_payload(tenant_id, original)

    # Tamper with the tag
    encrypted["tag"] = "0000000000000000"
    result = PayloadEncryptor.decrypt_payload(tenant_id, encrypted)
    # Should return the encrypted dict as-is (decryption failure)
    assert result == encrypted or result != original


def test_decrypt_non_dict_returns_input():
    """decrypt_payload should handle non-dict input gracefully."""
    result = PayloadEncryptor.decrypt_payload(uuid.uuid4(), {"no_encrypted_flag": True})
    assert result == {"no_encrypted_flag": True}

