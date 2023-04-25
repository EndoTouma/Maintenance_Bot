import logging
from typing import Dict, Union, Tuple

import aiohttp
import aiosqlite
import aiocache

from db_manager import get_user_services

from config import DB_NAME


@aiocache.cached(ttl=60)
async def check_user_services(chat_id: int) -> dict[str, tuple[bool, str]]:
    services = await get_user_services(chat_id)
    results = {}
    for service in services:
        url = service
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    results[url] = (response.status == 200, "")
        except Exception as e:
            results[url] = (False, str(e))

    return results
