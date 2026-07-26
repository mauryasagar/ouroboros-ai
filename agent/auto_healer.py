from flask import Flask, request, jsonify
import logging
import time
import random
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

app = Flask(__name__)

# Setup OpenTelemetry
resource = Resource(attributes={"service.name": "auto-healer-service"})
trace_provider = TracerProvider(resource=resource)
exporter = OTLPSpanExporter(endpoint="localhost:4317", insecure=True)
trace_provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

def optimized_llm_call(prompt):
    with tracer.start_as_current_span("optimized_llm_call") as span:
        delay = random.uniform(0.3, 0.5)
        time.sleep(delay)
        
        tokens = random.randint(100, 200)
        cost = (tokens / 1000) * 0.0001
        
        span.set_attribute("llm.prompt", prompt)
        span.set_attribute("llm.tokens", tokens)
        span.set_attribute("llm.estimated_cost_usd", round(cost, 6))
        span.set_attribute("llm.optimized", True)
        span.set_attribute("llm.auto_healed", True)
        
        return "Optimized response"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json or {}
    alert_name = data.get("alertname") or data.get("labels", {}).get("alertname", "Unknown Alert")
    alert_state = data.get("status", "firing")
    print(f"🚨 ALERT RECEIVED FROM SIGNOZ: {alert_name} [{alert_state}]")

    with tracer.start_as_current_span("auto_heal_webhook") as span:
        span.set_attribute("alert.triggered", True)
        span.set_attribute("alert.name", alert_name)
        span.set_attribute("alert.state", alert_state)
        
        print(" AUTO-HEAL: Retrying with optimized parameters...")
        
        result = optimized_llm_call("Auto-healed request")
        
        span.set_attribute("auto_heal.success", True)
        span.set_attribute("auto_heal.message", result)
        
        # Add success event
        span.add_event("AUTO-HEAL SUCCESS", attributes={
            "message": "Request auto-healed with optimized parameters",
            "status": "healed"
        })
        
        return jsonify({
            "status": "healed",
            "message": "Request auto-healed with optimized parameters",
            "result": result
        }), 200

if __name__ == "__main__":
    print("🛡️ Auto-Healer service starting on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
