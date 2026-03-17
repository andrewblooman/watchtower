"""Amazon Bedrock client using Claude for investigation reasoning."""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

import boto3

from agent.config import settings
from agent.session import InvestigationSession


class BedrockClient:
    """Sends investigation context to Claude via Amazon Bedrock and records each turn."""

    def __init__(self, session: InvestigationSession) -> None:
        self._session = session
        self._turn = 0
        kwargs: dict[str, Any] = {"region_name": settings.bedrock_region}
        if settings.bedrock_endpoint_url:
            kwargs["endpoint_url"] = settings.bedrock_endpoint_url
        self._client = boto3.client("bedrock-runtime", **kwargs)

    def _system_prompt(self) -> str:
        return (
            "You are an expert SRE debugging agent investigating a deployment issue.\n"
            f"Repository: {settings.github_repo}\n"
            f"Commit: {settings.commit_sha[:7]}\n"
            f"Service: {settings.service_name}\n"
            f"Environment: {settings.environment}\n\n"
            "Your goals:\n"
            "1. Analyze provided logs, metrics, and context.\n"
            "2. Identify the root cause.\n"
            "3. Recommend remediation steps.\n"
            "4. State your confidence as a decimal (e.g. 'Confidence: 0.85').\n\n"
            "Be concise and technical. Focus on actionable insights."
        )

    def analyze(self, context: str, prompt_summary: str) -> dict[str, Any]:
        """Send context to Bedrock Claude and record the reasoning turn."""
        self._turn += 1
        ts = datetime.now(UTC).isoformat()
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "system": self._system_prompt(),
            "messages": [{"role": "user", "content": context}],
        }
        try:
            resp = self._client.invoke_model(
                modelId=settings.bedrock_model,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            response_body = json.loads(resp["body"].read())
            response_text = response_body["content"][0]["text"]
            usage = response_body.get("usage", {})
            record = {
                "ts": ts,
                "turn": self._turn,
                "model": settings.bedrock_model,
                "prompt_tokens": usage.get("input_tokens"),
                "completion_tokens": usage.get("output_tokens"),
                "prompt_summary": prompt_summary,
                "response": response_text,
            }
            self._session.append_reasoning(record)
            print(f"[bedrock] Turn {self._turn}: {prompt_summary[:70]}", flush=True)
            return {"success": True, "response": response_text, "turn": self._turn}
        except Exception as exc:
            error_msg = f"Bedrock call failed: {exc}"
            print(f"[bedrock] {error_msg}", flush=True)
            record = {
                "ts": ts,
                "turn": self._turn,
                "model": settings.bedrock_model,
                "prompt_tokens": None,
                "completion_tokens": None,
                "prompt_summary": prompt_summary,
                "response": error_msg,
            }
            self._session.append_reasoning(record)
            return {"success": False, "response": error_msg, "turn": self._turn}

    def generate_rca(self, investigation_context: str) -> str:
        """Generate a final root cause analysis markdown document."""
        prompt = (
            f"{investigation_context}\n\n"
            "Produce a Root Cause Analysis document in Markdown with these sections:\n"
            "## Summary\n## Root Cause\n## Impact\n"
            "## Timeline\n## Remediation Steps\n## Prevention\n"
        )
        result = self.analyze(prompt, "Generating final RCA document")
        return result.get("response", "RCA generation failed.")

    def extract_diagnosis(self, response_text: str) -> dict[str, Any]:
        """Parse confidence score and root cause from a Bedrock response."""
        confidence = 0.5
        m = re.search(r"[Cc]onfidence[:\s]+([0-9]+(?:\.[0-9]+)?)", response_text)
        if m:
            try:
                confidence = max(0.0, min(1.0, float(m.group(1))))
            except ValueError:
                pass
        return {
            "root_cause": response_text[:500],
            "confidence": confidence,
            "recommendation": "See full RCA document for remediation steps.",
        }
