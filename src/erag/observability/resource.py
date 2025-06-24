from opentelemetry.sdk.resources import Resource

from erag.config.settings import Settings


def build_resource(settings: Settings) -> Resource:
    return Resource.create(
        {
            "service.name": settings.service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.environment,
        }
    )
