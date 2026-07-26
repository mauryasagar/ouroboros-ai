import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

class MCPClient:
    def __init__(self, url, api_key):
        self.url = url
        self.api_key = api_key
        self.session_id = None
        self.req_id = 1

    def _headers(self):
        h = {
            "SIGNOZ-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if self.session_id:
            h["Mcp-Session-Id"] = self.session_id
        return h

    def _send(self, method, params=None):
        payload = {
            "jsonrpc": "2.0",
            "id": self.req_id,
            "method": method
        }
        if params:
            payload["params"] = params

        response = requests.post(
            self.url,
            headers=self._headers(),
            json=payload,
            timeout=60
        )
        response.raise_for_status()

        sid = response.headers.get("Mcp-Session-Id")
        if sid:
            self.session_id = sid

        self.req_id += 1

        content_type = response.headers.get("content-type", "")
        text = response.text

        if "text/event-stream" in content_type or "data: " in text:
            data_line = None
            for line in text.splitlines():
                if line.startswith("data:"):
                    data_line = line[len("data:"):].strip()
            if data_line:
                text = data_line

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}

        if "error" in parsed:
            raise RuntimeError(f"MCP error: {parsed['error']}")

        return parsed.get("result", {})

    def initialize(self):
        return self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "sidekick", "version": "1.0"}
        })

    def list_tools(self):
        self.initialize()
        result = self._send("tools/list")
        return result.get("tools", [])

    def call_tool(self, name, args):
        result = self._send("tools/call", {
            "name": name,
            "arguments": args
        })
        if isinstance(result, dict) and "content" in result:
            contents = result["content"]
            if isinstance(contents, list):
                parts = []
                for c in contents:
                    if isinstance(c, dict):
                        parts.append(c.get("text", str(c)))
                    else:
                        parts.append(str(c))
                return "\n".join(parts)
        return result
