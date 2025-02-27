import hashlib
import json
import logging

import backoff
from langfuse.decorators import langfuse_context, observe
from llm_multiple_choice import DisplayFormat, InvalidChoicesResponseError

from aider.exceptions import InvalidResponseError, SendCompletionError
from aider.llm import litellm
from aider.models import ModelConfig

logger = logging.getLogger(__name__)


def is_anthropic_model(model_name):
    """
    Determine if a model is an Anthropic model by checking:
    - If it contains 'claude' in its name

    Args:
        model_name (str): The name of the model to check

    Returns:
        bool: True if the model is an Anthropic model, False otherwise
    """
    if not model_name:
        return False

    model_name = model_name.lower()

    # Check if it's just a claude model
    if "claude" in model_name:
        return True

    return False


def transform_messages_for_anthropic(messages):
    """
    Transform message sequences for Anthropic models according to these rules:
    - Concatenate all system messages into one opening system message.
    - Ensure there's a user message after the system message.
    - Separate consecutive user messages with assistant messages saying "Understood."
    - Separate consecutive assistant messages with user messages saying "Please continue."
    """
    result = []

    # Combine system messages if present
    system_messages = [msg for msg in messages if msg["role"] == "system"]
    other_messages = [msg for msg in messages if msg["role"] != "system"]

    if system_messages:
        # Handle the case where content might be a list (for image messages)
        combined_content = []
        for msg in system_messages:
            content = msg["content"]
            if isinstance(content, list):
                # For messages containing images, extract text portions
                text_parts = [
                    item["text"]
                    for item in content
                    if isinstance(item, dict) and "text" in item
                ]
                combined_content.extend(text_parts)
            else:
                combined_content.append(content)

        combined_system = {"role": "system", "content": "\n\n".join(combined_content)}
        result.append(combined_system)

    # If no user message follows system, add "Go ahead."
    if not other_messages or other_messages[0]["role"] != "user":
        result.append({"role": "user", "content": "Go ahead."})

    last_role = result[-1]["role"] if result else None
    for msg in other_messages:
        # If two user messages would be consecutive
        if msg["role"] == "user" and last_role == "user":
            result.append({"role": "assistant", "content": "Understood."})
        # If two assistant messages would be consecutive
        elif msg["role"] == "assistant" and last_role == "assistant":
            result.append({"role": "user", "content": "Understood."})

        if isinstance(msg["content"], list):
            # For messages containing images, extract and join text portions
            text_parts = [
                item["text"]
                for item in msg["content"]
                if isinstance(item, dict) and "text" in item
            ]
            msg = dict(msg)  # Make a copy to avoid modifying the original
            msg["content"] = " ".join(text_parts) if text_parts else ""

        result.append(msg)
        last_role = msg["role"]

    return result


def transform_messages_for_o3(messages):
    """Transform message sequences for o3 models.

    Simple conversion of system messages to user messages, preserving order.
    No special handling or message combining needed.
    """
    result = []
    for msg in messages:
        if msg["role"] == "system":
            msg = dict(msg)  # Make a copy to avoid modifying the original
            msg["role"] = "user"
        result.append(msg)
    return result


# from diskcache import Cache
CACHE_PATH = "~/.aider.send.cache.v1"
CACHE = None
# CACHE = Cache(CACHE_PATH)

RETRY_TIMEOUT = 60


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
        InvalidResponseError,
    )


def lazy_litellm_retry_decorator(func):
    def wrapper(*args, **kwargs):
        decorated_func = backoff.on_exception(
            backoff.expo,
            retry_exceptions(),
            max_time=RETRY_TIMEOUT,
            on_backoff=lambda details: print(
                f"{details.get('exception', 'Exception')}\nRetry in {details['wait']:.1f} seconds."
            ),
        )(func)
        return decorated_func(*args, **kwargs)

    return wrapper


