import os
import datetime
import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import Command
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from db_manager import (
	init_db, get_user_services_dict, get_downtime_for_service, update_downtime_for_service
)
from commands import (
	cmd_start, cmd_help, cmd_interval, cmd_get_interval, cmd_add_service,
	cmd_remove_service, cmd_log, cmd_myservices, cmd_check_service
)
from service_checker import check_user_services
from config import API_TOKEN

logging.basicConfig(
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	level=logging.INFO
)
logger = logging.getLogger(__name__)


class MonitoringBot:
	def __init__(self):
		self.bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
		self.dp = Dispatcher(self.bot)
		self.dp.middleware.setup(LoggingMiddleware())

		self.dp.register_message_handler(cmd_start, Command("start"))
		self.dp.register_message_handler(cmd_help, Command("help"))
		self.dp.register_message_handler(cmd_interval, Command("interval"))
		self.dp.register_message_handler(cmd_get_interval, Command("get_interval"))
		self.dp.register_message_handler(cmd_add_service, Command("add"))
		self.dp.register_message_handler(cmd_remove_service, Command("remove"))
		self.dp.register_message_handler(cmd_log, Command("log"))
		self.dp.register_message_handler(cmd_myservices, Command("myservices"))
		self.dp.register_message_handler(cmd_check_service, Command("check_service"))

	async def start(self):
		await init_db()
		asyncio.create_task(self.monitor_services())

		await self.dp.start_polling()

		await self.bot.session.close()
		await self.dp.storage.close()
		await self.dp.storage.wait_closed()

	async def monitor_services(self):
		service_statuses = {}
		while True:
			user_dict = await get_user_services_dict()
			for chat_id, user_data in user_dict.items():
				user_services, check_interval = user_data
				results = await check_user_services(chat_id)

				for url, (status, error) in results.items():
					if (chat_id, url) not in service_statuses:
						service_statuses[(chat_id, url)] = (status, error)

					if status != service_statuses[(chat_id, url)][0]:
						service_statuses[(chat_id, url)] = (status, error)

						message = f"🔄 Статус сервиса <b>{url}</b> изменился:\n\n"

						if status:
							message += f"✅ Сервис доступен"
						else:
							message += f"❌ Сервис недоступен"

							message += f"\n\nПричина: {error}"

						await self.send_message(chat_id, message, parse_mode=types.ParseMode.HTML)

				await asyncio.sleep(check_interval)


if __name__ == "__main__":
	logging.basicConfig(level=logging.WARNING)
	monitoring_bot = MonitoringBot()
	loop = asyncio.get_event_loop()
	try:
		loop.create_task(monitoring_bot.start())
		loop.run_forever()
	except Exception as e:
		logging.exception(f"Exception in main: {e}")
	finally:
		loop.close()
