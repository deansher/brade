[langfuse.com /docs/tracing](https://langfuse.com/docs/tracing)

# **LLM Observability & Application Tracing**

4-5 minutes

---

LLM applications use increasingly complex abstractions, such as chains, agents with tools, and advanced prompts. **Nested traces** in Langfuse help to understand what is happening and identify the root cause of problems.

*Example trace of our [public demo](https://langfuse.com/docs/demo)*

## **Why Use Tracing to gain observability into an LLM Application?**

* Capture the full context of the execution, including API calls, context, prompts, parallelism, and more  
* Track model usage and cost  
* Collect user feedback  
* Identify low-quality outputs  
* Build fine-tuning and testing datasets

## **Why Use Langfuse?**

* Open-source  
* Low performance overhead  
* SDKs for Python and JavaScript  
* Integrated with popular frameworks: OpenAI SDK (Python), Langchain (Python, JS), LlamaIndex (Python)  
* Multi-Modal tracing support  
* Public API for custom integrations  
* Suite of tools for the whole LLM application development lifecycle

## **Introduction to Observability & Traces in Langfuse**

A trace in Langfuse consists of the following objects:

* A typically represents a single request or operation. It contains the overall input and output of the function, as well as metadata about the request, such as the user, the session, and tags.  
* Each trace can contain multiple to log the individual steps of the execution.  
  * Observations are of different types:  
    * are the basic building blocks. They are used to track discrete events in a trace.  
    * represent durations of units of work in a trace.  
    * are spans used to log generations of AI models. They contain additional attributes about the model, the prompt, and the completion. For generations, [token usage and costs](https://langfuse.com/docs/model-usage-and-cost) are automatically calculated.  
  * Observations can be nested.

**Hierarchical structure of traces in Langfuse**

1

n

Nesting

Trace

Observation

Event

Span

Generation

**Example trace in Langfuse UI**

**![Trace in Langfuse UI][image1]**

**Example trace in Langfuse UI**

**![Trace in Langfuse UI][image2]**

## **Get Started**

Follow the quickstart to add Langfuse tracing to your LLM app.

## **Advanced usage**

You can extend the tracing capabilities of Langfuse by using the following features:

## **Enable/disable tracing**

All Langfuse SDKs and integrations are designed to be non-intrusive. You can add Langfuse tracing to your application while being able to enable it only in specific environments.

By default, the Langfuse Tracing is enabled if an API key is set. You can manually disable tracing via the flag. See the documentation for the specific SDK or integration for more details.

## **Event queuing/batching**

Langfuse’s client SDKs and integrations are all designed to queue and batch requests in the background to optimize API calls and network time. Batches are determined by a combination of time and size (number of events and size of batch).

### **Configuration**

All integrations have a sensible default configuration, but you can customise the batching behaviour to suit your needs.

You can e.g. set to send every event immediately, or to send every second.

### **Manual flushing**

If you want to send a batch immediately, you can call the method on the client. In case of network issues, flush will log an error and retry the batch, it will never throw an exception.

If you exit the application, use method to make sure all requests are flushed and pending requests are awaited before the process exits. On success of this function, no more events will be sent to Langfuse API.

## **FAQ**

* [How do I link prompt management with tracing in Langfuse to see which prompt versions were used?](https://langfuse.com/faq/all/link-prompt-management-with-tracing)  
* [How to manage different environments in Langfuse?](https://langfuse.com/faq/all/managing-different-environments)  
* [I have setup Langfuse, but I do not see any traces in the dashboard. How to solve this?](https://langfuse.com/faq/all/missing-traces)

Last updated on September 29, 2024

[Self-host (docker)](https://langfuse.com/docs/deployment/self-host)[Quickstart](https://langfuse.com/docs/get-started)

### **Was this page useful?**

### **Questions? We're here to help**

### **Subscribe to updates**

[langfuse.com /docs/sdk/python/decorators](https://langfuse.com/docs/sdk/python/decorators)

# **Decorator-based Python Integration \- Langfuse**

8-10 minutes

---

Integrate [Langfuse Tracing](https://langfuse.com/docs/tracing) into your LLM applications with the Langfuse Python SDK using the decorator.

The SDK supports both synchronous and asynchronous functions, automatically handling traces, spans, and generations, along with key execution details like inputs, outputs and timings. This setup allows you to concentrate on developing high-quality applications while benefitting from observability insights with minimal code. The decorator is fully interoperable with our main integrations (more on this below): [OpenAI](https://langfuse.com/docs/integrations/openai), [Langchain](https://langfuse.com/docs/integrations/langchain), [LlamaIndex](https://langfuse.com/docs/integrations/llama-index).

See the [reference](https://python.reference.langfuse.com/langfuse/decorators) for a comprehensive list of all available parameters and methods.

Want more control over the traces logged to Langfuse? Check out the [low-level Python SDK](https://langfuse.com/docs/sdk/python/low-level-sdk).

## **Overview**

## **Example**

*Simple example (decorator \+ openai integration)*

*Trace in Langfuse ([public link](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/fac231bc-90ee-490a-aa32-78c4269474e3?observation=36544d09-dec7-48ff-88c3-6c2ae3fe2baf))*

*![Simple OpenAI decorator trace][image3]*

## **Installation & setup**

## **Decorator arguments**

See [SDK reference](https://python.reference.langfuse.com/langfuse/decorators#observe) for full details.

### **Log any LLM call**

In addition to the native intgerations with LangChain, LlamaIndex, and OpenAI (details [below](https://langfuse.com/docs/sdk/python/decorators#frameworks)), you can log any LLM call by decorating it with . **Important:** Make sure the decorated function is called inside another \-decorated function for it to have a top-level trace.

Optionally, you can parse some of the arguments to the LLM call and pass them to to enrich the trace.

If you want to see an example of how to do this, check out the [example cookbook](https://langfuse.com/guides/cookbook/integration_mistral_sdk) which wraps the Mistral SDK with the decorator.

### **Capturing of input/output**

By default, the decorator captures the input arguments and output results of the function.

**You can disable this** behavior by setting the and parameters to .

The decorator implementation supports capturing any serializable object as input and output such as strings, numbers, lists, dictionaries, and more. Python which are common when streaming LLM responses are supported as return values from decorated functions, but not as input arguments.

You can **manually set the input and output** of the observation using (details below).

This will result in a trace with only sanitized input and output, and no actual function arguments or return values.

## **Decorator context**

Use the object to interact with the decorator context. This object is a thread-local singleton and can be accessed from anywhere within the function context.

### **Configure the Langfuse client**

The decorator manages the Langfuse client for you. If you need to configure the client, you can do so via the method **at the top of your application** before executing any decorated functions.

By setting the parameter to , you can disable the decorator and prevent any traces from being sent to Langfuse.

See the [API Reference](https://python.reference.langfuse.com/langfuse/decorators#LangfuseDecorator.configure) for more details on the available parameters.

### **Add additional attributes to the trace and observations**

In addition to the attributes automatically captured by the decorator, you can add others to use the full features of Langfuse.

Below is an example demonstrating how to enrich traces and observations with custom parameters:

### **Get trace URL**

You can get the URL of the current trace using . Works anywhere within the function context, also in deeply nested functions.

### **Trace/observation IDs**

By default, Langfuse assigns random IDs to all logged events.

#### **Get trace and observation IDs**

You can access the current trace and observation IDs from the object.

#### **Set custom IDs**

If you have your own unique ID (e.g. messageId, traceId, correlationId), you can easily set those as trace or observation IDs for effective lookups in Langfuse. Just pass the keyword argument to the decorated function.

#### **Set parent trace ID or parent span ID**

If you’d like to nest the the observations created from the decoratored function execution under an existing trace or span, you can pass the ID as a value to the or keyword argument to your decorated function. In that case, Langfuse will record that execution not under a standalone trace, but nest it under the provided entity.

This is useful for distributed tracing use-cases, where decorated function executions are running in parallel or in the background and should be associated to single existing trace.

## **Interoperability with framework integrations**

The decorator is fully interoperable with our main integrations: [OpenAI](https://langfuse.com/docs/integrations/openai), [Langchain](https://langfuse.com/docs/integrations/langchain), [LlamaIndex](https://langfuse.com/docs/integrations/llama-index). Thereby you can easily trace and evaluate functions that use (a combination of) these integrations.

### **OpenAI**

The [drop-in OpenAI SDK integration](https://langfuse.com/docs/integrations/openai) is fully compatible with the decorator. It automatically adds a generation observation to the trace within the current context.

### **LangChain**

The [native LangChain integration](https://langfuse.com/docs/integrations/langchain) is fully compatible with the decorator. It automatically adds a generation to the trace within the current context.

exposes a callback handler scoped to the current trace context. Pass it to subsequent runs to your LangChain application to get full tracing within the scope of the current trace.

### **LlamaIndex**

The [LlamaIndex integration](https://langfuse.com/docs/integrations/llama-index) is fully compatible with the decorator. It automatically adds a generation to the trace within the current context.

Via you can configure the callback to use for tracing of the subsequent LlamaIndex executions. exposes a callback handler scoped to the current trace context.

## **Adding scores**

[Scores](https://langfuse.com/docs/scores/overview) are used to evaluate single observations or entire traces. They can be created via our annotation workflow in the Langfuse UI or via the SDKs.

You can attach a score to the current observation context by calling . You can also score the entire trace from anywhere inside the nesting hierarchy by calling :

## **Additional configuration**

### **Flush observations**

The Langfuse SDK executes network requests in the background on a separate thread for better performance of your application. This can lead to lost events in short lived environments such as AWS Lambda functions when the Python process is terminated before the SDK sent all events to our backend.

To avoid this, ensure that the method is called before termination. This method is waiting for all tasks to have completed, hence it is blocking.

### **Debug mode**

Enable debug mode to get verbose logs. Set the debug mode via the environment variable .

### **Sampling**

Sampling can be controlled via the environment variable. See the [sampling documentation](https://langfuse.com/docs/tracing-features/sampling) for more details.

### **Authentication check**

Use to verify that your host and API credentials are valid. This operation is blocking and is not recommended for production use.

## **Limitations**

### **Using ThreadPoolExecutors or ProcessPoolExecutors**

The decorator uses Python’s to store the current trace context and to ensure that the observations are correctly associated with the current execution context. However, when using Python’s ThreadPoolExecutors and ProcessPoolExecutors *and* when spawning threads from inside a trace (i.e. the executor is run inside a decorated function) the decorator will not work correctly as the are not correctly copied to the new threads or processes. There is an [existing issue](https://github.com/python/cpython/pull/9688#issuecomment-544304996) in Python’s standard library and a [great explanation](https://github.com/tiangolo/fastapi/issues/2776#issuecomment-776659392) in the fastapi repo that discusses this limitation.

For example when a @observe-decorated function uses a ThreadPoolExecutor to make concurrent LLM requests the context that holds important info on the nesting hierarchy (“we are inside another trace”) is not copied over correctly to the child threads. So the created generations will not be linked to the trace and be ‘orphaned’. In the UI, you will see a trace missing those generations.

There are 2 possible workarounds:

#### **1\. Pass the parent observation ID (recommended)**

The first and recommended workaround is to pass the parent observation id as a keyword argument to each multithreaded execution, thus re-establishing the link to the parent span or trace:

#### **2\. Copy over the context**

The second workaround is to manually copy over the context to the new threads or processes:

The executions inside the ThreadPoolExecutor will now be correctly associated with the trace opened by the function.

### **Large input/output data**

Large input/output data can lead to performance issues. We recommend disabling capturing input/output for these methods and manually add the relevant information via .

## **API reference**

See the [Python SDK API reference](https://python.reference.langfuse.com/langfuse/decorators) for more details.

## **GitHub Discussions**

* 2votes  
* 1votes  
* 1votes  
* 1votes  
* 1votes  
* 1votes  
* 1votes

Discussions last updated: 9/30/2024, 2:13:42 AM (4 hours ago)

Last updated on September 22, 2024

[Overview](https://langfuse.com/docs/sdk/overview)[Example Notebook](https://langfuse.com/docs/sdk/python/example)

### **Was this page useful?**

### **Questions? We're here to help**

### **Subscribe to updates**

[langfuse.com /docs/sdk/python/low-level-sdk](https://langfuse.com/docs/sdk/python/low-level-sdk)

# **Python SDK (Low-level) \- Langfuse**

8-10 minutes

---

PyPI

This is a Python SDK used to send LLM data to Langfuse in a convenient way. It uses a worker Thread and an internal queue to manage requests to the Langfuse backend asynchronously. Hence, the SDK adds only minimal latency to your application.

For most use cases, you should check out the [decorator-based SDK](https://langfuse.com/docs/sdk/python/decorators), which is more convenient and easier to use. This SDK is more low-level and is only recommended if you need more control over the request process.

## **Installation**

## **Initialize Client**

To start, initialize the client by providing your credentials. You can set the credentials either as environment variables or constructor arguments.

If you are self-hosting Langfuse or using the US data region, don’t forget to configure .

To verify your credentials and host, use the function.

## **Tracing**

The Langfuse SDK and UI are designed to support complex LLM features which contain for example vector database searches and multiple LLM calls. For that, it is very convenient to nest or chain the SDK. Understanding a small number of terms makes it easy to integrate with Langfuse.

**Traces**

A represents a single execution of a LLM feature. It is a container for all succeeding objects.

**Observations**

Each can contain multiple to record individual steps of an execution. There are different types of :

* are the basic building block. They are used to track discrete events in a .  
* track time periods and include an end\_time.  
* are a specific type of which are used to record generations of an AI model. They contain additional metadata about the model, LLM token and cost tracking, and the prompt/completions are specifically rendered in the langfuse UI.

*Example*

### **Traces**

Traces are the top-level entity in the Langfuse API. They represent an execution flow in a LLM application usually triggered by an external event.

Traces can be updated:

You can get the url of a trace in the Langfuse interface. Helpful in interactive use or when adding this url to your logs.

### **Span**

Spans represent durations of units of work in a trace.

Parameters of :

Use trace or observation objects to create child spans:

Other span methods:

* , does not change end\_time if not explicitly set

Alternatively, if using the Langfuse objects is not convenient, you can use the client, and (optionally) to create spans, and to upsert a span.

### **Generation**

Generations are used to log generations of AI models. They contain additional metadata about the model, the prompt/completion, the cost of executing the model and are specifically rendered in the langfuse UI.

Use trace or observation objects to create child generations:

Other generation methods:

* , does not change end\_time if not explicitly set

See documentation of spans above on how to use the langfuse client and ids if you cannot use the Langfuse objects to trace your application. This also fully applies to generations.

### **Events**

Events are used to track discrete events in a trace.

Use trace or observation objects to create child generations:

See documentation of spans above on how to use the langfuse client and ids if you cannot use the Langfuse objects to trace your application. This also fully applies to events.

## **Scores**

[Scores](https://langfuse.com/docs/scores/overview) are used to evaluate single executions/traces. They can be created via Annotation in the Langfuse UI or via the SDKs.

If the score relates to a specific step of the trace, specify the .

## **Additional configurations**

### **Shutdown behavior**

The Langfuse SDK executes network requests in the background on a separate thread for better performance of your application. This can lead to lost events in short lived environments like NextJs cloud functions or AWS Lambda functions when the Python process is terminated before the SDK sent all events to our backend.

To avoid this, ensure that the function is called before termination. This method is waiting for all tasks to have completed, hence it is blocking.

### **Releases and versions**

Track in Langfuse to relate traces in Langfuse with the versioning of your application. This can be done by either providing the environment variable , instantiating the client with the release, or setting it as a trace parameter.

If no release is set, this defaults to [common system environment names](https://github.com/langfuse/langfuse-python/blob/main/langfuse/environment.py#L3).

To track versions of individual pieces of you application apart from releases, use the parameter on all observations. This is for example useful to track the effect of changed prompts.

## **Troubleshooting**

### **Debug mode**

Enable debug mode to get verbose logs.

Alternatively, set the debug mode via the environment variable .

### **Configuration/authentication problems**

Use auth\_check() to verify that your host and api credentials are correct.

### **Google Cloud Functions**

When using Langfuse in a Google Cloud Function or a Firebase Function, the underlying managed Python runtime has issues with threading whenever threads are spawned off the main scope and not inside the actual function scope. [See here](https://www.googlecloudcommunity.com/gc/Serverless/The-issue-with-pythons-s-threading-on-Google-Function/m-p/614384). Since Langfuse uses background threads to deliver the observability events, this will lead to incomplete traces.

Make sure to initialize Langfuse always *inside* the function body. If you want to reuse the created Langfuse clients in different modules, use lazy initialization of the Langfuse client to ensure the actual initialization occurs inside the function execution context.

## **Upgrading from v1.x.x to v2.x.x**

v2 is a major release with breaking changes to simplify the SDK and make it more consistent. We recommend to upgrade to v2 as soon as possible.

You can automatically migrate your codebase using [grit](https://www.grit.io/), either [online](https://app.grit.io/migrations/new/langfuse_v2) or with the following CLI command:

The grit binary executes entirely locally with AST-based transforms. Be sure to audit its changes: we suggest ensuring you have a clean working tree beforehand, and running afterwards.

If your Jupyter Notebooks are not in source control, it might be harder to track changes. You may want to copy each cell individually into grit’s web interface, and paste the output back in.

### **Remove Pydantic interfaces**

We like Pydantic, but it made the Langfuse SDK interfaces messy. Therefore, we removed the objects from the function signatures and replaced them with named parameters.

All parameters are still validated using Pydantic internally. If the validation fails, errors are logged instead of throwing exceptions.

#### **Pydantic objects**

**v1.x.x**

**v2.x.x**

#### **Pydantic Enums**

**v1.x.x**

**v2.x.x**

### **Rename and to and**

To ensure consistency throughout Langfuse, we have renamed the and parameters in the function to and , respectively. This change brings them in line with the rest of the Langfuse API.

### **Snake case parameters**

To increase consistency, all parameters are snake case in v2.

* instead of  
* instead of  
* instead of  
* instead of  
* instead of  
* instead of  
* instead of  
* instead of  
* instead of

### **More generalized usage object**

We improved the flexibility of the SDK by allowing you to ingest any type of usage while still supporting the OpenAI-style usage object.

**v1.x.x**

**v2.x.x**

The usage object supports the OpenAi structure with {, , } and a more generic version {, , , } where unit can be of value or . For some models the token counts and costs are [automatically calculated](https://langfuse.com/docs/model-usage-and-cost) by Langfuse. Create an issue to request support for other units and models.

## **FastAPI**

For engineers working with FastAPI, we have a short example, of how to use it there.

Here is an example of how to initialise FastAPI and register the method to run at shutdown. With this, your Python environment will only terminate once Langfuse received all the events.

Last updated on August 5, 2024

[Example Notebook](https://langfuse.com/docs/sdk/python/example)[Guide](https://langfuse.com/docs/sdk/typescript/guide)

### **Was this page useful?**

### **Questions? We're here to help**

### **Subscribe to updates**

[langfuse.com /docs/sdk/python/example](https://langfuse.com/docs/sdk/python/example)

# **Cookbook: Python Decorators**

The Langfuse Python SDK uses decorators for you to effortlessly integrate observability into your LLM applications. It supports both synchronous and asynchronous functions, automatically handling traces, spans, and generations, along with key execution details like inputs and outputs. This setup allows you to concentrate on developing high-quality applications while benefitting from observability insights with minimal code.

This cookbook containes examples for all key functionalities of the decorator-based integration with Langfuse.

## **Installation & setup**

Install `langfuse`:  
%pip install langfuse

If you haven’t done so yet, [sign up to Langfuse](https://cloud.langfuse.com/auth/sign-up) and obtain your API keys from the project settings. You can also [self-host](https://langfuse.com/docs/deployment/self-host) Langfuse.  
import os \# Get keys for your project from the project settings page\# https://cloud.langfuse.comos.environ\["LANGFUSE\_PUBLIC\_KEY"\] \= ""os.environ\["LANGFUSE\_SECRET\_KEY"\] \= ""os.environ\["LANGFUSE\_HOST"\] \= "https://cloud.langfuse.com" \# 🇪🇺 EU region\# os.environ\["LANGFUSE\_HOST"\] \= "https://us.cloud.langfuse.com" \# 🇺🇸 US region \# Your openai keyos.environ\["OPENAI\_API\_KEY"\] \= ""

## **Basic usage**

Langfuse simplifies observability in LLM-powered applications by organizing activities into traces. Each trace contains observations: spans for nested activities, events for distinct actions, or generations for LLM interactions. This setup mirrors your app’s execution flow, offering insights into performance and behavior. See our [Tracing documentation](https://langfuse.com/docs/tracing) for more details on Langfuse’s telemetry model.

`@observe()` decorator automatically and asynchronously logs nested traces to Langfuse. The outermost function becomes a `trace` in Langfuse, all children are `spans` by default.

By default it captures:

* nesting via context vars  
* timings/durations  
* args and kwargs as input dict  
* returned values as output

from langfuse.decorators import langfuse\_context, observeimport time @observe()def wait():    time.sleep(1) @observe()def capitalize(input: str):    return input.upper() @observe()def main\_fn(query: str):    wait()    capitalized \= capitalize(query)    return f"Q:{capitalized}; A: nice too meet you\!" main\_fn("hi there");

Voilà\! ✨ Langfuse will generate a trace with a nested span for you.  
*Example trace: [https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/21128edc-27bf-4643-92f9-84d66c63de8d](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/21128edc-27bf-4643-92f9-84d66c63de8d)*

## **Add additional parameters to the trace**

In addition to the attributes automatically captured by the decorator, you can add others to use the full features of Langfuse.

Two utility methods:

* `langfuse_context.update_current_observation`: Update the trace/span of the current function scope  
* `langfuse_context.update_current_trace`: Update the trace itself, can also be called within any deeply nested span within the trace

For details on available attributes, have a look at the [reference](https://python.reference.langfuse.com/langfuse/decorators#LangfuseDecorator.update_current_observation)

Below is an example demonstrating how to enrich traces and observations with custom parameters:  
from langfuse.decorators import langfuse\_context, observe @observe(as\_type="generation")def deeply\_nested\_llm\_call():    \# Enrich the current observation with a custom name, input, and output    langfuse\_context.update\_current\_observation(        name="Deeply nested LLM call", input="Ping?", output="Pong\!"    )    \# Set the parent trace's name from within a nested observation    langfuse\_context.update\_current\_trace(        name="Trace name set from deeply\_nested\_llm\_call",        session\_id="1234",        user\_id="5678",        tags=\["tag1", "tag2"\],        public=True    ) @observe()def nested\_span():    \# Update the current span with a custom name and level    langfuse\_context.update\_current\_observation(name="Nested Span", level="WARNING")    deeply\_nested\_llm\_call() @observe()def main():    nested\_span() \# Execute the main function to generate the enriched tracemain()

On the Langfuse platform the trace now shows with the updated name from the `deeply_nested_llm_call`, and the observations will be enriched with the appropriate data points.  
*Example trace: [https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/f16e0151-cca8-4d90-bccf-1d9ea0958afb](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/f16e0151-cca8-4d90-bccf-1d9ea0958afb)*

## **Log an LLM Call using `as_type="generation"`**

Model calls are represented by `generations` in Langfuse and allow you to add additional attributes. Use the `as_type="generation"` flag to mark a function as a generation. Optionally, you can extract additional generation specific attributes ([reference](https://python.reference.langfuse.com/langfuse/decorators#LangfuseDecorator.update_current_observation)).

This works with any LLM provider/SDK. In this example, we’ll use Anthropic.  
%pip install anthropic  
os.environ\["ANTHROPIC\_API\_KEY"\] \= "" import anthropicanthopic\_client \= anthropic.Anthropic()  
\# Wrap LLM function with decorator@observe(as\_type="generation")def anthropic\_completion(\*\*kwargs):  \# extract some fields from kwargs  kwargs\_clone \= kwargs.copy()  input \= kwargs\_clone.pop('messages', None)  model \= kwargs\_clone.pop('model', None)  langfuse\_context.update\_current\_observation(      input=input,      model=model,      metadata=kwargs\_clone  )   response \= anthopic\_client.messages.create(\*\*kwargs)  \# See docs for more details on token counts and usd cost in Langfuse  \# https://langfuse.com/docs/model-usage-and-cost  langfuse\_context.update\_current\_observation(      usage={          "input": response.usage.input\_tokens,          "output": response.usage.output\_tokens      }  )  \# return result  return response.content\[0\].text @observe()def main():  return anthropic\_completion(      model="claude-3-opus-20240229",      max\_tokens=1024,      messages=\[          {"role": "user", "content": "Hello, Claude"}      \]  ) main()  
*Example trace: [https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/66d06dd7-eeec-40c1-9b11-aac0e9c4f2fe?observation=d48a45f8-593c-4013-8a8a-23665b94aeda](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/66d06dd7-eeec-40c1-9b11-aac0e9c4f2fe?observation=d48a45f8-593c-4013-8a8a-23665b94aeda)*

## **Customize input/output**

By default, input/ouput of a function are captured by `@observe()`.

You can disable capturing input/output for a specific function:  
from langfuse.decorators import observe @observe(capture\_input=False, capture\_output=False)def stealth\_fn(input: str):    return input stealth\_fn("Super secret content")  
*Example trace: [https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/6bdeb443-ef8c-41d8-a8a1-68fe75639428](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/6bdeb443-ef8c-41d8-a8a1-68fe75639428)*

Alternatively, you can override input and output via `update_current_observation` (or `update_current_trace`):  
from langfuse.decorators import langfuse\_context, observe @observe()def fn\_2():    langfuse\_context.update\_current\_observation(        input="Table?", output="Tennis\!"    )    \# Logic for a deeply nested LLM call    pass @observe()def main\_fn():    langfuse\_context.update\_current\_observation(        input="Ping?", output="Pong\!"    )    fn\_2() main\_fn()  
*Example trace: [https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/d3c3ad92-d85d-4437-aaf3-7587d84f398c](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/d3c3ad92-d85d-4437-aaf3-7587d84f398c)*

## **Interoperability with other Integrations**

Langfuse is tightly integrated with the OpenAI SDK, LangChain, and LlamaIndex. The integrations are seamlessly interoperable with each other within a decorated function. The following example demonstrates this interoperability by using all three integrations within a single trace.

### **1\. Initializing example applications**

%pip install llama-index langchain langchain\_openai \--upgrade

#### **OpenAI**

The [OpenAI integration](https://langfuse.com/docs/integrations/openai/get-started) automatically detects the context in which it is executed. Just use `from langfuse.openai import openai` and get native tracing of all OpenAI calls.  
from langfuse.openai import openaifrom langfuse.decorators import observe @observe()def openai\_fn(calc: str):    res \= openai.chat.completions.create(        model="gpt-3.5-turbo",        messages=\[          {"role": "system", "content": "You are a very accurate calculator. You output only the result of the calculation."},          {"role": "user", "content": calc}\],    )    return res.choices\[0\].message.content

#### **LlamaIndex**

Via `Settings.callback_manager` you can configure the callback to use for tracing of the subsequent LlamaIndex executions. `langfuse_context.get_current_llama_index_handler()` exposes a callback handler scoped to the current trace context, in this case `llama_index_fn()`.  
from langfuse.decorators import langfuse\_context, observefrom llama\_index.core import Document, VectorStoreIndexfrom llama\_index.core import Settingsfrom llama\_index.core.callbacks import CallbackManager doc1 \= Document(text="""Maxwell "Max" Silverstein, a lauded movie director, screenwriter, and producer, was born on October 25, 1978, in Boston, Massachusetts. A film enthusiast from a young age, his journey began with home movies shot on a Super 8 camera. His passion led him to the University of Southern California (USC), majoring in Film Production. Eventually, he started his career as an assistant director at Paramount Pictures. Silverstein's directorial debut, “Doors Unseen,” a psychological thriller, earned him recognition at the Sundance Film Festival and marked the beginning of a successful directing career.""")doc2 \= Document(text="""Throughout his career, Silverstein has been celebrated for his diverse range of filmography and unique narrative technique. He masterfully blends suspense, human emotion, and subtle humor in his storylines. Among his notable works are "Fleeting Echoes," "Halcyon Dusk," and the Academy Award-winning sci-fi epic, "Event Horizon's Brink." His contribution to cinema revolves around examining human nature, the complexity of relationships, and probing reality and perception. Off-camera, he is a dedicated philanthropist living in Los Angeles with his wife and two children.""") @observe()def llama\_index\_fn(question: str):    \# Set callback manager for LlamaIndex, will apply to all LlamaIndex executions in this function    langfuse\_handler \= langfuse\_context.get\_current\_llama\_index\_handler()    Settings.callback\_manager \= CallbackManager(\[langfuse\_handler\])    \# Run application    index \= VectorStoreIndex.from\_documents(\[doc1,doc2\])    response \= index.as\_query\_engine().query(question)    return response

#### **LangChain**

`langfuse_context.get_current_llama_index_handler()` exposes a callback handler scoped to the current trace context, in this case `langchain_fn()`. Pass it to subsequent runs to your LangChain application to get full tracing within the scope of the current trace.  
from operator import itemgetterfrom langchain\_openai import ChatOpenAIfrom langchain.prompts import ChatPromptTemplatefrom langchain.schema import StrOutputParserfrom langfuse.decorators import observe prompt \= ChatPromptTemplate.from\_template("what is the city {person} is from?")model \= ChatOpenAI()chain \= prompt | model | StrOutputParser() @observe()def langchain\_fn(person: str):    \# Get Langchain Callback Handler scoped to the current trace context    langfuse\_handler \= langfuse\_context.get\_current\_langchain\_handler()    \# Pass handler to invoke    chain.invoke({"person": person}, config={"callbacks":\[langfuse\_handler\]})

### **2\. Run all in a single trace**

from langfuse.decorators import observe @observe()def main():    output\_openai \= openai\_fn("5+7")    output\_llamaindex \= llama\_index\_fn("What did he do growing up?")    output\_langchain \= langchain\_fn("Feynman")    return output\_openai, output\_llamaindex, output\_langchain main();  
*Example trace: [https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/4fcd93e3-79f2-474a-8e25-0e21c616249a](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/4fcd93e3-79f2-474a-8e25-0e21c616249a)*

## **Flush observations**

The Langfuse SDK executes network requests in the background on a separate thread for better performance of your application. This can lead to lost events in short lived environments such as AWS Lambda functions when the Python process is terminated before the SDK sent all events to the Langfuse API.

Make sure to call `langfuse_context.flush()` before exiting to prevent this. This method waits for all tasks to finish.

## **Additional features**

### **Scoring**

[Scores](https://langfuse.com/docs/scores/overview) are used to evaluate single observations or entire traces. You can create them via our annotation workflow in the Langfuse UI, run model-based evaluation or ingest via the SDK.

| Parameter | Type | Optional | Description |
| ----- | ----- | ----- | ----- |
| name | string | no | Identifier of the score. |
| value | number | no | The value of the score. Can be any number, often standardized to 0..1 |
| comment | string | yes | Additional context/explanation of the score. |

#### **Within the decorated function**

You can attach a score to the current observation context by calling `langfuse_context.score_current_observation`. You can also score the entire trace from anywhere inside the nesting hierarchy by calling `langfuse_context.score_current_trace`:  
from langfuse.decorators import langfuse\_context, observe @observe()def nested\_span():    langfuse\_context.score\_current\_observation(        name="feedback-on-span",        value=1,        comment="I like how personalized the response is",    )    langfuse\_context.score\_current\_trace(        name="feedback-on-trace-from-nested-span",        value=1,        comment="I like how personalized the response is",    ) \# This will create a new trace@observe()def main():    langfuse\_context.score\_current\_trace(        name="feedback-on-trace",        value=1,        comment="I like how personalized the response is",    )    nested\_span() main()  
*Example trace: [https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/1dfcff43-34c3-4888-b99a-bb9b9afd57c9](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/1dfcff43-34c3-4888-b99a-bb9b9afd57c9)*

#### **Outside the decorated function**

Alternatively you may also score a trace or observation from outside its context as often scores are added async. For example, based on user feedback.

The decorators expose the trace\_id and observation\_id which are necessary to add scores outside of the decorated functions:  
from langfuse import Langfusefrom langfuse.decorators import langfuse\_context, observe \# Initialize the Langfuse clientlangfuse\_client \= Langfuse() @observe()def nested\_fn():    span\_id \= langfuse\_context.get\_current\_observation\_id()    \# can also be accessed in main    trace\_id \= langfuse\_context.get\_current\_trace\_id()    return "foo\_bar", trace\_id, span\_id \# Create a new trace@observe()def main():    \_, trace\_id, span\_id \= nested\_fn()    return "main\_result", trace\_id, span\_id \# Flush the trace to send it to the Langfuse platformlangfuse\_context.flush() \# Execute the main function to generate a trace\_, trace\_id, span\_id \= main() \# Score the trace from outside the trace contextlangfuse\_client.score(    trace\_id=trace\_id,    name="trace-score",    value=1,    comment="I like how personalized the response is") \# Score the specific span/function from outside the trace contextlangfuse\_client.score(    trace\_id=trace\_id,    observation\_id=span\_id,    name="span-score",    value=1,    comment="I like how personalized the response is");  
*Example trace: [https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/0090556d-015c-48cb-bc33-4af29b05af31](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/0090556d-015c-48cb-bc33-4af29b05af31)*

### **Customize IDs**

By default, Langfuse assigns random ids to all logged events.

If you have your own unique ID (e.g. messageId, traceId, correlationId), you can easily set those as trace or observation IDs for effective lookups in Langfuse.

To dynamically set a custom ID for a trace or observation, simply pass a keyword argument `langfuse_observation_id` to the function decorated with `@observe()`. Thereby, the trace/observation in Langfuse will use this id. Note: ids in Langfuse are unique and traces/observations are upserted/merged on these ids.  
from langfuse.decorators import langfuse\_context, observeimport uuid @observe()def process\_user\_request(user\_id, request\_data, \*\*kwargs):    \# Function logic here    pass def main():    user\_id \= "user123"    request\_data \= {"action": "login"}    \# Custom ID for tracking    custom\_observation\_id \= "custom-" \+ str(uuid.uuid4())    \# Pass id as kwarg    process\_user\_request(        user\_id=user\_id,        request\_data=request\_data,        \# Pass the custom observation ID to the function        langfuse\_observation\_id=custom\_observation\_id,    ) main()  
*Example trace: [https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/custom-bbda815f-c61a-4cf5-a545-7fceeef1b635](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/custom-bbda815f-c61a-4cf5-a545-7fceeef1b635)*

### **Debug mode**

Enable debug mode to get verbose logs. Set the debug mode via the environment variable `LANGFUSE_DEBUG=True`.

### **Authentication check**

Use `langfuse_context.auth_check()` to verify that your host and API credentials are valid.  
from langfuse.decorators import langfuse\_context assert langfuse\_context.auth\_check()

## **Learn more**

See Docs and [SDK reference](https://python.reference.langfuse.com/langfuse/decorators) for more details. Questions? Add them on [GitHub Discussions](https://github.com/orgs/langfuse/discussions/categories/support).

