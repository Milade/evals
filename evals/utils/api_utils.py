"""
This file defines various helper functions for interacting with the OpenAI API.
"""

import concurrent
import logging
import os

import backoff
import openai

try:  # pragma: no cover - old openai versions
    openai_error = openai.error  # type: ignore[attr-defined]
except AttributeError:  # pragma: no cover - openai>=1.0

    class _OpenAIErrorModule:
        APIError = openai.APIError
        RateLimitError = openai.RateLimitError
        APIConnectionError = openai.APIConnectionError
        Timeout = openai.APITimeoutError
        ServiceUnavailableError = openai.APIStatusError

    openai_error = _OpenAIErrorModule()

EVALS_THREAD_TIMEOUT = float(os.environ.get("EVALS_THREAD_TIMEOUT", "40"))


@backoff.on_exception(
    wait_gen=backoff.expo,
    exception=(
        openai_error.ServiceUnavailableError,
        openai_error.APIError,
        openai_error.RateLimitError,
        openai_error.APIConnectionError,
        openai_error.Timeout,
    ),
    max_value=60,
    factor=1.5,
)
def openai_completion_create_retrying(*args, **kwargs):
    """
    Helper function for creating a completion.
    `args` and `kwargs` match what is accepted by `openai.Completion.create`.
    """
    result = openai.Completion.create(*args, **kwargs)
    if "error" in result:
        logging.warning(result)
        raise openai_error.APIError(result["error"])
    return result


def request_with_timeout(func, *args, timeout=EVALS_THREAD_TIMEOUT, **kwargs):
    """
    Worker thread for making a single request within allotted time.
    """
    while True:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                result = future.result(timeout=timeout)
                return result
            except concurrent.futures.TimeoutError as e:
                continue


@backoff.on_exception(
    wait_gen=backoff.expo,
    exception=(
        openai_error.ServiceUnavailableError,
        openai_error.APIError,
        openai_error.RateLimitError,
        openai_error.APIConnectionError,
        openai_error.Timeout,
    ),
    max_value=60,
    factor=1.5,
)
def openai_chat_completion_create_retrying(*args, **kwargs):
    """
    Helper function for creating a chat completion.
    `args` and `kwargs` match what is accepted by `openai.ChatCompletion.create`.
    """
    result = request_with_timeout(openai.ChatCompletion.create, *args, **kwargs)
    if "error" in result:
        logging.warning(result)
        raise openai_error.APIError(result["error"])
    return result
