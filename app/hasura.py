import httpx
from app.config import settings


class HasuraClient:
    def __init__(self):
        self.url = settings.HASURA_URL
        self.headers = {
            "Content-Type": "application/json",
            "X-Hasura-Admin-Secret": settings.HASURA_ADMIN_SECRET,
        }

    async def query(self, query: str, variables: dict = None):
        """Execute a GraphQL query against Hasura."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()


# Singleton instance
hasura_client = HasuraClient()
