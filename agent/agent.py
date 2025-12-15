"""
Логика AI-агента на основе LangChain
"""
import json
import os
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from .logger_config import get_logger

# Инициализация логгера
logger = get_logger("ai_agent.agent")

# Импорты LangChain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Импорты агентов
# В LangChain 0.2+ структура изменилась, пробуем разные варианты
try:
    # Стандартный импорт для большинства версий LangChain
    from langchain.agents import AgentExecutor, create_openai_tools_agent
except ImportError:
    # Альтернативный способ для некоторых версий
    try:
        import langchain.agents as agents_module
        AgentExecutor = getattr(agents_module, 'AgentExecutor', None)
        create_openai_tools_agent = getattr(agents_module, 'create_openai_tools_agent', None)
        
        if AgentExecutor is None or create_openai_tools_agent is None:
            raise ImportError(
                "Не удалось импортировать AgentExecutor или create_openai_tools_agent.\n"
                "Попробуйте выполнить: pip install --upgrade 'langchain>=0.2.0' 'langchain-openai>=0.1.0'"
            )
    except Exception as e:
        raise ImportError(
            f"Не удалось импортировать необходимые модули LangChain: {e}\n"
            "Попробуйте выполнить: pip install --upgrade 'langchain>=0.2.0' 'langchain-openai>=0.1.0'"
        )

from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv
from .tools import get_tools

load_dotenv()


class AIAgent:
    """AI-агент с инструментами и памятью"""
    
    def __init__(self, model: str = "gpt-4", temperature: float = 0.7):
        """
        Инициализация агента
        
        Args:
            model: Модель OpenAI (gpt-4, gpt-3.5-turbo)
            temperature: Температура для генерации
        """
        logger.info(f"Инициализация AIAgent с моделью: {model}, temperature: {temperature}")
        
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OPENAI_API_KEY не найден в переменных окружения!")
            raise ValueError("OPENAI_API_KEY не найден в переменных окружения!")
        
        logger.debug("API ключ найден (первые 10 символов): " + self.api_key[:10] + "...")
        
        # Настройка прокси, если указан в переменных окружения
        http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        
        llm_kwargs = {
            "model": model,
            "temperature": temperature,
            "openai_api_key": self.api_key
        }
        
        # Добавляем прокси, если указан
        if http_proxy or https_proxy:
            logger.info(f"Обнаружены настройки прокси: HTTP_PROXY={bool(http_proxy)}, HTTPS_PROXY={bool(https_proxy)}")
            try:
                import httpx
                proxies = {}
                if http_proxy:
                    proxies["http://"] = http_proxy
                if https_proxy:
                    proxies["https://"] = https_proxy
                # Создаем httpx клиент с прокси
                http_client = httpx.Client(
                    proxies=proxies,
                    timeout=60.0,
                    verify=True
                )
                llm_kwargs["http_client"] = http_client
                logger.info(f"Прокси настроен: {proxies}")
            except ImportError:
                logger.warning("httpx не установлен. Прокси не будет использован.")
        
        logger.debug("Создание ChatOpenAI экземпляра...")
        self.llm = ChatOpenAI(**llm_kwargs)
        logger.info(f"ChatOpenAI инициализирован с моделью: {model}")
        
        logger.debug("Загрузка инструментов...")
        self.tools = get_tools()
        logger.info(f"Загружено инструментов: {len(self.tools)}")
        
        self.memory_file = os.path.join(os.path.dirname(__file__), "memory.json")
        logger.debug(f"Файл памяти: {self.memory_file}")
        
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        logger.debug("ConversationBufferMemory инициализирована")
        
        # Загрузка истории из файла
        logger.debug("Загрузка истории диалога из файла...")
        self._load_memory()
        
        # Создание промпта для агента
        logger.debug("Создание промпта для агента...")
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Ты полезный AI-агент с доступом к различным инструментам.
Ты можешь:
- Искать информацию в интернете (web_search)
- Выполнять HTTP запросы (http_request)
- Работать с файлами: читать (read_file) и писать (write_file)
- Выполнять безопасные терминальные команды (execute_terminal)
       - Получать погоду для любого города (get_weather)
       - Узнавать курс криптовалют (get_crypto_price)
       - Узнавать курс обычных валют (EUR/USD/RUB и др.) (get_currency_rate)
       - Генерировать QR-коды (generate_qr_code)

ВАЖНО при работе с файлами:
- Для чтения файла используй read_file с путем к файлу (например: 'test.json')
- Для записи файла используй write_file в формате 'путь|содержимое' (например: 'output.txt|Текст резюме')
- Используй относительные пути без начального слеша: 'test.json', а не '/test.json'