def send_completion(
    model_config: ModelConfig,
    messages,
    functions,
    stream,
    temperature=0,
    reasoning_level: int = 0,
    extra_params=None,
    purpose="send-completion",
):
    logger.debug("send_completion input messages: %s", messages)
    logger.debug(
        "send_completion input kwargs: model=%s temperature=%s reasoning_level=%s extra_params=%s",
        model_config.name,
        temperature,
        reasoning_level,
        extra_params,
    )
    """
    Send a completion request to the language model and handle the response.

    This function manages caching and error handling for LLM requests. It uses litellm.completion()
    under the hood, which accepts OpenAI-compatible parameters and passes any non-OpenAI parameters
    directly to the provider as kwargs. litellm.completion() recognizes many OpenAI-compatible
    parameters and converts them for the provider, while simply passing through parameters that
    it does not recognize.

    Args:
        model_config (ModelConfig): The model configuration instance to use.
        messages (list): A list of message dictionaries to send to the model.
        functions (list): A list of function definitions that the model can use.
        stream (bool): Whether to stream the response or not.
        temperature (float, optional): The sampling temperature to use. Only used if the model
            supports temperature. Defaults to 0.
        reasoning_level (int, optional): For reasoning models, sets the reasoning effort level 
            relative to the model's default. Defaults to 0, which means the model's default level.
            Each negative integer step reduces the reasoning effort by one level, and each positive
            integer step increases the reasoning effort by one level. Reasoning effort is truncated
            to the model's minimum and maximum levels.
        extra_params (dict, optional): Additional parameters to pass to litellm.completion().
            These parameters override any matching parameters from model_config.extra_params.
            This includes:
            - OpenAI-compatible parameters (like max_tokens, top_p, etc.)
            - Provider-specific parameters passed through to the provider
        purpose (str, optional): The purpose label for this completion request for Langfuse tracing.
            Defaults to "send-completion".

    Returns:
        tuple: A tuple containing:
            - hash_object (hashlib.sha1): A SHA1 hash object of the request parameters
            - res (litellm.ModelResponse): The model's response object. The structure depends on stream mode:
                When stream=False:
                    - choices[0].message.content: The complete response text
                    - choices[0].tool_calls[0].function: Function call details if tools were used
                    - usage.prompt_tokens: Number of input tokens
                    - usage.completion_tokens: Number of output tokens
                    - usage.total_cost: Total cost in USD if available
                    - usage.prompt_cost: Input cost in USD if available
                    - usage.completion_cost: Output cost in USD if available
                When stream=True:
                    Returns an iterator yielding chunks, where each chunk has:
                    - choices[0].delta.content: The next piece of response text
                    - choices[0].delta.tool_calls[0].function: Partial function call details
                    - usage: Only available in final chunk if stream_options.include_usage=True

    Raises:
        SendCompletionError: If the API returns a non-200 status code
        InvalidResponseError: If the response is missing required fields or empty
        litellm.exceptions.RateLimitError: If rate limit is exceeded
        litellm.exceptions.APIError: For various API-level errors
        litellm.exceptions.Timeout: If the request times out
        litellm.exceptions.APIConnectionError: For network connectivity issues
        litellm.exceptions.ServiceUnavailableError: If the service is unavailable
        litellm.exceptions.InternalServerError: For server-side errors
        TypeError: If model_config is not a ModelConfig instance
    """
    if not isinstance(model_config, ModelConfig):
        error_msg = f"Expected ModelConfig instance, got {type(model_config)}"
        logger.error(error_msg)
        raise TypeError(error_msg)

    # Transform messages for Anthropic and o3 models
    if is_anthropic_model(model_config.name):
        messages = transform_messages_for_anthropic(messages)
        logger.debug("messages after anthropic transform: %s", messages)
    elif "o3" in model_config.name.lower():
        messages = transform_messages_for_o3(messages)
        logger.debug("messages after o3 transform: %s", messages)

    # Start with base kwargs
    kwargs = dict(
        model=model_config.name,
        messages=messages,
        stream=stream,
        purpose=purpose,
    )

    # Build extra_params dict starting with model defaults
    extra = {}
    if model_config.extra_params:
        extra.update(model_config.extra_params)

    # Add request-specific parameters, overriding model defaults
    if extra_params:
        extra.update(extra_params)

    # Add reasoning parameters with highest precedence
    reasoning_result = model_config.map_reasoning_level(reasoning_level)
    if reasoning_result.model_params:
        extra.update(reasoning_result.model_params)

    # Add temperature if model supports it and not in reasoning mode
    if temperature is not None and model_config.use_temperature and not reasoning_result.is_reasoning_enabled:
        extra["temperature"] = temperature

    # Add provider-specific headers if any
    if model_config.extra_headers:
        extra["extra_headers"] = dict(model_config.extra_headers)

    # Layer in any remaining parameters from extra
    if extra:
        kwargs.update(extra)

    # Create cache key from final kwargs
    key = json.dumps(kwargs, sort_keys=True).encode()

    # Generate SHA1 hash of kwargs to use as a cache key
    hash_object = hashlib.sha1(key)

    if not stream and CACHE is not None and key in CACHE:
        return hash_object, CACHE[key]

    # Call the actual LLM function with the model name and all kwargs
    logger.debug("_send_completion_to_litellm kwargs: %s", kwargs)
    res = _send_completion_to_litellm(
        model_config=model_config,
        **kwargs,
    )

    if not stream and CACHE is not None:
        CACHE[key] = res

    return hash_object, res


