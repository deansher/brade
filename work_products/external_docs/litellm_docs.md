# **Input Params**

## **Common Params[​](https://docs.litellm.ai/docs/completion/input#common-params)**

LiteLLM accepts and translates the [OpenAI Chat Completion params](https://platform.openai.com/docs/api-reference/chat/create) across all providers.

### **Usage[​](https://docs.litellm.ai/docs/completion/input#usage)**

import litellm

*\# set env variables*  
os.environ\["OPENAI\_API\_KEY"\] \= "your-openai-key"

*\#\# SET MAX TOKENS \- via completion()*  
response \= litellm.completion(  
           model="gpt-3.5-turbo",  
           messages=\[{ "content": "Hello, how are you?","role": "user"}\],  
           max\_tokens=10  
       )

print(response)

### **Translated OpenAI params[​](https://docs.litellm.ai/docs/completion/input#translated-openai-params)**

Use this function to get an up-to-date list of supported openai params for any model \+ provider.  
from litellm import get\_supported\_openai\_params

response \= get\_supported\_openai\_params(model="anthropic.claude-3", custom\_llm\_provider="bedrock")

print(response) *\# \["max\_tokens", "tools", "tool\_choice", "stream"\]*

This is a list of openai params we translate across providers.

Use `litellm.get_supported_openai_params()` for an updated list of params for each model \+ provider

| Provider | temperature | max\_completion\_tokens | max\_tokens | top\_p | stream | stream\_options | stop | n | presence\_penalty | frequency\_penalty | functions | function\_call | logit\_bias | user | response\_format | seed | tools | tool\_choice | logprobs | top\_logprobs | extra\_headers |  |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| Anthropic | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  | ✅ | ✅ | ✅ | ✅ | ✅ |  |  | ✅ |  |
| OpenAI | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |
| Azure OpenAI | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  | ✅ |  |
| Replicate | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Anyscale | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Cohere | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Huggingface | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Openrouter | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  | ✅ | ✅ |  |  |  |  |  |
| AI21 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |  |  |  |  |  |  |
| VertexAI | ✅ | ✅ | ✅ |  | ✅ | ✅ |  |  |  |  |  |  |  |  | ✅ | ✅ |  |  |  |  |  |  |
| Bedrock | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |  |  | ✅ (model dependent) |  |  |  |  |  |  |
| Sagemaker | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| TogetherAI | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  | ✅ |  |  | ✅ |  | ✅ | ✅ |  |  |  |  |
| AlephAlpha | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| NLP Cloud | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Petals | ✅ | ✅ |  | ✅ | ✅ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Ollama | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  | ✅ |  |  |  |  | ✅ |  |  | ✅ |  |  |  |  |  |
| Databricks | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ClarifAI | ✅ | ✅ | ✅ |  | ✅ | ✅ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Github | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |  |  |  | ✅ | ✅ (model dependent) | ✅ (model dependent) |  |  |  |  |

note

By default, LiteLLM raises an exception if the openai param being passed in isn't supported.

To drop the param instead, set `litellm.drop_params = True` or `completion(..drop_params=True)`.

This ONLY DROPS UNSUPPORTED OPENAI PARAMS.

LiteLLM assumes any non-openai param is provider specific and passes it in as a kwarg in the request body

## **Input Params[​](https://docs.litellm.ai/docs/completion/input#input-params-1)**

def completion(  
   model: str,  
   messages: List \= \[\],  
   *\# Optional OpenAI params*  
   timeout: Optional\[Union\[float, int\]\] \= None,  
   temperature: Optional\[float\] \= None,  
   top\_p: Optional\[float\] \= None,  
   n: Optional\[int\] \= None,  
   stream: Optional\[bool\] \= None,  
   stream\_options: Optional\[dict\] \= None,  
   stop=None,  
   max\_completion\_tokens: Optional\[int\] \= None,  
   max\_tokens: Optional\[int\] \= None,  
   presence\_penalty: Optional\[float\] \= None,  
   frequency\_penalty: Optional\[float\] \= None,  
   logit\_bias: Optional\[dict\] \= None,  
   user: Optional\[str\] \= None,  
   *\# openai v1.0+ new params*  
   response\_format: Optional\[dict\] \= None,  
   seed: Optional\[int\] \= None,  
   tools: Optional\[List\] \= None,  
   tool\_choice: Optional\[str\] \= None,  
   parallel\_tool\_calls: Optional\[bool\] \= None,  
   logprobs: Optional\[bool\] \= None,  
   top\_logprobs: Optional\[int\] \= None,  
   deployment\_id=None,  
   *\# soon to be deprecated params by OpenAI*  
   functions: Optional\[List\] \= None,  
   function\_call: Optional\[str\] \= None,  
   *\# set api\_base, api\_version, api\_key*  
   base\_url: Optional\[str\] \= None,  
   api\_version: Optional\[str\] \= None,  
   api\_key: Optional\[str\] \= None,  
   model\_list: Optional\[list\] \= None,  *\# pass in a list of api\_base,keys, etc.*  
   *\# Optional liteLLM function params*  
   \*\*kwargs,

) \-\> ModelResponse:

### **Required Fields[​](https://docs.litellm.ai/docs/completion/input#required-fields)**

* `model`: *string* \- ID of the model to use. Refer to the model endpoint compatibility table for details on which models work with the Chat API.  
* `messages`: *array* \- A list of messages comprising the conversation so far.

#### **Properties of `messages`[​](https://docs.litellm.ai/docs/completion/input#properties-of-messages)**

*Note* \- Each message in the array contains the following properties:

* `role`: *string* \- The role of the message's author. Roles can be: system, user, assistant, function or tool.  
* `content`: *string or list\[dict\] or null* \- The contents of the message. It is required for all messages, but may be null for assistant messages with function calls.  
* `name`: *string (optional)* \- The name of the author of the message. It is required if the role is "function". The name should match the name of the function represented in the content. It can contain characters (a-z, A-Z, 0-9), and underscores, with a maximum length of 64 characters.  
* `function_call`: *object (optional)* \- The name and arguments of a function that should be called, as generated by the model.  
* `tool_call_id`: *str (optional)* \- Tool call that this message is responding to.

[See All Message Values](https://github.com/BerriAI/litellm/blob/8600ec77042dacad324d3879a2bd918fc6a719fa/litellm/types/llms/openai.py#L392)

## **Optional Fields[​](https://docs.litellm.ai/docs/completion/input#optional-fields)**

* `temperature`: *number or null (optional)* \- The sampling temperature to be used, between 0 and 2\. Higher values like 0.8 produce more random outputs, while lower values like 0.2 make outputs more focused and deterministic.  
* `top_p`: *number or null (optional)* \- An alternative to sampling with temperature. It instructs the model to consider the results of the tokens with top\_p probability. For example, 0.1 means only the tokens comprising the top 10% probability mass are considered.  
* `n`: *integer or null (optional)* \- The number of chat completion choices to generate for each input message.  
* `stream`: *boolean or null (optional)* \- If set to true, it sends partial message deltas. Tokens will be sent as they become available, with the stream terminated by a \[DONE\] message.  
* `stream_options` *dict or null (optional)* \- Options for streaming response. Only set this when you set `stream: true`  
  * `include_usage` *boolean (optional)* \- If set, an additional chunk will be streamed before the data: \[DONE\] message. The usage field on this chunk shows the token usage statistics for the entire request, and the choices field will always be an empty array. All other chunks will also include a usage field, but with a null value.  
* `stop`: *string/ array/ null (optional)* \- Up to 4 sequences where the API will stop generating further tokens.  
* `max_completion_tokens`: *integer (optional)* \- An upper bound for the number of tokens that can be generated for a completion, including visible output tokens and reasoning tokens.  
* `max_tokens`: *integer (optional)* \- The maximum number of tokens to generate in the chat completion.  
* `presence_penalty`: *number or null (optional)* \- It is used to penalize new tokens based on their existence in the text so far.  
* `response_format`: *object (optional)* \- An object specifying the format that the model must output.  
  * Setting to `{ "type": "json_object" }` enables JSON mode, which guarantees the message the model generates is valid JSON.  
  * Important: when using JSON mode, you must also instruct the model to produce JSON yourself via a system or user message. Without this, the model may generate an unending stream of whitespace until the generation reaches the token limit, resulting in a long-running and seemingly "stuck" request. Also note that the message content may be partially cut off if finish\_reason="length", which indicates the generation exceeded max\_tokens or the conversation exceeded the max context length.  
* `seed`: *integer or null (optional)* \- This feature is in Beta. If specified, our system will make a best effort to sample deterministically, such that repeated requests with the same seed and parameters should return the same result. Determinism is not guaranteed, and you should refer to the `system_fingerprint` response parameter to monitor changes in the backend.  
* `tools`: *array (optional)* \- A list of tools the model may call. Currently, only functions are supported as a tool. Use this to provide a list of functions the model may generate JSON inputs for.  
  * `type`: *string* \- The type of the tool. Currently, only function is supported.  
  * `function`: *object* \- Required.  
* `tool_choice`: *string or object (optional)* \- Controls which (if any) function is called by the model. none means the model will not call a function and instead generates a message. auto means the model can pick between generating a message or calling a function. Specifying a particular function via `{"type: "function", "function": {"name": "my_function"}}` forces the model to call that function.  
  * `none` is the default when no functions are present. `auto` is the default if functions are present.  
* `parallel_tool_calls`: *boolean (optional)* \- Whether to enable parallel function calling during tool use.. OpenAI default is true.  
* `frequency_penalty`: *number or null (optional)* \- It is used to penalize new tokens based on their frequency in the text so far.  
* `logit_bias`: *map (optional)* \- Used to modify the probability of specific tokens appearing in the completion.  
* `user`: *string (optional)* \- A unique identifier representing your end-user. This can help OpenAI to monitor and detect abuse.  
* `timeout`: *int (optional)* \- Timeout in seconds for completion requests (Defaults to 600 seconds)  
* `logprobs`: *bool (optional)* \- Whether to return log probabilities of the output tokens or not. If true returns the log probabilities of each output token returned in the content of message  
* `top_logprobs`: *int (optional)* \- An integer between 0 and 5 specifying the number of most likely tokens to return at each token position, each with an associated log probability. `logprobs` must be set to true if this parameter is used.

#### **Deprecated Params[​](https://docs.litellm.ai/docs/completion/input#deprecated-params)**

* `functions`: *array* \- A list of functions that the model may use to generate JSON inputs. Each function should have the following properties:  
  * `name`: *string* \- The name of the function to be called. It should contain a-z, A-Z, 0-9, underscores and dashes, with a maximum length of 64 characters.  
  * `description`: *string (optional)* \- A description explaining what the function does. It helps the model to decide when and how to call the function.  
  * `parameters`: *object* \- The parameters that the function accepts, described as a JSON Schema object.  
* `function_call`: *string or object (optional)* \- Controls how the model responds to function calls.

#### **litellm-specific params[​](https://docs.litellm.ai/docs/completion/input#litellm-specific-params)**

* `api_base`: *string (optional)* \- The api endpoint you want to call the model with  
* `api_version`: *string (optional)* \- (Azure-specific) the api version for the call  
* `num_retries`: *int (optional)* \- The number of times to retry the API call if an APIError, TimeoutError or ServiceUnavailableError occurs  
* `context_window_fallback_dict`: *dict (optional)* \- A mapping of model to use if call fails due to context window error  
* `fallbacks`: *list (optional)* \- A list of model names \+ params to be used, in case the initial call fails  
* `metadata`: *dict (optional)* \- Any additional data you want to be logged when the call is made (sent to logging integrations, eg. promptlayer and accessible via custom callback function)

CUSTOM MODEL COST

* `input_cost_per_token`: *float (optional)* \- The cost per input token for the completion call  
* `output_cost_per_token`: *float (optional)* \- The cost per output token for the completion call

CUSTOM PROMPT TEMPLATE (See [prompt formatting for more info](https://docs.litellm.ai/docs/completion/prompt_formatting#format-prompt-yourself))

* `initial_prompt_value`: *string (optional)* \- Initial string applied at the start of the input messages  
* `roles`: *dict (optional)* \- Dictionary specifying how to format the prompt based on the role \+ message passed in via `messages`.  
* `final_prompt_value`: *string (optional)* \- Final string applied at the end of the input messages  
* `bos_token`: *string (optional)* \- Initial string applied at the start of a sequence  
* `eos_token`: *string (optional)* \- Initial string applied at the end of a sequence  
* `hf_model_name`: *string (optional)* \- \[Sagemaker Only\] The corresponding huggingface name of the model, used to pull the right chat template for the model.

# **Prompt Formatting**

LiteLLM automatically translates the OpenAI ChatCompletions prompt format, to other models. You can control this by setting a custom prompt template for a model as well.

## **Huggingface Models[​](https://docs.litellm.ai/docs/completion/prompt_formatting#huggingface-models)**

LiteLLM supports [Huggingface Chat Templates](https://huggingface.co/docs/transformers/main/chat_templating), and will automatically check if your huggingface model has a registered chat template (e.g. [Mistral-7b](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1/blob/main/tokenizer_config.json#L32)).

For popular models (e.g. meta-llama/llama2), we have their templates saved as part of the package.

Stored Templates

| Model Name | Works for Models | Completion Call |
| ----- | ----- | ----- |
| mistralai/Mistral-7B-Instruct-v0.1 | mistralai/Mistral-7B-Instruct-v0.1 | `completion(model='huggingface/mistralai/Mistral-7B-Instruct-v0.1', messages=messages, api_base="your_api_endpoint")` |
| meta-llama/Llama-2-7b-chat | All meta-llama llama2 chat models | `completion(model='huggingface/meta-llama/Llama-2-7b', messages=messages, api_base="your_api_endpoint")` |
| tiiuae/falcon-7b-instruct | All falcon instruct models | `completion(model='huggingface/tiiuae/falcon-7b-instruct', messages=messages, api_base="your_api_endpoint")` |
| mosaicml/mpt-7b-chat | All mpt chat models | `completion(model='huggingface/mosaicml/mpt-7b-chat', messages=messages, api_base="your_api_endpoint")` |
| codellama/CodeLlama-34b-Instruct-hf | All codellama instruct models | `completion(model='huggingface/codellama/CodeLlama-34b-Instruct-hf', messages=messages, api_base="your_api_endpoint")` |
| WizardLM/WizardCoder-Python-34B-V1.0 | All wizardcoder models | `completion(model='huggingface/WizardLM/WizardCoder-Python-34B-V1.0', messages=messages, api_base="your_api_endpoint")` |
| Phind/Phind-CodeLlama-34B-v2 | All phind-codellama models | `completion(model='huggingface/Phind/Phind-CodeLlama-34B-v2', messages=messages, api_base="your_api_endpoint")` |

[Jump to code](https://github.com/BerriAI/litellm/blob/main/litellm/llms/prompt_templates/factory.py)

## **Format Prompt Yourself[​](https://docs.litellm.ai/docs/completion/prompt_formatting#format-prompt-yourself)**

You can also format the prompt yourself. Here's how:  
import litellm  
*\# Create your own custom prompt template*  
litellm.register\_prompt\_template(  
       model="togethercomputer/LLaMA-2-7B-32K",  
       initial\_prompt\_value="You are a good assistant" *\# \[OPTIONAL\]*  
       roles={  
           "system": {  
               "pre\_message": "\[INST\] \<\<SYS\>\>\\n", *\# \[OPTIONAL\]*  
               "post\_message": "\\n\<\</SYS\>\>\\n \[/INST\]\\n" *\# \[OPTIONAL\]*  
           },  
           "user": {  
               "pre\_message": "\[INST\] ", *\# \[OPTIONAL\]*  
               "post\_message": " \[/INST\]" *\# \[OPTIONAL\]*  
           },  
           "assistant": {  
               "pre\_message": "\\n" *\# \[OPTIONAL\]*  
               "post\_message": "\\n" *\# \[OPTIONAL\]*  
           }  
       }  
       final\_prompt\_value="Now answer as best you can:" *\# \[OPTIONAL\]*  
)

def test\_huggingface\_custom\_model():  
   model \= "huggingface/togethercomputer/LLaMA-2-7B-32K"  
   response \= completion(model=model, messages=messages, api\_base="https://my-huggingface-endpoint")  
   print(response\['choices'\]\[0\]\['message'\]\['content'\])  
   return response

test\_huggingface\_custom\_model()

This is currently supported for Huggingface, TogetherAI, Ollama, and Petals.

Other providers either have fixed prompt templates (e.g. Anthropic), or format it themselves (e.g. Replicate). If there's a provider we're missing coverage for, let us know\!

# **Streaming \+ Async**

* [Streaming Responses](https://docs.litellm.ai/docs/completion/stream#streaming-responses)  
* [Async Completion](https://docs.litellm.ai/docs/completion/stream#async-completion)  
* [Async \+ Streaming Completion](https://docs.litellm.ai/docs/completion/stream#async-streaming)

## **Streaming Responses[​](https://docs.litellm.ai/docs/completion/stream#streaming-responses)**

LiteLLM supports streaming the model response back by passing `stream=True` as an argument to the completion function

### **Usage[​](https://docs.litellm.ai/docs/completion/stream#usage)**

from litellm import completion  
messages \= \[{"role": "user", "content": "Hey, how's it going?"}\]  
response \= completion(model="gpt-3.5-turbo", messages=messages, stream=True)  
for part in response:  
   print(part.choices\[0\].delta.content or "")

### **Helper function[​](https://docs.litellm.ai/docs/completion/stream#helper-function)**

LiteLLM also exposes a helper function to rebuild the complete streaming response from the list of chunks.  
from litellm import completion  
messages \= \[{"role": "user", "content": "Hey, how's it going?"}\]  
response \= completion(model="gpt-3.5-turbo", messages=messages, stream=True)

for chunk in response:  
   chunks.append(chunk)

print(litellm.stream\_chunk\_builder(chunks, messages=messages))

## **Async Completion[​](https://docs.litellm.ai/docs/completion/stream#async-completion)**

Asynchronous Completion with LiteLLM. LiteLLM provides an asynchronous version of the completion function called `acompletion`

### **Usage[​](https://docs.litellm.ai/docs/completion/stream#usage-1)**

from litellm import acompletion  
import asyncio

async def test\_get\_response():  
   user\_message \= "Hello, how are you?"  
   messages \= \[{"content": user\_message, "role": "user"}\]  
   response \= await acompletion(model="gpt-3.5-turbo", messages=messages)  
   return response

response \= asyncio.run(test\_get\_response())  
print(response)

## **Async Streaming[​](https://docs.litellm.ai/docs/completion/stream#async-streaming)**

We've implemented an `__anext__()` function in the streaming object returned. This enables async iteration over the streaming object.

### **Usage[​](https://docs.litellm.ai/docs/completion/stream#usage-2)**

Here's an example of using it with openai.  
from litellm import acompletion  
import asyncio, os, traceback

async def completion\_call():  
   try:  
       print("test acompletion \+ streaming")  
       response \= await acompletion(  
           model="gpt-3.5-turbo",  
           messages=\[{"content": "Hello, how are you?", "role": "user"}\],  
           stream=True  
       )  
       print(f"response: {response}")  
       async for chunk in response:  
           print(chunk)  
   except:  
       print(f"error occurred: {traceback.format\_exc()}")  
       pass

asyncio.run(completion\_call())

## **Error Handling \- Infinite Loops[​](https://docs.litellm.ai/docs/completion/stream#error-handling---infinite-loops)**

Sometimes a model might enter an infinite loop, and keep repeating the same chunks \- [e.g. issue](https://github.com/BerriAI/litellm/issues/5158)

Break out of it with:  
litellm.REPEATED\_STREAMING\_CHUNK\_LIMIT \= 100 *\# \# catch if model starts looping the same chunk while streaming. Uses high default to prevent false positives.*

LiteLLM provides error handling for this, by checking if a chunk is repeated 'n' times (Default is 100). If it exceeds that limit, it will raise a `litellm.InternalServerError`, to allow retry logic to happen.

* SDK  
* PROXY

import litellm  
import os

litellm.set\_verbose \= False  
loop\_amount \= litellm.REPEATED\_STREAMING\_CHUNK\_LIMIT \+ 1  
chunks \= \[  
   litellm.ModelResponse(\*\*{  
   "id": "chatcmpl-123",  
   "object": "chat.completion.chunk",  
   "created": 1694268190,  
   "model": "gpt-3.5-turbo-0125",  
   "system\_fingerprint": "fp\_44709d6fcb",  
   "choices": \[  
       {"index": 0, "delta": {"content": "How are you?"}, "finish\_reason": "stop"}  
   \],  
}, stream=True)  
\] \* loop\_amount  
completion\_stream \= litellm.ModelResponseListIterator(model\_responses=chunks)

response \= litellm.CustomStreamWrapper(  
   completion\_stream=completion\_stream,  
   model="gpt-3.5-turbo",  
   custom\_llm\_provider="cached\_response",  
   logging\_obj=litellm.Logging(  
       model="gpt-3.5-turbo",  
       messages=\[{"role": "user", "content": "Hey"}\],  
       stream=True,  
       call\_type="completion",  
       start\_time=time.time(),  
       litellm\_call\_id="12345",  
       function\_id="1245",  
   ),  
)

for chunk in response:  
   continue *\# expect to raise InternalServerError*  