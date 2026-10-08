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
    """Raised when a CasePilot policy cannot be loaded from S3."""


def _s3_client():
    """
    Create an S3 client using the AWS credential chain.

    Credentials can therefore come from the configured AWS
    environment, IAM role, AWS CLI configuration, or another
    supported boto3 credential provider.
    """

    return boto3.client("s3")


def _build_policy_key(filename: str) -> str:
    """
    Build the S3 object key for a policy file.
    """

    filename = str(filename or "").strip().lstrip("/")

    if not filename:
        raise S3PolicyError(
            "Policy filename cannot be empty."
        )

    prefix = str(S3_PREFIX or "").strip().strip("/")

    if prefix:
        return f"{prefix}/{filename}"

    return filename


@lru_cache(maxsize=4)
def get_policy(filename: str) -> dict:
    """
    Load a JSON policy from the private CasePilot S3 bucket.

    Policies are cached in-process so repeated tool calls do not
    repeatedly download the same policy.

    Current policy files:

        policies/amazon_policy.json
        policies/casepilot_policy.json
    """

    key = _build_policy_key(filename)

    try:

        response = _s3_client().get_object(
            Bucket=S3_BUCKET,
            Key=key,
        )

        content = response["Body"].read().decode(
            "utf-8"
        )

        policy = json.loads(content)

        if not isinstance(policy, dict):
            raise S3PolicyError(
                f"Policy file '{key}' must contain "
                "a JSON object."
            )

        return policy

    except S3PolicyError:
        raise

    except (ClientError, BotoCoreError) as exc:

        raise S3PolicyError(
            "Unable to load policy from "
            f"s3://{S3_BUCKET}/{key}: {exc}"
        ) from exc

    except UnicodeDecodeError as exc:

        raise S3PolicyError(
            f"Policy file '{key}' is not valid UTF-8."
        ) from exc

    except json.JSONDecodeError as exc:

        raise S3PolicyError(
            f"Policy file '{key}' contains invalid JSON."
        ) from exc

    except KeyError as exc:

        raise S3PolicyError(
            f"S3 response for '{key}' did not contain "
            f"the expected field: {exc}"
        ) from exc