Всегда будь вежливым и полезным. Если тебе нужна дополнительная информация для выполнения задачи, спроси у пользователя.
ОБЯЗАТЕЛЬНО используй инструменты для выполнения задач пользователя - не говори, что не можешь, а используй доступные инструменты!"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        logger.debug("Промпт создан")
        
        # Создание агента
        logger.debug("Создание агента с инструментами...")
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        logger.debug("Агент создан")
        
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )
        logger.info("AgentExecutor инициализирован успешно")
    
    def _load_memory(self):
        """Загрузка истории диалога из файла"""
        logger.debug(f"Попытка загрузки памяти из {self.memory_file}")
        if os.path.exists(self.memory_file):
            try:
                logger.debug("Файл памяти существует, чтение...")
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    memory_data = json.load(f)
                
                logger.debug(f"Загружено данных из памяти: {len(memory_data.get('messages', []))} сообщений")
                    
                # Восстановление истории из сохраненных сообщений
                if 'messages' in memory_data:
                    loaded_count = 0
                    for msg in memory_data['messages']:
                        if msg['type'] == 'human':
                            self.memory.chat_memory.add_user_message(msg['content'])
                            loaded_count += 1
                        elif msg['type'] == 'ai':
                            self.memory.chat_memory.add_ai_message(msg['content'])
                            loaded_count += 1
                    logger.info(f"Загружено {loaded_count} сообщений из истории диалога")
                else:
                    logger.warning("В файле памяти нет ключа 'messages'")
            except Exception as e:
                logger.error(f"Ошибка при загрузке памяти: {e}", exc_info=True)
        else:
            logger.info("Файл памяти не существует, будет создан новый")
    
    def _save_memory(self):
        """Сохранение истории диалога в файл"""
        logger.debug("Сохранение памяти в файл...")
        try:
            messages = []
            for msg in self.memory.chat_memory.messages:
                if hasattr(msg, 'content'):
                    msg_type = 'human' if msg.__class__.__name__ == 'HumanMessage' else 'ai'
                    messages.append({
                        'type': msg_type,
                        'content': msg.content
                    })
            
            logger.debug(f"Подготовлено {len(messages)} сообщений для сохранения")
            
            logger.debug("Генерация резюме диалога...")
            summary = self._generate_summary()
            
            memory_data = {
                'messages': messages,
                'summary': summary
            }
            
            logger.debug(f"Запись в файл {self.memory_file}...")
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(memory_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Память успешно сохранена: {len(messages)} сообщений")
        except Exception as e:
            logger.error(f"Ошибка при сохранении памяти: {e}", exc_info=True)
    
    def _generate_summary(self) -> str:
        """Генерация краткого резюме диалога"""
        logger.debug("Генерация резюме диалога...")
        try:
            recent_messages = self.memory.chat_memory.messages[-10:]
            if not recent_messages:
                logger.debug("Нет сообщений для резюме")
                return "История диалога пуста."
            
            logger.debug(f"Генерация резюме для {len(recent_messages)} последних сообщений")
            summary_prompt = "Кратко опиши последние сообщения в диалоге (максимум 3 предложения):\n"
            for msg in recent_messages:
                role = "Пользователь" if msg.__class__.__name__ == 'HumanMessage' else "Агент"
                summary_prompt += f"{role}: {msg.content}\n"
            
            summary_llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.3,
                openai_api_key=self.api_key
            )
            logger.debug("Вызов LLM для генерации резюме...")
            summary = summary_llm.invoke(summary_prompt).content
            logger.debug(f"Резюме сгенерировано: {summary[:50]}...")
            return summary
        except Exception as e:
            logger.warning(f"Не удалось сгенерировать резюме: {e}", exc_info=True)
            return "Не удалось сгенерировать резюме."
    
    def process(self, user_input: str) -> str:
        """
        Обработка запроса пользователя
        
        Args:
            user_input: Ввод пользователя
            
        Returns:
            Ответ агента
        """
        logger.info(f"Получен запрос пользователя: {user_input[:100]}...")
        logger.debug(f"Полный запрос: {user_input}")
        
        try:
            logger.debug("Вызов agent_executor.invoke()...")
            response = self.agent_executor.invoke({"input": user_input})
            logger.debug(f"Получен ответ от agent_executor: {type(response)}")
            
            answer = response.get("output", "Извините, не удалось обработать запрос.")
            logger.info(f"Ответ агента сгенерирован (длина: {len(answer)} символов)")
            logger.debug(f"Ответ агента: {answer[:200]}...")
            
            # Сохранение памяти после каждого запроса
            logger.debug("Сохранение памяти после обработки запроса...")
            self._save_memory()
            
            return answer
        except Exception as e:
            error_str = str(e)
            logger.error(f"Ошибка при обработке запроса: {error_str}", exc_info=True)
            
            # Специальная обработка ошибки 403 - регион не поддерживается
            if "403" in error_str or "unsupported_country_region_territory" in error_str.lower():
                logger.error("Обнаружена ошибка 403 - регион не поддерживается")
                error_msg = (
                    "❌ Ошибка: OpenAI API недоступен в вашем регионе.\n\n"
                    "Возможные решения:\n"
                    "1. Используйте VPN или прокси для доступа к OpenAI API\n"
                    "2. Используйте альтернативный API endpoint (если доступен)\n"
                    "3. Настройте прокси в переменных окружения:\n"
                    "   export HTTP_PROXY=http://your-proxy:port\n"
                    "   export HTTPS_PROXY=http://your-proxy:port\n\n"
                    "Подробнее см. файл REGION_FIX.md"
                )
                logger.info("Вывод сообщения об ошибке региона пользователю")
                return error_msg
            
            # Обработка других ошибок API
            if "401" in error_str or "invalid_api_key" in error_str.lower():
                logger.error("Обнаружена ошибка 401 - неверный API ключ")
                error_msg = (
                    "❌ Ошибка: Неверный API ключ OpenAI.\n"
                    "Проверьте, что в файле .env указан правильный OPENAI_API_KEY"
                )
                return error_msg
            
            if "429" in error_str or "rate_limit" in error_str.lower():
                logger.warning("Обнаружена ошибка 429 - превышен лимит запросов")
                error_msg = (
                    "❌ Ошибка: Превышен лимит запросов к OpenAI API.\n"
                    "Подождите некоторое время и попробуйте снова."
                )
                return error_msg
            
            # Общая обработка ошибок
            logger.error(f"Необработанная ошибка: {error_str}")
            error_msg = f"❌ Ошибка при обработке запроса: {error_str}"
            return error_msg

