"""
Simple test client for the AutoDevOS API server.
Tests the health check and generation endpoints.
"""
import requests
import sys
import time
from typing import Optional


class AutoDevOSClient:
    """Client for interacting with the AutoDevOS API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
    
    def health_check(self) -> dict:
        """Check if the server is healthy."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def generate(self, prompt: str, output_dir: str = "output") -> dict:
        """Generate an application from a prompt."""
        payload = {
            "prompt": prompt,
            "output_dir": output_dir
        }
        response = requests.post(
            f"{self.base_url}/generate",
            json=payload,
            timeout=600  # 10 minutes timeout for long-running operations
        )
        response.raise_for_status()
        return response.json()


def main():
    """Run example tests against the AutoDevOS API."""
    client = AutoDevOSClient()
    
    print("🔍 Testing AutoDevOS API Server\n")
    print("=" * 60)
    
    # Test 1: Health Check
    print("\n1. Testing Health Check...")
    try:
        health = client.health_check()
        print(f"   ✓ Server is healthy: {health}")
    except Exception as e:
        print(f"   ✗ Health check failed: {e}")
        print("\n❌ Make sure the server is running:")
        print("   python server.py")
        print("   OR")
        print("   uvicorn main:app --reload")
        sys.exit(1)
    
    # Test 2: Generate Application
    print("\n2. Testing Application Generation...")
    print("   Prompt: 'Create a simple calculator with basic operations'")
    print("   This may take a few minutes...\n")
    
    try:
        start_time = time.time()
        result = client.generate(
            prompt="Create a simple calculator with basic operations",
            output_dir="output_test"
        )
        elapsed_time = time.time() - start_time
        
        print(f"\n   ✓ Generation completed in {elapsed_time:.2f} seconds")
        print(f"   Success: {result['success']}")
        print(f"   Message: {result['message']}")
        print(f"   Summary: {result['summary']}")
        
        if result['success']:
            print("\n   📁 Check the 'output_test' directory for generated files")
        else:
            print("\n   ⚠️  Some tasks failed during generation")
            
    except requests.exceptions.Timeout:
        print("   ✗ Request timed out. The operation is taking longer than expected.")
    except Exception as e:
        print(f"   ✗ Generation failed: {e}")
    
    print("\n" + "=" * 60)
    print("✓ API tests completed\n")


if __name__ == "__main__":
    main()