@observe(as_type="generation", capture_output=False)
def _send_completion_to_litellm(
    model_config: ModelConfig, purpose="(unlabeled)", **litellm_kwargs
):
    """
    Send a completion request to the language model and handle the response.

    This function handles Langfuse integration and parameter validation for litellm.completion().
    It is an internal implementation detail and should not be called directly.

    Args:
        model_config (ModelConfig): The model configuration instance to use.
        purpose (str, optional): The purpose label for this completion request for Langfuse tracing.
            Defaults to "(unlabeled)".
        **kwargs: Additional arguments passed directly to litellm.completion().

    Returns:
        litellm.ModelResponse: The model's response object. See litellm.completion() for details.

    Raises:
        SendCompletionError: If the API returns a non-200 status code
        InvalidResponseError: If the response is missing required fields or empty
        litellm.exceptions.RateLimitError: If rate limit is exceeded
        litellm.exceptions.APIError: For various API-level errors
        TypeError: If model_config is not a ModelConfig instance
    """
    if not isinstance(model_config, ModelConfig):
        error_msg = f"Expected ModelConfig instance, got {type(model_config)}"
        logger.error(error_msg)
        raise TypeError(error_msg)

    # Prepare Langfuse parameters
    langfuse_params = {
        "name": purpose,
        "model": model_config.name,
        "input": litellm_kwargs["messages"],
        "metadata": {
            "parameters": litellm_kwargs,
        },
    }
    langfuse_context.update_current_observation(**langfuse_params)

    try:
        res = litellm.completion(**litellm_kwargs)
    except (litellm.exceptions.RateLimitError, litellm.exceptions.APIError) as e:
        # Log the error before re-raising for retry
        logger.warning(f"LiteLLM error ({type(e).__name__}): {str(e)}")
        # Re-raise these exceptions to be handled by the retry decorator
        raise

    # Handle None response
    if res is None:
        error_message = f"Received None response from {model_config.name}"
        logger.error(error_message)
        raise InvalidResponseError(error_message)

    # Check for non-200 status code first
    if hasattr(res, "status_code") and res.status_code != 200:
        error_message = f"Error sending completion to {model_config.name}: {res.status_code} - {res.text}"
        raise SendCompletionError(error_message, status_code=res.status_code)

    usage = None
    if hasattr(res, "usage"):
        usage = {
            "input": res.usage.prompt_tokens,
            "output": res.usage.completion_tokens,
            "unit": "TOKENS",
        }

        # Add cost information if available
        if hasattr(res.usage, "total_cost"):
            usage["total_cost"] = res.usage.total_cost
        elif hasattr(res.usage, "completion_cost") and hasattr(
            res.usage, "prompt_cost"
        ):
            usage["input_cost"] = res.usage.prompt_cost
            usage["output_cost"] = res.usage.completion_cost

    if litellm_kwargs.get("stream"):
        langfuse_context.update_current_observation(usage=usage, name=purpose)
    else:
        # Handle case where response has text but no choices
        if not hasattr(res, "choices"):
            error_message = (
                f"Response from {model_config.name} has no choices attribute"
            )
            logger.error(error_message + "\nResponse: " + str(res))
            raise InvalidResponseError(error_message)

        # Handle empty choices list
        if len(res.choices) == 0:
            error_message = f"Received empty choices list from {model_config.name}"
            logger.error(error_message + "\nResponse: " + str(res))
            raise InvalidResponseError(error_message)

        output = None
        choice = res.choices[0]

        # Handle function calls
        if hasattr(choice, "tool_calls") and choice.tool_calls:
            tool_call = choice.tool_calls[0]
            if hasattr(tool_call, "function"):
                output = tool_call.function

        # Handle regular content
        if hasattr(choice, "message") and hasattr(choice.message, "content"):
            output = choice.message.content

        langfuse_context.update_current_observation(
            output=output if output else None,
            usage=usage if usage else None,
        )

    return res


