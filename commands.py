from aiogram import types
from aiogram.types import InputFile
from aiogram.dispatcher.filters import Text
import aiohttp
import urllib.parse

from db_manager import (
	add_service, remove_user_service, get_user_services, get_interval, set_interval, get_logs_for_user, add_user,
	get_user_services_dict

)


async def cmd_start(message: types.Message):
	chat_id = message.chat.id
	await add_user(chat_id)
	await message.reply("Привет! Я бот для мониторинга сервисов.\n"
	                    "Для получения списка доступных команд используйте /help.")


async def cmd_help(message: types.Message):
	await message.reply("Доступные команды:\n"
	                    "/add [URL] - добавить сервис для мониторинга\n"
	                    "/remove [URL] - удалить сервис из мониторинга\n"
	                    "/interval [секунды] - изменить интервал проверки сервисов\n"
	                    "/get_interval - узнать текущий интервал проверки сервисов\n"
	                    "/log - получить лог простоя сервисов\n"
	                    "/myservices - получить список ваших добавленных сервисов\n"
	                    "/check_service - Проверка состояние конкретного сервиса "
	                    )


async def cmd_interval(message: types.Message):
	try:
		if len(message.text.split()) < 2:
			await message.reply("Необходимо указать интервал в виде числа после команды /interval.")
			return
		interval = int(message.text.split()[1])
		await set_interval(message.chat.id, interval)
		await message.reply(f"Интервал проверки сервисов успешно изменен на {interval} секунд.")
	except ValueError as e:
		await message.reply(
			"Ошибка при изменении интервала проверки сервисов. Убедитесь, что указали интервал в виде числа.")


async def cmd_get_interval(message: types.Message):
	interval = await get_interval(message.chat.id)
	if interval is not None:
		await message.reply(f"Текущий интервал проверки сервисов: {interval} секунд.")
	else:
		await message.reply("Ошибка! Не удалось получить интервал проверки сервисов.")


async def cmd_add_service(message: types.Message):
	try:
		service_url = message.text.split()[1]
	except IndexError:
		await message.answer("Please provide a service URL")
		return

	chat_id = message.chat.id
	await add_service(chat_id, service_url)
	await message.answer(f"Service {service_url} added for monitoring.")


async def cmd_remove_service(message: types.Message):
	service_url = message.get_args()
	if not service_url:
		await message.reply("Пожалуйста, введите URL сервиса, который хотите удалить.")
	else:
		removed = await remove_user_service(message.chat.id, service_url)
		if removed:
			await message.reply(f"Сервис {service_url} успешно удален.")
		else:
			await message.reply(f"Ошибка! Не удалось удалить сервис {service_url}.")


async def cmd_log(message: types.Message):
	logs = await get_logs_for_user(message.chat.id)
	if logs:
		log_messages = [f"{log[0]} - {log[1]}" for log in logs]
		log_text = "\n".join(log_messages)
		await message.reply(f"Логи простоя сервисов:\n\n{log_text}")
	else:
		await message.reply("Нет логов простоя сервисов.")


async def cmd_myservices(message: types.Message):
	chat_id = message.chat.id
	services = await get_user_services(chat_id)
	if services:
		reply_text = "Ваши добавленные сервисы:\n\n" + "\n".join(services)
	else:
		reply_text = "У вас пока не добавлено ни одного сервиса."

	await message.reply(reply_text)


async def cmd_check_service(message: types.Message):
	service_url = message.get_args()

	if not service_url:
		await message.reply("Пожалуйста, укажите URL сервиса")
		return

	encoded_url = urllib.parse.quote(service_url, safe=':/')
	async with aiohttp.ClientSession() as session:
		try:
			async with session.get(encoded_url, timeout=5) as response:
				response.raise_for_status()
		except Exception as e:
			await message.reply(f"Сервис {service_url} недоступен. Ошибка: {str(e)}")
		else:
			await message.reply(f"Сервис {service_url} доступен. Статус код: {response.status}")
