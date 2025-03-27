import httpx
import os

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")

async def get_payment_plan_status(plate_number: str) -> bool:
    url = f"{USER_SERVICE_URL}/us/api/users/{plate_number}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    plan = data.get("data", {}).get("payment_plan")
                    return bool(plan and plan != "none")
    except httpx.RequestError as e:
        print(f"Failed to reach User Service: {str(e)}")

    return False
