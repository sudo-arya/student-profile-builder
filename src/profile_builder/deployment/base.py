from typing import Protocol
from .models import DeploymentRequest, DeploymentResult


class DeploymentProvider(Protocol):
    def deploy(self, request: DeploymentRequest) -> DeploymentResult: ...
