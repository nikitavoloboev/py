import asyncio
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class User(BaseModel):
    id: int
    name: str = "John Doe"
    signup_ts: Optional[datetime] = None
    friends: list[int] = []


async def main() -> None:
    external_data = {
        "id": "123",
        "signup_ts": "2017-06-01 12:22",
        "friends": [1, "2", b"3"],
    }
    user = User(**external_data)
    print(user)


if __name__ == "__main__":
    asyncio.run(main())
    print("✔️")
