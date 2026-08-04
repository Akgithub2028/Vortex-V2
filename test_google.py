import asyncio
from vortex.config import get_settings
from vortex.gateway.providers import get_provider
from vortex.gateway.providers.base import CompletionRequest

async def main():
    settings = get_settings()
    provider = get_provider("google", settings.google_api_key)
    req = CompletionRequest(
        model="gemini-2.5-flash",
        messages=[{"role": "user", "content": "Respond with {'is_injection': true}"}],
    )
    resp = await provider.complete(req)
    print(repr(resp.content))

if __name__ == "__main__":
    asyncio.run(main())
