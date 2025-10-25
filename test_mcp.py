#!/usr/bin/env python3
"""
Quick test script for Remembar MCP Server
Tests basic connectivity and tool availability
"""
import asyncio
import sys
from mcp_server import app, API_BASE
import httpx


async def test_mcp():
    """Test MCP server setup"""
    print("🧪 Testing Remembar MCP Server")
    print("=" * 50)
    print()
    
    # Test 1: Check API connectivity
    print("1. Testing API connectivity...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE}/")
            response.raise_for_status()
            print(f"   ✓ API is accessible at {API_BASE}")
    except Exception as e:
        print(f"   ❌ Cannot connect to API: {e}")
        print(f"   Make sure the API is running: python3 api-service/main.py")
        return False
    
    # Test 2: List available tools
    print()
    print("2. Checking available MCP tools...")
    try:
        tools = await app._tool_manager.list_tools()
        print(f"   ✓ Found {len(tools)} tools:")
        for tool in tools:
            print(f"      • {tool.name}: {tool.description[:60]}...")
    except Exception as e:
        print(f"   ❌ Error listing tools: {e}")
        return False
    
    # Test 3: List available prompts
    print()
    print("3. Checking available prompts...")
    try:
        prompts = await app._prompt_manager.list_prompts()
        print(f"   ✓ Found {len(prompts)} prompts:")
        for prompt in prompts:
            print(f"      • {prompt.name}: {prompt.description}")
    except Exception as e:
        print(f"   ❌ Error listing prompts: {e}")
        return False
    
    print()
    print("=" * 50)
    print("✅ All tests passed!")
    print()
    print("Next steps:")
    print("1. Configure Claude Desktop (see MCP_SETUP.md)")
    print("2. Or test directly: echo '<your_mcp_request>' | python3 mcp_server.py")
    print()
    return True


if __name__ == "__main__":
    success = asyncio.run(test_mcp())
    sys.exit(0 if success else 1)

