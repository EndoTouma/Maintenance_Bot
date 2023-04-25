import logging
import asyncio
from typing import List, Dict, Union, Tuple

import aiosqlite

from config import DB_NAME


async def create_users_table(conn):
	cursor = await conn.cursor()
	await cursor.execute(
		"CREATE TABLE IF NOT EXISTS users ("
		"chat_id INTEGER PRIMARY KEY,"
		"interval INTEGER NOT NULL DEFAULT 30"
		")"
	)
	await conn.commit()


async def create_user_services_table(conn):
	cursor = await conn.cursor()
	await cursor.execute(
		"CREATE TABLE IF NOT EXISTS user_services ("
		"id INTEGER PRIMARY KEY AUTOINCREMENT,"
		"chat_id INTEGER NOT NULL,"
		"service_name TEXT NOT NULL,"
		"service_url TEXT NOT NULL,"
		"FOREIGN KEY (chat_id) REFERENCES users (chat_id)"
		")"
	)
	await conn.commit()


async def init_db():
	async with aiosqlite.connect(DB_NAME) as conn:
		await create_users_table(conn)
		await create_user_services_table(conn)


async def add_user(chat_id: int) -> None:
	async with aiosqlite.connect(DB_NAME) as conn:
		cursor = await conn.cursor()
		await cursor.execute("INSERT OR IGNORE INTO users (chat_id, interval) VALUES (?, 30)", (chat_id,))
		await conn.commit()


async def set_interval(chat_id: int, interval: int) -> None:
	async with aiosqlite.connect(DB_NAME) as conn:
		cursor = await conn.cursor()
		await cursor.execute("UPDATE users SET interval=? WHERE chat_id=?", (interval, chat_id))
		if cursor.rowcount == 0:
			await cursor.execute("INSERT INTO users (chat_id, interval) VALUES (?, ?)", (chat_id, interval))
		await conn.commit()


async def get_interval(chat_id: int) -> int:
	async with aiosqlite.connect(DB_NAME) as db:
		cursor = await db.cursor()
		await cursor.execute("SELECT interval FROM users WHERE chat_id=?", (chat_id,))
		row = await cursor.fetchone()
		return row[0] if row else None


async def add_service(chat_id: int, service_url: str) -> None:
	async with aiosqlite.connect(DB_NAME) as conn:
		cursor = await conn.cursor()
		await cursor.execute("INSERT INTO user_services (chat_id, service_name, service_url) VALUES (?, ?, ?)",
		                     (chat_id, 'default_service_name', service_url))
		await conn.commit()


async def remove_user_service(chat_id: int, service_url: str) -> bool:
	async with aiosqlite.connect(DB_NAME) as conn:
		cursor = await conn.cursor()
		await cursor.execute(
			"DELETE FROM user_services WHERE chat_id=? AND service_url=?",
			(chat_id, service_url)
		)
		rows_affected = cursor.rowcount
		await conn.commit()

	return rows_affected > 0


async def get_user_services(chat_id: int) -> List[str]:
	async with aiosqlite.connect(DB_NAME) as conn:
		cursor = await conn.cursor()
		await cursor.execute("SELECT service_url FROM user_services WHERE chat_id=?", (chat_id,))
		services = await cursor.fetchall()
		return [service[0] for service in services]


async def get_user_services_dict() -> Dict[int, Tuple[List[str], int]]:
	async with aiosqlite.connect(DB_NAME) as db:
		cursor = await db.execute("SELECT u.chat_id, ifnull(group_concat(us.service_url, ','), '') as services, "
		                          "u.interval FROM users as u LEFT JOIN user_services as us ON u.chat_id = us.chat_id GROUP BY u.chat_id")
		rows = await cursor.fetchall()
		return {row[0]: (row[1].split(","), row[2]) for row in rows}


async def get_downtime_for_service(chat_id: int, service_url: str) -> int:
	async with aiosqlite.connect(DB_NAME) as conn:
		cursor = await conn.cursor()
		await cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='downtime_logs'")
		result = await cursor.fetchone()
		if not result:
			await cursor.execute('''CREATE TABLE downtime_logs
                                   (chat_id INTEGER, service_url TEXT, downtime_duration INTEGER,
                                    PRIMARY KEY(chat_id, service_url))''')
			await conn.commit()
			return 0
		await cursor.execute(
			"SELECT downtime_duration FROM downtime_logs WHERE chat_id=? AND service_url=?",
			(chat_id, service_url),
		)
		result = await cursor.fetchone()
		return result[0] if result else 0


async def update_downtime_for_service(chat_id: int, service_url: str, downtime_duration: int) -> None:
	async with aiosqlite.connect(DB_NAME) as conn:
		cursor = await conn.cursor()
		await cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='downtime_logs'")
		result = await cursor.fetchone()
		if not result:
			await cursor.execute('''CREATE TABLE downtime_logs
                                   (chat_id INTEGER, service_url TEXT, downtime_duration INTEGER,
                                    PRIMARY KEY(chat_id, service_url))''')
			await conn.commit()
		await cursor.execute(
			"UPDATE downtime_logs SET downtime_duration=? WHERE chat_id=? AND service_url=?",
			(downtime_duration, chat_id, service_url),
		)
		await conn.commit()


async def get_logs_for_user(chat_id: int) -> Dict[str, List[Tuple[str, int]]]:
	async with aiosqlite.connect(DB_NAME) as conn:
		cursor = await conn.cursor()
		await cursor.execute(
			"SELECT name FROM sqlite_master WHERE type='table' AND name='downtime_logs'"
		)
		result = await cursor.fetchone()
		if not result:
			await cursor.execute('''CREATE TABLE downtime_logs
                                   (chat_id INTEGER, service_url TEXT, downtime_duration INTEGER,
                                    PRIMARY KEY(chat_id, service_url))''')
			await conn.commit()
			return {}

		await cursor.execute(
			"SELECT service_url, downtime_duration FROM downtime_logs WHERE chat_id=?",
			(chat_id,)
		)
		rows = await cursor.fetchall()

	logs = {}
	for row in rows:
		service_url, downtime_duration = row
		if service_url not in logs:
			logs[service_url] = []
		logs[service_url].append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), downtime_duration))

	return logs
