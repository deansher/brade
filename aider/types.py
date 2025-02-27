# This file uses the Brade coding style: full modern type hints and strong documentation.
# Expect to resolve merges manually. See CONTRIBUTING.md.

"""Shared type definitions used across both Aider and Brade style files.

This module defines the core types used throughout the codebase. These types are used:
- As type hints in Brade-style files
- In docstrings and comments in Aider-style files

This provides a consistent vocabulary for types across both coding styles while
preserving merge compatibility where needed.
"""

from typing import Callable, NotRequired, TypedDict


class ImageUrl(TypedDict):
    """Image data for a content block."""

    url: str  # Can be a web URL or data URL
    detail: str  # "low", "high", etc


class CacheControl(TypedDict):
    """Cache control metadata for a content block."""

    type: str  # "ephemeral" etc


class ContentBlock(TypedDict):
    """A block of structured content in a chat message.

    Can represent:
    - Simple text with optional cache control
    - Image data with URL and detail level
    """

    type: str  # "text" or "image_url"
    text: str | None  # Present for text blocks
    image_url: ImageUrl | None  # Present for image blocks
    cache_control: CacheControl | None


class ChatMessage(TypedDict):
    """A message in a chat conversation with an LLM.

    Attributes:
        role: The role of the message sender (system, user, assistant)
        content: The message content, either as a string or structured content
        function_call: Optional function call data
        prefix: Optional flag indicating this message should be prefixed to next completion

    Examples:
        Simple text message:
        >>> msg = ChatMessage(role="user", content="Hello")

        Message with structured content:
        >>> msg = ChatMessage(role="assistant",
        ...                   content=[{"type": "text", "text": "Hi",
        ...                             "image_url": None, "cache_control": None}])
    """

    role: str  # "system", "user", "assistant"
    content: str | list[ContentBlock]
    function_call: NotRequired[dict[str, str] | None]
    # When True, indicates this message contains a truncated response that should be
    # prefixed to the next completion. This enables handling responses that exceed the
    # model's maximum output tokens by allowing the model to continue from where it left off.
    prefix: NotRequired[bool | None]


from dataclasses import dataclass


TokenCountFunc = Callable[[str | ChatMessage | list[ChatMessage]], int]
"""Function that counts tokens in text or chat messages.

Used by models to count tokens in various types of content:
- Plain text strings
- Individual chat messages
- Lists of chat messages
"""


@dataclass
class ReasoningResult:
    """Result from mapping a reasoning level to model-specific parameters.
    
    This class encapsulates whether a model is currently operating in reasoning mode
    (e.g. extended thinking for Anthropic) and what parameters that requires.
    
    Attributes:
        is_reasoning_enabled: True if the model is currently in reasoning mode
        model_params: Model-specific parameters needed for reasoning mode
    """
    is_reasoning_enabled: bool
    model_params: dict[str, Any]


Edit = tuple[str | None, str, str]
"""A tuple representing a code edit extracted from an LLM response.

The tuple is (path, original, updated) where:
- path: The file path to edit, or None for shell commands
- original: The original content to match and replace
- updated: The new content to replace with
"""


class RepoFile(TypedDict):
    """Information about a file in the repository.

    Attributes:
        path: The file path relative to repo root
        content: The file content if available
        size: File size in bytes
    """

    path: str
    content: str | None
    size: int
