from __future__ import annotations

import json
import os
from functools import lru_cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError


S3_BUCKET = os.getenv(
    "CASEPILOT_POLICY_BUCKET",
    "casepilot-policies-2026",
)

S3_PREFIX = os.getenv(
    "CASEPILOT_POLICY_PREFIX",
    "policies",
)


class S3PolicyError(Exception):
    """Raised when a policy cannot be loaded from S3."""


def _s3_client():
    """Create an S3 client using the AWS credential chain."""
    return boto3.client("s3")


@lru_cache(maxsize=2)
def get_policy(filename: str) -> dict:
    """
    Load a JSON policy from the private CasePilot S3 bucket.

    The result is cached so repeated agent tool calls do not
    download the same policy repeatedly.
    """

    key = f"{S3_PREFIX}/{filename}"

    try:
        response = _s3_client().get_object(
            Bucket=S3_BUCKET,
            Key=key,
        )

        content = response["Body"].read().decode("utf-8")

        policy = json.loads(content)

        if not isinstance(policy, dict):
            raise S3PolicyError(
                f"Policy file '{key}' must contain a JSON object."
            )

        return policy

    except (ClientError, BotoCoreError) as exc:
        raise S3PolicyError(
            f"Unable to load policy from s3://{S3_BUCKET}/{key}: {exc}"
        ) from exc

    except json.JSONDecodeError as exc:
        raise S3PolicyError(
            f"Policy file '{key}' contains invalid JSON."
        ) from exc