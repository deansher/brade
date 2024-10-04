import hashlib
import json
import logging

import backoff

from aider.dump import dump  # noqa: F401
from aider.llm import litellm
from langfuse.decorators import observe, langfuse_context

logging.basicConfig(level=logging.WARNING)

# from diskcache import Cache


CACHE_PATH = "~/.aider.send.cache.v1"
CACHE = None
# CACHE = Cache(CACHE_PATH)


def retry_exceptions():
    import httpx

    return (
        httpx.ConnectError,
        httpx.RemoteProtocolError,
        httpx.ReadTimeout,
        litellm.exceptions.APIConnectionError,
        litellm.exceptions.APIError,
        litellm.exceptions.RateLimitError,
        litellm.exceptions.ServiceUnavailableError,
        litellm.exceptions.Timeout,
        litellm.exceptions.InternalServerError,
        litellm.llms.anthropic.chat.AnthropicError,
    )


def lazy_litellm_retry_decorator(func):
    def wrapper(*args, **kwargs):
        decorated_func = backoff.on_exception(
            backoff.expo,
            retry_exceptions(),
            max_time=60,
            on_backoff=lambda details: print(
                f"{details.get('exception', 'Exception')}\nRetry in {details['wait']:.1f} seconds."
            ),
        )(func)
        return decorated_func(*args, **kwargs)

    return wrapper


@observe(as_type="generation")
def send_completion(
    model_name,
    messages,
    functions,
    stream,
    temperature=0,
    extra_params=None,
):
    """
    Send a completion request to the language model and handle the response.

    This function sends a request to the specified language model, processes the response,
    and updates Langfuse tracing context. It supports both streaming and non-streaming responses.

    Args:
        model_name (str): The name of the language model to use.
        messages (list): A list of message dictionaries to send to the model.
        functions (list): A list of function definitions that the model can use.
        stream (bool): Whether to stream the response or not.
        temperature (float, optional): The sampling temperature to use. Defaults to 0.
        extra_params (dict, optional): Additional parameters to pass to the model. Defaults to None.

    Returns:
        tuple: A tuple containing:
            - hash_object (hashlib.sha1): A SHA1 hash object of the request parameters.
            - res (litellm.ModelResponse): The model's response object for non-streaming requests.
            - iterator: For streaming requests, returns an iterator that should be consumed by the caller.
              The Langfuse context will be updated after the iterator is exhausted.

    Raises:
        AttributeError: If the response structure is unexpected.
        Exception: For any other unexpected errors during execution.

    Notes:
        - This function uses Langfuse for tracing and monitoring.
        - It handles caching of responses when applicable.
        - The function adapts its behavior based on whether streaming is enabled or not.
        - It updates Langfuse tracing context before and after the LLM call.
    """
    from aider.llm import litellm

    kwargs = dict(
        model=model_name,
        messages=messages,
        stream=stream,
    )
    if temperature is not None:
        kwargs["temperature"] = temperature

    if functions is not None:
        function = functions[0]
        kwargs["tools"] = [dict(type="function", function=function)]
        kwargs["tool_choice"] = {"type": "function", "function": {"name": function["name"]}}

    if extra_params is not None:
        kwargs.update(extra_params)

    key = json.dumps(kwargs, sort_keys=True).encode()

    # Generate SHA1 hash of kwargs and append it to chat_completion_call_hashes
    hash_object = hashlib.sha1(key)

    if not stream and CACHE is not None and key in CACHE:
        return hash_object, CACHE[key]

    # Update Langfuse tracing context before LLM call
    langfuse_context.update_current_observation(
        input={
            'model_name': model_name,
            'messages': messages,
            'functions': functions,
            'stream': stream,
            'temperature': temperature,
            'extra_params': extra_params,
        },
        model=model_name,
    )

    res = litellm.completion(**kwargs)

    if not stream:
        # Non-streaming case
        langfuse_context.update_current_observation(
            output=res.choices,
            usage={
                'input': res.usage.prompt_tokens,
                'output': res.usage.completion_tokens,
            },
        )
        if CACHE is not None:
            CACHE[key] = res
        return hash_object, res
    else:
        # For streaming, wrap the iterator
        return hash_object, stream_with_langfuse(res, model_name)

def stream_with_langfuse(stream_iter, model_name):
    """
    Wrap the streaming iterator to collect output content and usage data for Langfuse.

    This function processes each chunk from the stream, collects the content and usage data,
    and updates the Langfuse context after the stream is exhausted.

    Args:
        stream_iter (iterator): The original streaming iterator from the LLM.
        model_name (str): The name of the model being used.

    Yields:
        dict: Each chunk from the original stream.

    Notes:
        - This function aggregates the content and usage data from all chunks.
        - It updates the Langfuse context with the collected data after the stream is exhausted.
        - If an exception occurs during streaming, it logs the error and re-raises the exception.
        - It logs unexpected chunk structures for debugging purposes.
    """
    output_content = ''
    total_completion_tokens = 0
    prompt_tokens = getattr(stream_iter, 'usage', {}).get('prompt_tokens')

    try:
        for chunk in stream_iter:
            # Collect the content
            if (hasattr(chunk, 'choices') and chunk.choices and
                hasattr(chunk.choices[0], 'delta') and
                hasattr(chunk.choices[0].delta, 'content') and
                chunk.choices[0].delta.content):
                output_content += chunk.choices[0].delta.content
            else:
                # Log unexpected chunk structure for debugging
                logging.warning(f"Unexpected chunk structure: {chunk}")

            # Aggregate usage tokens if available
            if hasattr(chunk, 'usage') and chunk.usage:
                total_completion_tokens += getattr(chunk.usage, 'completion_tokens', 0)
                if prompt_tokens is None:
                    prompt_tokens = getattr(chunk.usage, 'prompt_tokens', None)

            yield chunk
    except Exception as e:
        logging.error(f"Exception occurred during streaming: {e}")
        raise
    finally:
        # After streaming is complete or if an exception occurs, update Langfuse tracing context
        langfuse_context.update_current_observation(
            output=output_content,
            usage={
                'input': prompt_tokens or 0,
                'output': total_completion_tokens,
            },
            model=model_name,
        )


@lazy_litellm_retry_decorator
def simple_send_with_retries(model_name, messages, extra_params=None):
    try:
        kwargs = {
            "model_name": model_name,
            "messages": messages,
            "functions": None,
            "stream": False,
            "extra_params": extra_params,
        }

        _hash, response = send_completion(**kwargs)
        return response.choices[0].message.content
    except (AttributeError, litellm.exceptions.BadRequestError):
        return
