import time
import random
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.trace import Status, StatusCode

# 1. Setup Resource
resource = Resource(attributes={"service.name": "deep-agent-service"})

# 2. Setup Tracing
trace_provider = TracerProvider(resource=resource)
trace_exporter = OTLPSpanExporter(endpoint="localhost:4317", insecure=True)
trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

# 3. Setup Logging
logger_provider = LoggerProvider(resource=resource)
log_exporter = OTLPLogExporter(endpoint="localhost:4317", insecure=True)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)

# Mock pricing: $0.0001 per 1K tokens
COST_PER_1K_TOKENS = 0.0001

def retrieve_context(query, is_chaos_mode=False):
    with tracer.start_as_current_span("retrieve_context") as span:
        # CHAOS MODE: 15 docs, NORMAL: 1-8 docs
        context_docs = 15 if is_chaos_mode else random.randint(1, 8)
        span.set_attribute("llm.context_docs", context_docs)
        time.sleep(random.uniform(0.1, 0.4))
        return f"Mock context data ({context_docs} docs)"

def llm_call(prompt, context_docs):
    with tracer.start_as_current_span("llm_call") as span:
        # More docs = more delay
        delay = 0.3 + (context_docs * 0.15) + random.uniform(0, 0.2)
        time.sleep(delay)
        
        tokens = random.randint(100, 500) + (context_docs * 50)
        cost = (tokens / 1000) * COST_PER_1K_TOKENS
        
        span.set_attribute("llm.prompt", prompt)
        span.set_attribute("llm.tokens", tokens)
        span.set_attribute("llm.estimated_cost_usd", round(cost, 6))
        
        # If chaos mode, log ERROR
        if context_docs >= 15:
            logging.error(f"CONTEXT_OVERLOAD: Agent failed. Used {tokens} tokens, cost ${round(cost, 6)}, took {delay:.2f}s.")
            span.set_status(Status(StatusCode.ERROR, "Context Overload"))
        else:
            logging.info(f"LLM call normal: {tokens} tokens, ${round(cost, 6)} cost, {context_docs} docs. Duration: {delay:.2f}s")
            span.set_status(Status(StatusCode.OK))
        
        return "Mock LLM response."

def handle_request(user_query):
    with tracer.start_as_current_span("handle_request") as span:
        span.set_attribute("user.query", user_query)
        
        # 20% chance of CHAOS MODE
        is_chaos_mode = random.random() < 0.20
        
        context = retrieve_context(user_query, is_chaos_mode)
        doc_count = int(context.split('(')[1].split(' ')[0])
        
        llm_response = llm_call(user_query, doc_count)
        
        return llm_response

if __name__ == "__main__":
    queries = ["What's the weather?", "Summarize this doc", "Book a flight", "Debug this error"]
    print("🚀 Starting Ouroboros telemetry generator... (Ctrl+C to stop)")
    i = 0
    try:
        while True:
            q = random.choice(queries)
            handle_request(q)
            i += 1
            if i % 10 == 0:
                print(f"✅ Sent {i} traces to SigNoz...")
            time.sleep(0.2)
    except KeyboardInterrupt:
        print(f"\n🛑 Stopped after {i} traces.")
