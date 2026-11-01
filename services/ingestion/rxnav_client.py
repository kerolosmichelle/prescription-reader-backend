import httpx
import asyncio
from typing import Dict, List, Any
import json

class RxNavClient:
    def __init__(self, base_url: str = "https://rxnav.nlm.nih.gov/REST"):
        self.base_url = base_url

    async def get_drugs(self, name: str) -> Dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/drugs.json", params={"name": name})
            response.raise_for_status()
            return response.json()

    async def get_approximate_match(self, term: str) -> Dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/approximateTerm.json", params={"term": term, "maxEntries": 20})
            response.raise_for_status()
            return response.json()

    async def get_rxcui_properties(self, rxcui: str) -> Dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/rxcui/{rxcui}/properties.json")
            response.raise_for_status()
            return response.json()

    async def get_all_related_info(self, rxcui: str) -> Dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/rxcui/{rxcui}/allrelated.json")
            response.raise_for_status()
            return response.json()

    async def get_ingredients(self, rxcui: str) -> Dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/rxcui/{rxcui}/related.json", params={"tty": "IN"})
            response.raise_for_status()
            return response.json()

async def test():
    client = RxNavClient()
    result = await client.get_drugs("paracetamol")
    print(json.dumps(result, indent=2)[:500])

if __name__ == "__main__":
    asyncio.run(test())
