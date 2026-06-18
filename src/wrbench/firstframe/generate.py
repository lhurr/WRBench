"""First-frame image generation from T2I prompts."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


class T2IProvider(Protocol):
    def generate(self, *, prompt: str, family_id: str, out_path: Path) -> dict[str, Any]: ...


@dataclass
class FirstFrameManifest:
    family_id: str
    prompt: str
    image_path: str
    provider: str
    model: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "prompt": self.prompt,
            "image_path": self.image_path,
            "provider": self.provider,
            "model": self.model,
            "metadata": self.metadata,
        }


def _require_httpx():
    try:
        import httpx  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "First-frame generation requires httpx. Install with: pip install 'wrbench[firstframe]'"
        ) from exc


class DashScopeT2IProvider:
    """Generate first frames via DashScope multimodal-generation API."""

    ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

    def __init__(
        self,
        *,
        model: str = "wan2.7-image-pro",
        api_key: str | None = None,
        timeout: float = 180.0,
    ) -> None:
        _require_httpx()
        import httpx

        self.model = model
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("WRBENCH_T2I_API_KEY")
        if not self.api_key:
            raise RuntimeError("DashScope API key required: set DASHSCOPE_API_KEY or WRBENCH_T2I_API_KEY")
        self._client = httpx.Client(timeout=timeout)

    def generate(self, *, prompt: str, family_id: str, out_path: Path) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
            "parameters": {"size": "1280*720", "n": 1},
        }
        resp = self._client.post(
            self.ENDPOINT,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        urls = _extract_image_urls(data)
        if not urls:
            b64 = _extract_image_b64(data)
            if b64:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(base64.b64decode(b64))
                return {"source": "base64", "model": self.model}
            raise RuntimeError(f"No image in DashScope response: {data}")
        # Download first URL
        import httpx

        img_resp = self._client.get(urls[0])
        img_resp.raise_for_status()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(img_resp.content)
        return {"source": "url", "url": urls[0], "model": self.model}


class MockT2IProvider:
    """Write a minimal PNG placeholder for tests (1x1 transparent)."""

    def __init__(self, *, model: str = "mock") -> None:
        self.model = model

    def generate(self, *, prompt: str, family_id: str, out_path: Path) -> dict[str, Any]:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Minimal valid PNG (1x1)
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )
        out_path.write_bytes(png)
        return {"source": "mock", "model": self.model, "prompt_len": len(prompt)}


def get_t2i_provider(name: str | None = None, **kwargs: Any) -> T2IProvider:
    provider = (name or os.environ.get("WRBENCH_T2I_PROVIDER") or "dashscope").strip().lower()
    if provider == "mock":
        model = kwargs.pop("model", "mock")
        kwargs.pop("api_key", None)
        return MockT2IProvider(model=model)
    if provider in {"dashscope", "wan"}:
        return DashScopeT2IProvider(**kwargs)
    raise ValueError(f"Unknown T2I provider {provider!r}; expected dashscope or mock")


def generate_first_frame(
    *,
    family_id: str,
    prompt: str,
    out_dir: str | Path,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    t2i: T2IProvider | None = None,
) -> FirstFrameManifest:
    """Generate ``{family_id}.png`` under *out_dir* and return manifest."""
    out_dir = Path(out_dir)
    image_path = out_dir / f"{family_id}.png"
    if t2i is None:
        t2i = get_t2i_provider(provider, model=model or os.environ.get("WRBENCH_T2I_MODEL", "wan2.7-image-pro"), api_key=api_key)
    meta = t2i.generate(prompt=prompt, family_id=family_id, out_path=image_path)
    provider_name = provider or os.environ.get("WRBENCH_T2I_PROVIDER") or "dashscope"
    model_name = model or meta.get("model") or os.environ.get("WRBENCH_T2I_MODEL") or "wan2.7-image-pro"
    return FirstFrameManifest(
        family_id=family_id,
        prompt=prompt,
        image_path=str(image_path),
        provider=provider_name,
        model=str(model_name),
        metadata=meta,
    )


def generate_first_frames_from_families(
    families: list[dict[str, Any]],
    *,
    out_dir: str | Path,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    t2i: T2IProvider | None = None,
    skip_existing: bool = True,
) -> list[FirstFrameManifest]:
    """Generate first frames for families that have ``t2i_scene``."""
    manifests: list[FirstFrameManifest] = []
    out_dir = Path(out_dir)
    for family in families:
        family_id = str(family["family_id"])
        prompt = str(family.get("t2i_scene") or "").strip()
        if not prompt:
            continue
        image_path = out_dir / f"{family_id}.png"
        if skip_existing and image_path.is_file():
            manifests.append(
                FirstFrameManifest(
                    family_id=family_id,
                    prompt=prompt,
                    image_path=str(image_path),
                    provider=provider or "skipped",
                    model=model or "",
                    metadata={"skipped": True},
                )
            )
            continue
        manifests.append(
            generate_first_frame(
                family_id=family_id,
                prompt=prompt,
                out_dir=out_dir,
                provider=provider,
                model=model,
                api_key=api_key,
                t2i=t2i,
            )
        )
    return manifests


def write_manifest(path: str | Path, manifests: list[FirstFrameManifest]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = [m.to_dict() for m in manifests]
    p.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def _extract_image_urls(data: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    output = data.get("output") or {}
    for choice in output.get("choices") or []:
        message = choice.get("message") or {}
        for item in message.get("content") or []:
            if isinstance(item, dict) and item.get("image"):
                urls.append(str(item["image"]))
            if isinstance(item, dict) and item.get("url"):
                urls.append(str(item["url"]))
    return urls


def _extract_image_b64(data: dict[str, Any]) -> str | None:
    output = data.get("output") or {}
    for choice in output.get("choices") or []:
        message = choice.get("message") or {}
        for item in message.get("content") or []:
            if isinstance(item, dict) and item.get("image_base64"):
                return str(item["image_base64"])
    return None
