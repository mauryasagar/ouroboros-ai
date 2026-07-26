import os
import json
import logging
from dotenv import load_dotenv
from groq import Groq
from mcp_client import MCPClient

load_dotenv()
logging.basicConfig(level=logging.INFO)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SIGNOZ_API_KEY = os.getenv("SIGNOZ_API_KEY")

SYSTEM_PROMPT = """You are an AI observability expert with live access to SigNoz via tools.

IMPORTANT:
- You are already authenticated to SigNoz via an API key. Do NOT include username, password, or any authentication parameters in tool calls.
- Only use the required parameters for each tool (e.g., serviceName, start, end, limit).
- If a tool requires a service name and none is given, use 'deep-agent-service'.
- If a time range is needed, use the last 1 hour.
- Be concise and direct. This is a live demo — answers should be a few sentences max.
- When you find a root cause, state it plainly with the specific numbers from the data.
- If a tool result includes a webUrl or trace link, include it verbatim in your answer.
"""

class SidekickAgent:
    def __init__(self):
        self.groq = Groq(api_key=GROQ_API_KEY)
        self.mcp = MCPClient(url="http://localhost:8000/mcp", api_key=SIGNOZ_API_KEY)
        self.tools = self.mcp.list_tools()
        self.model = "openai/gpt-oss-20b"
        logging.info(f"Loaded {len(self.tools)} MCP tools")

    def _format_tools_for_groq(self):
        # Whitelist of tools you actually need (reduces token usage)
        allowed_tools = {
            "signoz_list_services",
            "signoz_get_traces",
            "signoz_get_logs",
            "signoz_get_metrics",
            "signoz_get_span",
        }
        filtered = [t for t in self.tools if t.get("name") in allowed_tools]
        tools_to_use = filtered if filtered else self.tools

        groq_tools = []
        for tool in tools_to_use:
            schema = tool.get("inputSchema") or tool.get("parameters") or {"type": "object", "properties": {}}
            groq_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": schema
                }
            })
        return groq_tools

    def ask(self, question: str):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]

        tools = self._format_tools_for_groq()
        tools_used = []

        for turn in range(6):
            response = self.groq.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                max_tokens=512
            )
            msg = response.choices[0].message

            if not msg.tool_calls:
                return msg.content, tools_used

            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in msg.tool_calls
                ]
            })

            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}

                tools_used.append(name)
                logging.info(f"[turn {turn+1}] Tool: {name}({args})")

                try:
                    result = self.mcp.call_tool(name, args)
                except Exception as e:
                    result = f"Tool error: {str(e)}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)[:6000]
                })

        messages.append({
            "role": "user",
            "content": "Please summarise what you found from the data above."
        })
        final = self.groq.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=512
        )
        return final.choices[0].message.content, tools_used


if __name__ == "__main__":
    agent = SidekickAgent()
    answer, tools = agent.ask("What services have sent traces in the last hour?")
    print("ANSWER:", answer)
    print("TOOLS:", tools)
