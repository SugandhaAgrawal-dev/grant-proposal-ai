"""apps/llm/views.py — LLM management API endpoints."""
import asyncio
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.http import StreamingHttpResponse

from apps.llm.router import LLMRouter


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Check all LLM providers health."""
    results = {}
    for provider in LLMRouter.available_providers():
        try:
            router = LLMRouter(provider=provider)
            result = asyncio.run(router.health_check())
            results[provider] = result
        except Exception as exc:
            results[provider] = {"status": "error", "error": str(exc)}
    return Response(results)


@api_view(["GET"])
@permission_classes([AllowAny])
def list_providers(request):
    """List available LLM providers."""
    from django.conf import settings
    default = settings.LLM_CONFIG.get("default_provider", "ollama")
    return Response({
        "providers": LLMRouter.available_providers(),
        "default":   default,
    })


@api_view(["GET"])
def list_models(request):
    """List models for a specific provider."""
    provider = request.query_params.get("provider", "ollama")
    try:
        router  = LLMRouter(provider=provider)
        models  = asyncio.run(router.list_models())
        return Response({"provider": provider, "models": models})
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def test_generate(request):
    """Test LLM generation with a simple prompt."""
    provider   = request.data.get("provider", "ollama")
    prompt     = request.data.get("prompt", "Say hello in one sentence.")
    temperature= float(request.data.get("temperature", 0.35))

    try:
        router   = LLMRouter(provider=provider)
        response = asyncio.run(router.chat(
            messages    = [{"role": "user", "content": prompt}],
            temperature = temperature,
            max_tokens  = 200,
        ))
        return Response({"provider": provider, "response": response})
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
