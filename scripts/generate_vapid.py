import base64
import os

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
PRIVATE_KEY_PATH = os.path.join(ROOT_DIR, "vapid_private.pem")


def main():
    vapid = Vapid()
    vapid.generate_keys()
    vapid.save_key(PRIVATE_KEY_PATH)

    public_key_bytes = vapid.public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).rstrip(b"=").decode("utf-8")

    print("Private key saved to:", PRIVATE_KEY_PATH)
    print("Public key:", public_key_b64)


if __name__ == "__main__":
    main()
