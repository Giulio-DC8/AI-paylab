import os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

PRIVATE_KEY_PATH = os.path.join(os.path.dirname(__file__), "private_key.pem")
PUBLIC_KEY_PATH = os.path.join(os.path.dirname(__file__), "public_key.pem")


class IncompleteKeyPairError(Exception):
    """Raised when only one of the two keys exists, not both."""
    pass


def generate_keys():
    """Generates a new Ed25519 key pair and saves it to disk."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(private_bytes)
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(public_bytes)


def _ensure_keys_exist():
    """
    Generates the key pair ONLY if both keys are missing. If only one
    is missing, the situation is ambiguous/dangerous (silently
    regenerating would invalidate previously signed receipts) - raises
    an explicit error instead.
    """
    private_exists = os.path.exists(PRIVATE_KEY_PATH)
    public_exists = os.path.exists(PUBLIC_KEY_PATH)

    if private_exists and public_exists:
        return
    if not private_exists and not public_exists:
        generate_keys()
        return

    missing = "private_key.pem" if public_exists else "public_key.pem"
    raise IncompleteKeyPairError(
        f"Found only one of the two keys in receipt/. Missing {missing}. "
        "Regenerating automatically would invalidate already-signed receipts. "
        "Restore the missing file, or delete the other key as well "
        "and re-run to generate a fresh pair."
    )


def load_private_key():
    _ensure_keys_exist()
    with open(PRIVATE_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def load_public_key():
    _ensure_keys_exist()
    with open(PUBLIC_KEY_PATH, "rb") as f:
        return serialization.load_pem_public_key(f.read())