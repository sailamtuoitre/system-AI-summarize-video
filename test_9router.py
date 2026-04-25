"""
Test script to verify 9router integration with CDIO 3
Run this to check if 9router is properly configured and Qwen API is accessible
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_9router_running():
    """Check if 9router is running on localhost:20128"""
    import requests
    
    try:
        response = requests.get("http://localhost:20128/v1/models", timeout=5)
        if response.status_code == 200:
            print("✅ 9router is running and accessible")
            return True
        else:
            print(f"⚠️  9router responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 9router is NOT running")
        print("   Start 9router with: cd C:\\Users\\leduc\\OneDrive\\Desktop\\9router\\9router && npm run dev")
        return False
    except requests.exceptions.Timeout:
        print("❌ 9router request timed out")
        return False

def check_env_configuration():
    """Check if .env file is properly configured"""
    from dotenv import load_dotenv
    
    env_path = Path(__file__).parent.parent / ".env"
    
    if not env_path.exists():
        print("❌ .env file not found")
        print("   Copy .env.9router.example to .env and configure it")
        return False
    
    load_dotenv(env_path)
    
    nine_router_url = os.getenv("NINE_ROUTER_URL")
    nine_router_api_key = os.getenv("NINE_ROUTER_API_KEY")
    
    if not nine_router_url:
        print("⚠️  NINE_ROUTER_URL not set in .env")
        print("   Using default: http://localhost:20128/v1")
    
    if not nine_router_api_key:
        print("⚠️  NINE_ROUTER_API_KEY not set in .env")
        print("   Get API key from: http://localhost:20128/dashboard")
        return False
    
    if nine_router_api_key == "copy_from_9router_dashboard":
        print("❌ NINE_ROUTER_API_KEY has placeholder value")
        print("   Get actual API key from: http://localhost:20128/dashboard")
        return False
    
    print("✅ Environment variables configured")
    print(f"   URL: {nine_router_url or 'http://localhost:20128/v1'}")
    print(f"   API Key: {nine_router_api_key[:10]}...")
    return True

def test_qwen_model_access():
    """Test if we can access Qwen model through 9router"""
    import requests
    
    api_key = os.getenv("NINE_ROUTER_API_KEY")
    base_url = os.getenv("NINE_ROUTER_URL", "http://localhost:20128/v1")
    
    if not api_key or api_key == "copy_from_9router_dashboard":
        print("⚠️  Skipping model test - API key not configured")
        return False
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "qw/qwen3-coder-plus",
        "messages": [
            {"role": "user", "content": "Say hello in Vietnamese"}
        ],
        "max_tokens": 50
    }
    
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            message = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print("✅ Successfully accessed Qwen model through 9router")
            print(f"   Response: {message[:100]}...")
            return True
        else:
            print(f"❌ Model access failed with status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Error testing model access: {e}")
        return False

def check_qwen_provider_connected():
    """Check if Qwen provider is connected in 9router dashboard"""
    import requests
    
    try:
        response = requests.get("http://localhost:20128/api/providers", timeout=5)
        if response.status_code == 200:
            providers = response.json()
            qwen_provider = None
            
            for provider in providers:
                if provider.get("id") == "qwen" or "qwen" in provider.get("name", "").lower():
                    qwen_provider = provider
                    break
            
            if qwen_provider:
                status = qwen_provider.get("status", "unknown")
                if status == "connected":
                    print("✅ Qwen provider is connected")
                    return True
                else:
                    print(f"⚠️  Qwen provider status: {status}")
                    print("   Connect Qwen in dashboard: http://localhost:20128/dashboard")
                    return False
            else:
                print("⚠️  Qwen provider not found")
                print("   Add Qwen provider in dashboard: http://localhost:20128/dashboard")
                return False
        else:
            print(f"⚠️  Could not fetch providers: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  Could not check providers: {e}")
        return False

def main():
    print("=" * 60)
    print("  9router + CDIO 3 Integration Test")
    print("=" * 60)
    print()
    
    # Test 1: Check 9router running
    print("Test 1: Checking 9router status...")
    router_ok = check_9router_running()
    print()
    
    # Test 2: Check environment
    print("Test 2: Checking environment configuration...")
    env_ok = check_env_configuration()
    print()
    
    # Test 3: Check Qwen provider
    print("Test 3: Checking Qwen provider connection...")
    qwen_ok = check_qwen_provider_connected()
    print()
    
    # Test 4: Test model access
    print("Test 4: Testing Qwen model access...")
    model_ok = test_qwen_model_access()
    print()
    
    # Summary
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  9router Running:     {'✅' if router_ok else '❌'}")
    print(f"  Environment Config:  {'✅' if env_ok else '⚠️ '}")
    print(f"  Qwen Provider:       {'✅' if qwen_ok else '⚠️ '}")
    print(f"  Model Access:        {'✅' if model_ok else '⚠️ '}")
    print()
    
    if router_ok and env_ok and qwen_ok and model_ok:
        print("🎉 All tests passed! 9router integration is ready.")
        print()
        print("Next steps:")
        print("  1. Start your CDIO 3 backend and frontend")
        print("  2. Upload a video and test the AI features")
        print("  3. Monitor usage in 9router dashboard: http://localhost:20128")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        print()
        print("Quick fixes:")
        if not router_ok:
            print("  - Start 9router: cd C:\\Users\\leduc\\OneDrive\\Desktop\\9router\\9router && npm run dev")
        if not env_ok:
            print("  - Configure .env: Copy .env.9router.example to .env")
        if not qwen_ok:
            print("  - Connect Qwen: http://localhost:20128/dashboard → Providers → Connect Qwen")
        if not model_ok:
            print("  - Check API key and model name in .env")
        return 1

if __name__ == "__main__":
    sys.exit(main())
