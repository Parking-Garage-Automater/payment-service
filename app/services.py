import httpx


async def get_payment_plan_status(plate_number: str):
    url = f"http://user-service/api/v1/users/payment-plan/{plate_number}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json().get("is_enabled", False)
    except httpx.RequestError as e:
        print(f"Failed to reach User Service: {str(e)}")

    return False  # Default to False if User Service is unreachable