@observe
def analyze_assistant_response(
    choice_manager,
    introduction,
    model_config,
    response_text,
):
    """
    Analyze an assistant's response using a multiple choice questionnaire.

    This function analyzes a single response string using a questionnaire. It's a more
    focused version of analyze_chat_situation that takes just the response text rather
    than the full chat context.

    Args:
        choice_manager (ChoiceManager): The choice manager containing the questionnaire
        introduction (str): An introduction to the questionnaire explaining the context and goal.
            Write this as though for a human who will fill out the questionnaire. Refer to the
            assistant's response as appearing "below" -- it will automatically be appended
            at the end of the prompt, in a markdown section titled "Assistant's Response".
        model_config (ModelConfig): The model configuration to use
        response_text (str): The assistant's response text to analyze

    Returns:
        ChoiceCodeSet: The validated set of choices made by the model

    Raises:
        InvalidChoicesResponseError: If the model's response cannot be validated even after retries
    """
    max_retries = 3
    previous_response = None
    previous_error = None

    for attempt in range(max_retries):
        prompt = choice_manager.prompt_for_choices(DisplayFormat.MARKDOWN, introduction)
        if attempt > 0:
            # Include previous error in retry attempts
            prompt += "\n\n# Previous Error\n\n"
            prompt += f"You previously responded with this: {previous_response}\n\n"
            prompt += f"That response gave the following error:\n{previous_error}\n\nPlease try again."

        prompt += "\n\n# Assistant's Response\n\n" + response_text

        chat_messages = [{"role": "user", "content": prompt}]
        _hash, response = send_completion(
            model_config=model_config,
            messages=chat_messages,
            functions=None,
            stream=False,
            temperature=0,
            reasoning_level=-2,
            purpose=f"analyze assistant response (attempt {attempt + 1})",
        )
        content = response.choices[0].message.content

        try:
            return choice_manager.validate_choices_response(content)
        except InvalidChoicesResponseError as e:
            previous_response = content
            previous_error = str(e)
            if attempt == max_retries - 1:  # Last attempt
                raise  # Re-raise the last error if all retries failed
            logger.warning(
                f"Invalid choices response (attempt {attempt + 1}): {previous_error}"
            )


@lazy_litellm_retry_decorator
def simple_send_with_retries(
    model_config: ModelConfig, messages, extra_params=None, purpose="send with retries"
):
    """
    Send a completion request with retries on various error conditions.

    This function wraps send_completion with retry logic for handling various error types.
    It will retry on connection errors, rate limit errors, and invalid responses.

    Args:
        model_config (ModelConfig): The model configuration to use
        messages (list): A list of message dictionaries to send to the model
        extra_params (dict, optional): Additional parameters to pass to the model.
            This includes:
            - OpenAI-compatible parameters like max_tokens, top_p, etc.
            - Provider-specific parameters passed through to the provider
        purpose (str, optional): The purpose label for this completion request for Langfuse tracing.
            Defaults to "send with retries".

    Returns:
        str: The content of the model's response

    Raises:
        SendCompletionError: If the request fails with a non-200 status code
        InvalidResponseError: If the response is missing required fields or empty
    """
    kwargs = {
        "model_config": model_config,
        "messages": messages,
        "functions": None,
        "stream": False,
        "extra_params": extra_params,
        "purpose": purpose,
    }

    _hash, response = send_completion(**kwargs)

    # Extract content from response
    if hasattr(response, "choices") and response.choices:
        return response.choices[0].message.content
    else:
        error_message = f"Invalid response from {model_config.name}: missing choices"
        logger.error(error_message)
        raise InvalidResponseError(error_message)
