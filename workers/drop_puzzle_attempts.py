import asyncio
from settings import db


async def main():

    await db.users.update_many({},
        {'$set': {
            'total_attempts.free_puzzle': 30,
            'used_attempts.free_puzzle': 0,
            'used_attempts.puzzle': 0,
        }})

    print("OK")

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
    main()
