import asyncio
import mlx.core as mx


async def main() -> None:
    a = mx.array([1, 2, 3, 4])
    print(a.shape)


if __name__ == "__main__":
    asyncio.run(main())
    print("✔️")
